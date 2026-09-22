#!/usr/bin/env python3
"""Probe outbound reachability of every external service the benchmark uses.

Stdlib only (runs on the system python3.9 with no env). Any HTTP response
(even 401/403/404) counts as REACHABLE: we test the network path, not auth.

Run on a login node:    python3 scripts/check_connectivity.py
Run on a compute node:  srun -A <acct> -p a100-80gb -t 00:05:00 --pty \
                            python3 scripts/check_connectivity.py
Behind a proxy:         HTTPS_PROXY=http://<host>:<port> python3 scripts/check_connectivity.py
Exit code 0 = all reachable, 1 = at least one unreachable.
"""
import json, os, socket, sys, time, urllib.error, urllib.request

TARGETS = {
    "jev/typesafe": "https://api.typesafe.ai/v1/systemone",  # POST-only; GET -> 4xx still proves reachability
    "openai": "https://api.openai.com/v1/models",
    "anthropic": "https://api.anthropic.com/v1/models",
    "google": "https://generativelanguage.googleapis.com/",
    "huggingface": "https://huggingface.co/api/models/Qwen/Qwen3-8B",
    "pypi": "https://pypi.org/simple/pip/",
}


def probe(url, timeout=10.0):
    t0 = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=timeout) as r:
            return True, r.status, time.time() - t0, ""
    except urllib.error.HTTPError as e:  # server answered => network path OK
        return True, e.code, time.time() - t0, ""
    except (urllib.error.URLError, socket.timeout, OSError) as e:
        return False, None, time.time() - t0, str(getattr(e, "reason", e))


def main():
    print(f"host={socket.gethostname()} slurm_job={os.environ.get('SLURM_JOB_ID', '-')} "
          f"proxy={os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy') or '-'}")
    results, ok_all = {}, True
    for name, url in TARGETS.items():
        ok, code, dt, err = probe(url)
        ok_all &= ok
        results[name] = dict(reachable=ok, http=code, seconds=round(dt, 2), error=err)
        print(f"{'PASS' if ok else 'FAIL':4}  {name:14} http={code} {dt:5.2f}s {err}")
    print(json.dumps(results))
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
