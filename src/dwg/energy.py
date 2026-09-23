"""GPU energy per decision for LOCAL deciders (Kev, Qwen3, classifier) — DECISIONS.md 2026-09-23.

Reads NVML's cumulative energy counter (`nvmlDeviceGetTotalEnergyConsumption`, mJ, Volta+)
before and after each call, which is exact over the call window, unlike ~10 Hz power polling
(CHECKS.md #8) that can't resolve 100–500 ms calls.

What the number means, and doesn't:
- It is WHOLE-GPU energy, not per-process: the local decider must be the only thing on the
  GPU (Slurm `--exclusive` on Gilbreth), and its calls must be serialized — replay holds a
  lock around every call to a decider that has an energy meter.
- It is GROSS energy over the call window, idle draw included. `idle_watts()` measures the
  idle baseline so analysis can also report NET = gross - idle_W * latency.
- Hosted deciders (Jev, frontier LLMs) have no energy number: `N/A (hosted)`.
- The counter steps every ~100 ms, so a single 100 ms call catches 0 or 1 steps: per-call values
  are noisy. The headline J/decision is the BLOCK measure — counter delta over a contiguous run
  of back-to-back calls, divided by the call count — which is exact regardless of step size.
- `validate()` must pass before trusting the counter at all. Found 2026-09-23 on an RTX 3050 Ti
  Laptop GPU (driver 580.173.02): read across a 5 s sleep it gives a plausible 11 W, but read in
  a tight loop it accumulates ~730 W — physically impossible. Datacenter GPUs (A100) document
  this counter as accurate, but the check runs everywhere rather than assuming.
"""

from __future__ import annotations

import time
from typing import Optional


class EnergyUnavailable(RuntimeError):
    """No NVIDIA GPU / NVML, or this GPU has no energy counter."""


class GpuEnergyMeter:
    def __init__(self, device_index: int = 0) -> None:
        try:
            import pynvml
        except ImportError as exc:  # nvidia-ml-py not installed
            raise EnergyUnavailable("nvidia-ml-py is not installed") from exc
        try:
            pynvml.nvmlInit()
            self._handle = pynvml.nvmlDeviceGetHandleByIndex(device_index)
            pynvml.nvmlDeviceGetTotalEnergyConsumption(self._handle)
        except pynvml.NVMLError as exc:
            raise EnergyUnavailable(f"NVML energy counter unavailable: {exc}") from exc
        self._nvml = pynvml
        self.device_name = pynvml.nvmlDeviceGetName(self._handle)
        if isinstance(self.device_name, bytes):
            self.device_name = self.device_name.decode()

    def read_mj(self) -> int:
        """Cumulative GPU energy since driver load, in millijoules."""
        return self._nvml.nvmlDeviceGetTotalEnergyConsumption(self._handle)

    def validate(self, seconds: float = 1.0, tolerance: float = 3.0) -> float:
        """Poll the counter tightly for `seconds`; the implied watts must be plausible against
        NVML's own instantaneous power reading. Returns the implied watts, or raises."""
        reference_w = self._nvml.nvmlDeviceGetPowerUsage(self._handle) / 1000.0
        e0, t0 = self.read_mj(), time.perf_counter()
        while time.perf_counter() - t0 < seconds:
            self.read_mj()
        implied_w = (self.read_mj() - e0) / 1000.0 / (time.perf_counter() - t0)
        if implied_w > tolerance * reference_w + 20.0:
            raise EnergyUnavailable(
                f"energy counter implausible on {self.device_name}: {implied_w:.0f} W implied under polling "
                f"vs {reference_w:.1f} W reported by NVML power usage"
            )
        return implied_w

    def idle_watts(self, seconds: float = 5.0) -> float:
        """Average draw over `seconds` with nothing running — call it before a run."""
        e0, t0 = self.read_mj(), time.perf_counter()
        time.sleep(seconds)
        return (self.read_mj() - e0) / 1000.0 / (time.perf_counter() - t0)


def try_energy_meter(device_index: int = 0) -> tuple[Optional[GpuEnergyMeter], Optional[str]]:
    """(meter, None) if the counter exists and passes `validate()`, else (None, reason)."""
    try:
        meter = GpuEnergyMeter(device_index)
        meter.validate()
        return meter, None
    except EnergyUnavailable as exc:
        print(f"!! GPU energy not measured: {exc}")
        return None, str(exc)
