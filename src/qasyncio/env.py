import os
import asyncio
import contextlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.qasyncio.loop import _QEventLoop


if os.name == "nt":
    from ._windows import QProactorEventLoop

    QEventLoop = QProactorEventLoop
else:
    from ._unix import QSelectorEventLoop  # noqa

    QEventLoop = QSelectorEventLoop


class QEventLoopPolicyMixin(asyncio.DefaultEventLoopPolicy):
    def new_event_loop(self) -> "_QEventLoop":
        return QEventLoop()


@contextlib.contextmanager
def _set_event_loop_policy(policy):
    old_policy = asyncio.get_event_loop_policy()
    asyncio.set_event_loop_policy(policy)
    try:
        yield
    finally:
        asyncio.set_event_loop_policy(old_policy)


def run(*args, **kwargs):
    with _set_event_loop_policy(QEventLoopPolicyMixin()):
        return asyncio.run(*args, **kwargs)
