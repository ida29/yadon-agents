"""Common utility functions for Yadon Desktop Pet"""

import os
import shutil
import subprocess
from config import DEBUG_LOG


def log_debug(component: str, message: str):
    """Write debug message to log file

    Args:
        component: Name of the component (e.g., 'yadon_pet', 'process_monitor')
        message: Debug message to log
    """
    try:
        with open(DEBUG_LOG, 'a') as f:
            f.write(f"[{component}] {message}\n")
    except Exception:
        pass


def get_tmux_binary() -> str:
    """Resolve tmux binary path robustly

    Returns:
        Path to tmux binary
    """
    # Try environment PATH first
    path = shutil.which('tmux')
    if path:
        return path

    # Common paths for tmux
    for candidate in ('/opt/homebrew/bin/tmux', '/usr/local/bin/tmux', '/usr/bin/tmux'):
        if os.path.exists(candidate):
            return candidate

    # Fallback to plain name
    return 'tmux'


def run_tmux(args, component='utils'):
    """Run tmux command with resolved binary

    Args:
        args: List of arguments to pass to tmux
        component: Component name for logging

    Returns:
        CompletedProcess or None if failed
    """
    cmd = [get_tmux_binary()] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            log_debug(component, f"tmux call failed: {' '.join(cmd)} | rc={result.returncode} | err={result.stderr.strip()}")
        return result
    except Exception as e:
        log_debug(component, f"tmux invoke error: {e}")
        return None
