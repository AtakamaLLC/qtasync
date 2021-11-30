from typing import TYPE_CHECKING

from PySide2.QtCore import QEvent

if TYPE_CHECKING:
    from PySide2.QtCore import QCoreApplication


def process_events(qapp: "QCoreApplication"):
    for _ in range(0, 5):
        qapp.sendPostedEvents(event_type=QEvent.DeferredDelete)
        qapp.processEvents()

