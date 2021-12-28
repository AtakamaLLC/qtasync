class FailureCodes:
    TIMEOUT = 10000
    EXCEPTION_RAISED = 10001
    WINDOW_CREATION_FAILED = 10002
    WINDOW_SUPPRESSED_FAILURE = 10003
    UNEXPECTED = -1

    @classmethod
    def get_failure_message(cls, code: int):
        if code == cls.TIMEOUT:
            return "Test timed out"
        elif code == cls.EXCEPTION_RAISED:
            return "Unexpected exception encountered"
        elif code == cls.WINDOW_CREATION_FAILED:
            return "Window creation failed for interactive test"
        elif code == cls.WINDOW_SUPPRESSED_FAILURE:
            return "Window suppressed for interactive test"
        elif code == cls.UNEXPECTED:
            return "Test failed unexpectedly"
        else:
            return f"Unknown failure code: {code}"
