from typing import Callable, Optional

_automatically_convert_timeout: bool = False
_timeout_warning_threshold_min: float = 0.1
_timeout_warning_threshold_max: float = 10
_on_timeout_violation: Optional[Callable] = None


def set_automatic_timeout_conversion(
    auto_convert: bool,
    timeout_warning_threshold_min: float = 0.1,
    timeout_warning_threshold_max: float = 10,
    on_timeout_violation: Callable[[], None] = None,
):
    """
    To assist in migrating from Qt timeouts to Python timeouts, this function will disable automatic time duration
    conversion. The conversion occurs when this library calls through to any Qt object that accepts an integer time
    duration whose unit is milliseconds.
    :param auto_convert: If True, any timeouts which are integers and not floats will not be
    :param timeout_warning_threshold_min: A floating point number representing the minimum threshold at which a timeout
        will emit a warning log and traceback. This value is in seconds, and can be configured to a value appropriate
        to the application.
    :param timeout_warning_threshold_max: Like the min threshold, this will emit a warning if a timeout exceeds it.
    :return:
    """
    global _automatically_convert_timeout, _timeout_warning_threshold_min, _timeout_warning_threshold_max, _on_timeout_violation
    _automatically_convert_timeout = auto_convert
    _timeout_warning_threshold_min = timeout_warning_threshold_min
    _timeout_warning_threshold_max = timeout_warning_threshold_max
    _on_timeout_violation = on_timeout_violation
