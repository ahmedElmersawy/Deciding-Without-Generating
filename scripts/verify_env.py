#!/usr/bin/env python3
"""Verifies the pinned `dwg` conda env on a GPU node before any harness code is written.

Run via `sbatch scripts/verify_env.slurm` (which activates the env + exports first) —
running this file directly, without that wrapper, will fail the CUDA checks by design.

Three checks, in order (each PASS/FAIL, first failure aborts):
  1. `import sqlite3`            — stdlib build sanity (CentOS7 system python is 3.9; the
                                    conda 3.12 build must have sqlite3 compiled in).
  2. `torch.cuda.is_available()` — the CXXABI_1.3.15 / driver / CUDA toolkit chain works.
  3. one-token vLLM generation on facebook/opt-125m — the smallest model that exercises the
     full serving path (weight download to HF_HOME, kernel compilation, sampling).
"""
import sys


def check_sqlite3():
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.execute("SELECT 1")
    conn.close()
    return sqlite3.sqlite_version


def check_cuda():
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("torch.cuda.is_available() is False")
    return f"torch={torch.__version__} cuda={torch.version.cuda} device={torch.cuda.get_device_name(0)}"


def check_vllm_generate():
    from vllm import LLM, SamplingParams
    llm = LLM(model="facebook/opt-125m", gpu_memory_utilization=0.5, max_model_len=64)
    out = llm.generate(["Hello,"], SamplingParams(max_tokens=1, temperature=0.0))
    text = out[0].outputs[0].text
    if not isinstance(text, str):
        raise RuntimeError(f"unexpected vLLM output: {out!r}")
    return f"generated {text!r}"


CHECKS = [
    ("sqlite3", check_sqlite3),
    ("torch.cuda", check_cuda),
    ("vllm 1-token generate (facebook/opt-125m)", check_vllm_generate),
]


def main():
    for name, fn in CHECKS:
        try:
            detail = fn()
        except Exception as e:  # noqa: BLE001 - report and abort, don't continue past a failure
            print(f"FAIL  {name}: {e}")
            sys.exit(1)
        print(f"PASS  {name}: {detail}")
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
