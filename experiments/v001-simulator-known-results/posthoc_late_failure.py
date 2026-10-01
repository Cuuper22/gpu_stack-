"""POST-HOC re-analysis (not frozen).  Stage 2 check C2 counted 24 'late_failure_error' cases.
Cause: the harness appended a failure at end+5 ns even when the trace already held a later
failure, so FailureTrace correctly refused overlapping intervals.  This re-runs exactly those
cases with the extra failure placed after every existing failure."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_ckpt as K, ckpt_driver as D

out = {"invalid_inputs": 0, "rechecked": 0, "changed": 0, "engine_error": 0}
om = K._metamorphic
def wrap(sc, tr, run):
    late = tr + [(run.end_ns + 5, run.end_ns + 9)]
    last = max([r for _, r in tr], default=0)
    if last > run.end_ns + 5:
        out["invalid_inputs"] += 1
        t0 = max(last, run.end_ns) + 5
        try:
            r2 = D.run_engine(sc, tr + [(t0, t0 + 4)], 10 ** 15)
            out["rechecked"] += 1
            out["changed"] += int(r2.wall_ns != run.wall_ns or
                                  r2.runtime.work_ledger.ledger_digest != run.runtime.work_ledger.ledger_digest)
        except Exception:  # noqa: BLE001
            out["engine_error"] += 1
    return om(sc, tr, run)
K._metamorphic = wrap
for k in (1, 2, 3, 5):
    K.accounting_suite(seed=20261001 + 2000 + k, n_random=200, n_boundary=120, ks=(k,))
(HERE / "results" / "accounting_posthoc_late_failure.json").write_text(json.dumps(out, indent=1))
print(out)
