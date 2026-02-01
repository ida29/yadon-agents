"""Common utility functions for Yadon Desktop Pet"""

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
