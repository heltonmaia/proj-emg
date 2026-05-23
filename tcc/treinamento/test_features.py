import numpy as np
import pytest

from features import rms, mav, sd, wl, var


def test_rms_constant_signal():
    # RMS of constant 3 is 3
    assert rms(np.array([3, 3, 3, 3])) == pytest.approx(3.0)


def test_rms_zero_signal():
    assert rms(np.zeros(10)) == 0.0


def test_rms_handles_negative():
    # RMS of [-3, 3] = sqrt((9+9)/2) = 3
    assert rms(np.array([-3, 3])) == pytest.approx(3.0)


def test_mav_simple():
    assert mav(np.array([2, 2, 2])) == pytest.approx(2.0)


def test_mav_differs_from_mean_on_signed_values():
    # MAV uses abs(); mean does not. This is the bug in prediction.py.
    x = np.array([-2, 2])
    assert mav(x) == pytest.approx(2.0)
    assert np.mean(x) == 0.0          # confirma que mean simples é diferente


def test_sd_constant_signal_is_zero():
    assert sd(np.array([5, 5, 5, 5])) == 0.0


def test_sd_simple():
    # std of [1,2,3,4,5] with ddof=0 = sqrt(2)
    assert sd(np.array([1, 2, 3, 4, 5])) == pytest.approx(np.sqrt(2))


def test_wl_total_variation():
    # WL = sum of absolute consecutive differences
    # [1, 3, 2, 5] -> |3-1| + |2-3| + |5-2| = 2 + 1 + 3 = 6
    assert wl(np.array([1, 3, 2, 5])) == pytest.approx(6.0)


def test_wl_constant_signal_is_zero():
    assert wl(np.array([7, 7, 7, 7])) == 0.0


def test_var_is_sd_squared():
    x = np.array([1, 2, 3, 4, 5])
    assert var(x) == pytest.approx(sd(x) ** 2)
