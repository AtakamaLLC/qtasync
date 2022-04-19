import pytest
from qtasync.qconcurrent._futures import QtThreadPoolExecutor


@pytest.fixture
def executor(request):
    exe = QtThreadPoolExecutor()
    request.addfinalizer(exe.shutdown)
    return exe


@pytest.fixture
def shutdown_executor():
    exe = QtThreadPoolExecutor()
    exe.shutdown()
    return exe


def test_ctx_after_shutdown(shutdown_executor):
    with pytest.raises(RuntimeError):
        with shutdown_executor:
            pass


# def test_submit_after_shutdown(shutdown_executor):
#     with pytest.raises(RuntimeError):
#         shutdown_executor.submit(None)


# def test_stack_recursion_limit(executor):
#     # Test that worker threads have sufficient stack size for the default
#     # sys.getrecursionlimit. If not this should fail with SIGSEGV or SIGBUS
#     # (or event SIGILL?)
#     def rec(a, *args, **kwargs):
#         rec(a, *args, **kwargs)
#     fs = [executor.submit(rec, 1) for _ in range(10)]
#     for f in fs:
#         with pytest.raises(RecursionError):
#             f.result()
