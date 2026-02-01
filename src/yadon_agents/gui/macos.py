"""macOS window elevation — ウィンドウを最前面に固定する"""

import ctypes
import sys

from yadon_agents.gui.utils import log_debug


def mac_set_top_nonactivating(widget) -> None:
    """macOS: force window to status/floating level without stealing focus."""
    try:
        if sys.platform != "darwin":
            return
        view_ptr = int(widget.winId())
        if not view_ptr:
            return
        objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")
        cg = ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics"
        )

        sel_registerName = objc.sel_registerName
        sel_registerName.restype = ctypes.c_void_p
        sel = lambda name: sel_registerName(name)

        objc.objc_msgSend.restype = ctypes.c_void_p
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

        window = objc.objc_msgSend(ctypes.c_void_p(view_ptr), sel(b"window"))
        if not window:
            return

        cg.CGWindowLevelForKey.argtypes = [ctypes.c_int]
        cg.CGWindowLevelForKey.restype = ctypes.c_int
        KEYS = {"floating": 3, "modal": 8, "status": 18, "popup": 101}
        levels = {
            name: int(cg.CGWindowLevelForKey(ctypes.c_int(val)))
            for name, val in KEYS.items()
        }
        level = max(levels.values())

        objc.objc_msgSend.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long,
        ]
        objc.objc_msgSend(window, sel(b"setLevel:"), ctypes.c_long(int(level)))

        try:
            behavior = ctypes.c_ulong(1)
            objc.objc_msgSend.argtypes = [
                ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong,
            ]
            objc.objc_msgSend(window, sel(b"setCollectionBehavior:"), behavior)
        except Exception:
            pass

    except Exception as e:
        log_debug("macos", f"elevate failed: {e}")
