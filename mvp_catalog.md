# MVP catalog

Updated: 2026-10-02. Scores below are proposed planning judgments on a 1–5 scale, where 5 is strongest value, feasibility, fastest delivery, or strategic importance. They are not market research results.

`Priority = (Market Value × 0.4) + (Technical Feasibility × 0.3) + (Time-to-Market × 0.2) + (Strategic Importance × 0.1)`

| ID | Vertical slice | Market | Feasibility | Speed | Strategy | Priority | State |
|---|---|---:|---:|---:|---:|---:|---|
| M1 | Paired Mini/iOS session → bounded analysis job → persistent result | 4 | 4 | 5 | 5 | 4.3 | Source POC; hardware qualification pending |
| M2 | Same workflow over supported Wi-Fi networking | 4 | 5 | 4 | 5 | 4.4 | Proposed follow-on |
| M3 | Existing ThoxOS integration with TXF states and executor disclosure | 5 | 4 | 3 | 5 | 4.3 | Pending app-repository integration |
| M4 | Qualified Mini-local model inference with measured performance | 4 | 3 | 3 | 5 | 3.6 | Optional adapter; model/hardware qualification pending |
| M5 | Qualified USB Ethernet transport for same device-session boundary | 4 | 3 | 3 | 4 | 3.5 | Proposed research and bench work |
| M6 | ThoxKey selected workspace files + native iOS runtime | 4 | 2 | 2 | 4 | 3.0 | Separate roadmap slice |

The requested USB experiment M1 is the active slice even though the preliminary scoring places M2 slightly higher. Complete its bounded evidence before expanding transport scope.

## M1 acceptance

- **Frontend:** foreground companion pairs, shows connection/executor state, submits text, and displays/checks/cancels jobs.
- **Backend:** authenticated bounded messages, durable SQLite job state, explicit errors, reconnect without silent duplicate work.
- **Workload:** deterministic analysis is labelled accurately; optional inference is enabled only by operator configuration.
- **Evidence:** local checks plus the [bench checklist](poc/docs/BENCH_VALIDATION.md) on a named hardware/OS combination.

## Exit to the next slice

Choose M2/M3 once M1 has evidence sufficient to identify transport and lifecycle limits. Choose a model for M4 using measured RAM and latency on the target Mini. Do not treat microSD capacity as model-memory capacity. Keep M6 independent because storage access and USB host connectivity have different architectures.
