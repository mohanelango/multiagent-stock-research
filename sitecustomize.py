import os

# Prevent any accidental breakpoint() hooks from causing debugger/break exceptions
os.environ.setdefault("PYTHONBREAKPOINT", "0")

# Force matplotlib to a non-GUI backend (prevents Windows backend crashes)
os.environ.setdefault("MPLBACKEND", "Agg")

# Disable pytest auto-loading random plugins (we’ll explicitly enable what we need)
# You can comment this out if you prefer CLI env var instead.
os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
