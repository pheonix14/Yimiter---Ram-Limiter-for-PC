"""
Process control for Yimiter.
"""

import ctypes
import os
import time

import psutil


class ProcessManager:
    def __init__(self, cfg):
        self.cfg = cfg
        self.sleeping = {}  # pid -> (name, timestamp)
        self.activity = {}  # pid -> [(timestamp, cpu_seconds)]
        self.last_actions = []
        self.own_pid = os.getpid()

    def _remember(self, message):
        self.last_actions.append(message)
        self.last_actions = self.last_actions[-20:]

    def drain_actions(self):
        actions = self.last_actions[:]
        self.last_actions.clear()
        return actions

    def _cpu_seconds(self, cpu_times):
        if not cpu_times:
            return 0.0
        return float(getattr(cpu_times, "user", 0.0) + getattr(cpu_times, "system", 0.0))

    def sample_processes(self, total_mem):
        now = time.time()
        # Cache processes for 1.0 second to avoid multiple expensive iterations in the same cycle
        if hasattr(self, "_last_scan_time") and now - self._last_scan_time < 1.0:
            return self._cached_procs

        self._last_scan_time = now
        cutoff = now - max(1, int(self.cfg.activity_window_min)) * 60
        alive = set()
        procs = []

        for p in psutil.process_iter(["pid", "name", "memory_info", "cpu_times"]):
            try:
                info = p.info
                pid = info["pid"]
                name = info["name"] or "Unknown"
                alive.add(pid)

                # CPU times & Activity
                cpu_times = info.get("cpu_times")
                samples = self.activity.setdefault(pid, [])
                samples.append((now, self._cpu_seconds(cpu_times)))
                self.activity[pid] = [s for s in samples if s[0] >= cutoff]

                # Memory info
                mi = info.get("memory_info")
                if mi:
                    rss = mi.rss
                    pct = rss / total_mem * 100 if total_mem else 0
                    procs.append((pid, name, rss, pct))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception as exc:
                self._remember(f"Process sample skipped: {exc}")

        # Cleanup dead processes from activity
        for pid in list(self.activity):
            if pid not in alive:
                self.activity.pop(pid, None)

        procs.sort(key=lambda x: x[2], reverse=True)

        # Cleanup dead sleeping processes
        for pid in [p for p in self.sleeping if not psutil.pid_exists(p)]:
            del self.sleeping[pid]

        self._cached_procs = procs
        return procs

    def sample_activity(self):
        # Fallback if called independently
        mem_total = psutil.virtual_memory().total
        self.sample_processes(mem_total)

    def recent_cpu_delta(self, pid):
        samples = self.activity.get(pid, [])
        if len(samples) < 2:
            return 0.0
        return max(0.0, samples[-1][1] - samples[0][1])

    def _is_protected(self, pid, name):
        return pid == self.own_pid or self.cfg.is_essential((name or "").lower())

    def _trim_working_set(self, pid):
        try:
            h = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, int(pid))
            if h:
                ctypes.windll.psapi.EmptyWorkingSet(h)
                ctypes.windll.kernel32.CloseHandle(h)
                return True
        except Exception:
            return False
        return False

    def get_sorted_processes(self, total_mem):
        return self.sample_processes(total_mem)

    def sleep(self, pid, name):
        if self._is_protected(pid, name):
            return False, f"Protected: {name}"
        try:
            psutil.Process(pid).suspend()
            self.sleeping[pid] = (name, time.time())
            msg = f"Sleeping: {name}"
            self._remember(msg)
            return True, msg
        except psutil.NoSuchProcess:
            return False, f"Gone: {name}"
        except psutil.AccessDenied:
            return False, f"Access denied: {name} - run as Admin"
        except Exception as e:
            return False, str(e)

    def wake(self, pid, name):
        try:
            psutil.Process(pid).resume()
            self.sleeping.pop(pid, None)
            msg = f"Awake: {name}"
            self._remember(msg)
            return True, msg
        except psutil.NoSuchProcess:
            self.sleeping.pop(pid, None)
            return False, f"Gone: {name}"
        except psutil.AccessDenied:
            return False, f"Access denied: {name}"
        except Exception as e:
            return False, str(e)

    def wake_all(self):
        count = 0
        for pid in list(self.sleeping):
            try:
                psutil.Process(pid).resume()
                count += 1
            except Exception:
                pass
        self.sleeping.clear()
        if count:
            self._remember(f"Woke up {count} sleeping process(es)")
        return count

    def kill(self, pid, name):
        if self._is_protected(pid, name):
            return False, f"Protected: {name}"
        try:
            p = psutil.Process(pid)
            if pid in self.sleeping:
                try:
                    p.resume()
                except Exception:
                    pass
            p.terminate()
            try:
                p.wait(timeout=3)
            except psutil.TimeoutExpired:
                try:
                    p.resume()
                except Exception:
                    pass
                p.kill()
            self.sleeping.pop(pid, None)
            msg = f"Killed: {name}"
            self._remember(msg)
            return True, msg
        except psutil.NoSuchProcess:
            return True, f"Already gone: {name}"
        except psutil.AccessDenied:
            return False, f"Access denied: {name} - run as Admin"
        except Exception as e:
            return False, str(e)

    def _freeze_candidates(self):
        min_bytes = int(self.cfg.sleep_above_mb) * 1024 * 1024
        procs = []
        for p in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                info = p.info
                pid = info["pid"]
                name = info["name"] or "Unknown"
                mi = info["memory_info"]
                if not mi or mi.rss < min_bytes or pid in self.sleeping:
                    continue
                if self._is_protected(pid, name):
                    continue
                procs.append((pid, name, mi.rss, self.recent_cpu_delta(pid)))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        procs.sort(key=lambda x: (x[3], -x[2]))
        return procs

    def auto_sleep_low_activity(self):
        slept = []
        limit = max(1, int(self.cfg.freeze_per_cycle))
        self.sample_activity()

        for pid, name, rss, _cpu_delta in self._freeze_candidates()[:limit]:
            ok, _ = self.sleep(pid, name)
            if ok:
                self._trim_working_set(pid)
                slept.append((name, rss))
        return slept

    def auto_sleep_one(self):
        slept = self.auto_sleep_low_activity()
        if slept:
            return slept[0]
        return None, 0

    def deep_sleep_hogs(self):
        slept = 0
        for pid, name, _rss, _cpu_delta in self._freeze_candidates()[:8]:
            ok, _ = self.sleep(pid, name)
            if ok:
                slept += 1
        return slept

    def kill_notifications(self):
        count = 0
        for p in psutil.process_iter(["pid", "name"]):
            try:
                info = p.info
                name = info["name"] or "Unknown"
                if self.cfg.is_bloat(name.lower()) and info["pid"] not in self.sleeping:
                    ok, _ = self.sleep(info["pid"], name)
                    if ok:
                        count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return count

    def flush_memory(self):
        freed = 0
        for p in psutil.process_iter(["pid", "name"]):
            try:
                if not self._is_protected(p.info["pid"], p.info.get("name") or ""):
                    if self._trim_working_set(p.info["pid"]):
                        freed += 1
            except Exception:
                continue
        return freed

    def enforce_crash_prevention(self):
        if not self.cfg.crash_prevention:
            return []

        actions_taken = []
        limit_bytes = float(self.cfg.proc_limit_gb) * (1024**3)

        for p in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                info = p.info
                pid = info["pid"]
                name = info["name"] or "Unknown"
                mi = info["memory_info"]
                if not mi or mi.rss < limit_bytes or self._is_protected(pid, name):
                    continue

                action = self.cfg.proc_limit_action
                if action == "kill":
                    ok, msg = self.kill(pid, name)
                    if ok:
                        actions_taken.append(f"{msg} - exceeded {self.cfg.proc_limit_gb}GB limit")
                elif action == "flush":
                    if self._trim_working_set(pid):
                        msg = f"Flushed {name} - exceeded {self.cfg.proc_limit_gb}GB limit"
                        actions_taken.append(msg)
                        self._remember(msg)
                else:
                    ok, msg = self.sleep(pid, name)
                    if ok:
                        self._trim_working_set(pid)
                        actions_taken.append(f"{msg} - exceeded {self.cfg.proc_limit_gb}GB limit")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception as exc:
                self._remember(f"Crash guard skipped a process: {exc}")
        return actions_taken

    def system_crash_prevention(self, mem_pct, total_mem):
        if not self.cfg.system_crash_guard:
            return None

        # Cooldown of 20 seconds to prevent rapid-fire triggers
        now = time.time()
        if not hasattr(self, "_last_sys_guard_time"):
            self._last_sys_guard_time = 0.0
        if now - self._last_sys_guard_time < 20.0:
            return None

        if mem_pct >= self.cfg.system_crash_threshold:
            self._last_sys_guard_time = now
            actions = []

            # Step 1: Flush memory of non-essential processes
            flushed = self.flush_memory()
            if flushed > 0:
                actions.append(f"System RAM reached {mem_pct:.1f}%! Flushed working sets of {flushed} processes.")

            # Step 2: If system RAM is still above threshold, sleep/kill/flush the single largest non-essential process
            # Refresh memory percent check
            time.sleep(0.1) # brief pause to let memory settle
            new_mem = psutil.virtual_memory()
            if new_mem.percent >= self.cfg.system_crash_threshold:
                # Get the processes sorted by memory usage
                procs = self.get_sorted_processes(total_mem)
                for pid, name, rss, pct in procs:
                    if not self._is_protected(pid, name) and pid not in self.sleeping:
                        from colors import fmt
                        if self.cfg.system_crash_action == "sleep":
                            ok, msg = self.sleep(pid, name)
                            if ok:
                                self._trim_working_set(pid)
                                actions.append(f"System Crash Guard: Auto-slept memory hog '{name}' ({fmt(rss)}) to free RAM.")
                                break
                        elif self.cfg.system_crash_action == "kill":
                            ok, msg = self.kill(pid, name)
                            if ok:
                                actions.append(f"System Crash Guard: Auto-killed memory hog '{name}' ({fmt(rss)}) to prevent system crash.")
                                break
                        elif self.cfg.system_crash_action == "flush":
                            if self._trim_working_set(pid):
                                actions.append(f"System Crash Guard: Trimmed working set of memory hog '{name}' ({fmt(rss)}).")
                                break
            return actions
        return None
