"""
colors.py — Theme palette and basic formatting helpers for YIMITER.
"""

class C:
    BG         = "#0b0e14"
    CARD       = "#131720"
    CARD2      = "#181e2c"
    HOVER      = "#1a1f2e"
    BORDER     = "#262d3d"
    TEXT       = "#e2e8f0"
    TEXT2      = "#7c8da6"
    TEXT3      = "#3e4a63"
    CYAN       = "#22d3ee"
    GREEN      = "#34d399"
    YELLOW     = "#fbbf24"
    ORANGE     = "#fb923c"
    RED        = "#ef4444"
    PURPLE     = "#a78bfa"
    PINK       = "#f472b6"
    BLUE       = "#60a5fa"
    GAUGE_BG   = "#1e2433"
    SLEEP      = "#8b5cf6"
    SETTINGS   = "#2d3348"


def usage_color(pct):
    """Return an HSL-tailored warning color based on RAM usage percentage."""
    if pct < 50:  return C.GREEN
    if pct < 70:  return C.CYAN
    if pct < 85:  return C.YELLOW
    if pct < 95:  return C.ORANGE
    return C.RED


def fmt(b):
    """Format bytes into a sleek, human-readable string."""
    for u in ("B", "KB", "MB", "GB"):
        if abs(b) < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"
