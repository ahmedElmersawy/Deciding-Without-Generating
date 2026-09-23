from types import SimpleNamespace

import pytest

from dwg.energy import EnergyUnavailable, GpuEnergyMeter


def _meter(power_mw, mj_per_read):
    """A meter whose counter advances `mj_per_read` on every read, against a fixed NVML power."""
    counter = {"mj": 0}

    def total_energy(_handle):
        counter["mj"] += mj_per_read
        return counter["mj"]

    m = GpuEnergyMeter.__new__(GpuEnergyMeter)
    m._handle = None
    m.device_name = "fake"
    m._nvml = SimpleNamespace(nvmlDeviceGetTotalEnergyConsumption=total_energy,
                              nvmlDeviceGetPowerUsage=lambda _h: power_mw)
    return m


def test_validate_rejects_a_counter_that_runs_away_under_polling():
    # The RTX 3050 Ti laptop case: ~700 W implied vs ~9 W reported.
    with pytest.raises(EnergyUnavailable, match="implausible"):
        _meter(power_mw=9_000, mj_per_read=5_000).validate(seconds=0.05)


def test_validate_accepts_a_plausible_counter():
    assert _meter(power_mw=250_000, mj_per_read=0).validate(seconds=0.05) >= 0
