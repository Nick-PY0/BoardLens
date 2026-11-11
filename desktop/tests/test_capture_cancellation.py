import threading,time,pytest
from chess_helper.mac_capture import _await,CaptureCancelled


def test_capture_wait_is_bounded_and_stop_interrupts_it():
    began=time.monotonic()
    with pytest.raises(RuntimeError):_await(lambda callback:None,threading.Event(),timeout=.04)
    assert time.monotonic()-began<.4
    cancel=threading.Event();timer=threading.Timer(.02,cancel.set);timer.start();began=time.monotonic()
    with pytest.raises(CaptureCancelled):_await(lambda callback:None,cancel,timeout=2)
    assert time.monotonic()-began<.3
    timer.join()
