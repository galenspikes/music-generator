"""Share / export the generated MIDI via the native iOS share sheet.

Presents a ``UIActivityViewController`` for the ``.mid`` file so the user can
save it to Files, AirDrop it, or open it in another app (a DAW, a notation app,
etc.) — all on-device.
"""

from __future__ import annotations

from pathlib import Path

from rubicon.objc import ObjCClass
from rubicon.objc.types import CGPoint, CGRect, CGSize

NSURL = ObjCClass("NSURL")
NSArray = ObjCClass("NSArray")
UIApplication = ObjCClass("UIApplication")
UIActivityViewController = ObjCClass("UIActivityViewController")


def _root_view_controller():
    app = UIApplication.sharedApplication
    window = app.keyWindow  # deprecated but reliable for single-scene Toga apps
    if window is None:
        windows = app.windows
        if windows is not None and windows.count > 0:
            window = windows.objectAtIndex(0)
    return window.rootViewController if window is not None else None


def share_file(path: Path | str) -> bool:
    """Present the share sheet for ``path``. Returns ``False`` if no presenting
    view controller is available."""
    url = NSURL.fileURLWithPath(str(path))
    items = NSArray.arrayWithObject(url)
    controller = UIActivityViewController.alloc().initWithActivityItems(
        items, applicationActivities=None)

    root = _root_view_controller()
    if root is None:
        return False

    # On iPad the share sheet is a popover and must be anchored or it crashes;
    # anchor it to the centre of the presenting view.
    popover = controller.popoverPresentationController
    if popover is not None:
        view = root.view
        bounds = view.bounds
        w = bounds.size.width
        h = bounds.size.height
        popover.sourceView = view
        popover.sourceRect = CGRect(CGPoint(w / 2.0, h / 2.0), CGSize(1.0, 1.0))

    root.presentViewController(controller, animated=True, completion=None)
    return True
