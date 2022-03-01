_timeout_compatibility_mode = False


def set_timeout_compatibility_mode(compat_mode: bool):
    global _timeout_compatibility_mode
    _timeout_compatibility_mode = compat_mode


def get_timeout_compatibility_mode() -> bool:
    global _timeout_compatibility_mode
    return _timeout_compatibility_mode
