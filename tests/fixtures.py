from typing import TYPE_CHECKING

from src.env import QEvent, QtModuleName, PYQT6_MODULE_NAME

if TYPE_CHECKING:
    from src.env import QCoreApplication


def process_events(qapp: "QCoreApplication"):
    for _ in range(0, 5):
        if QtModuleName == PYQT6_MODULE_NAME:
            qapp.send_posted_events(event_type=QEvent.Type.DeferredDelete)
        else:
            qapp.send_posted_events(event_type=QEvent.DeferredDelete)
        qapp.processEvents()
