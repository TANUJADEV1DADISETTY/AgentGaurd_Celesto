# Post-Mortem: Reliability Evaluation

## Summary

| Metric | Value |
|--------|-------|
| Total runs | 22 |
| Successes | 19 |
| Failures | 3 |
| Success rate | 86.4% |
| Median wall-clock | 0.2180 s |
| p90 wall-clock | 0.2500 s |
| Median boot-to-ready | 0.0470 s |
| Total cost | $0.00002005 USD |

## Failure Analysis

### Intentional Failures (testing recovery path)

3 of the 22 runs were **deliberately injected** at step 7 (runs 10, 15, 20)
to exercise and verify the rollback recovery policy. These are not genuine agent failures;
they confirm that the `MidTaskFailure → rollback` path works correctly in production.

Each injected failure triggered:
1. A `step_failed` event in `reports/failure_trace.jsonl`
2. A `policy_applied` event with `policy=rollback`
3. A `snapshot_restored` event confirming the pre-execution state was recovered
4. Sandbox deletion in the `finally` block (cleanup_on_failure=true)

### Genuine Failure Modes (0 observed in this evaluation)

In production at scale, the most likely failure modes would be:

1. **Sandbox boot timeout** — The Celesto microVM takes longer than expected on a
   congested host node. *Mitigation*: increase `SANDBOX_TIMEOUT_S` from 120 to 300,
   add a readiness probe retry loop.

2. **Student code infinite loop** — A tight `while True` loop exhausts the wall-clock
   budget. *Mitigation*: set `ulimit -t 30` inside the VM before running student code;
   add `SIGALRM` to the guest agent.

3. **Disk exhaustion** — A student writes a large file that fills the sandbox root.
   *Mitigation*: set disk quota at sandbox creation; monitor `df` in the safety hook.

4. **Python version mismatch** — Student code uses syntax only available in Python 3.12+
   but the sandbox image ships 3.11. *Mitigation*: parameterize the Python version in the
   sandbox template; add a syntax-check step before execution.

5. **Image pull latency** — On first boot, Celesto downloads the sandbox image (~500 MB).
   *Mitigation*: pre-pull the image before the eval window opens; use a warm-pool of
   pre-booted sandboxes for latency-sensitive workloads.

## Recommendations

1. Add `ulimit -t 30 -v 512000` as a pre-execution step (CPU time + virtual memory cap).
2. Pre-pull sandbox images before recording demo or running the eval.
3. Consider `FreshStart` for failures caused by disk exhaustion (rollback would restore a
   corrupted filesystem in that scenario).
4. Add p95 and p99 percentiles to the reliability report for production SLA tracking.
5. Instrument the safety hook to emit metrics (hook_invocations, hook_blocks) to a
   Prometheus endpoint for real-time monitoring.
