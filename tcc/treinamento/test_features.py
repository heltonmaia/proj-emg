import numpy as np
import pytest

from features import rms


def test_rms_constant_signal():
    # RMS of constant 3 is 3
    assert rms(np.array([3, 3, 3, 3])) == pytest.approx(3.0)


def test_rms_zero_signal():
    assert rms(np.zeros(10)) == 0.0


def test_rms_handles_negative():
    # RMS of [-3, 3] = sqrt((9+9)/2) = 3
    assert rms(np.array([-3, 3])) == pytest.approx(3.0)
