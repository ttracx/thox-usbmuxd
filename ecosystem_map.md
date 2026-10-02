# THOX USB POC ecosystem map

Updated: 2026-10-02. Scope: experimental wired connection between a computing ThoxMini and a foreground iOS companion.

The customer experience remains: choose a THOX device, use ThoxOS, connect authorized resources through MeshStack, and organize work through ThoxWork when available.

| Component | Role in this POC | Delivery boundary |
|---|---|---|
| ThoxMini | USB host, connection initiator, durable job store, qualified executor | Hardware role/power/OS compatibility require bench validation |
| ThoxOS iOS | User's device and workflow interface | Standalone SwiftUI POC; existing app integration pending |
| usbmuxd + iproxy | Experimental host-to-iPhone socket transport | Upstream dependency; no production iOS support guarantee |
| THOX application protocol | Pairing, encrypted requests/responses, job status and cancellation | POC design; independent security review pending |
| TXF | Shared connection states, executor disclosure, eventual app presentation | Integration target; full TXF adoption not claimed |
| MeshStack | Potential later routing to explicitly authorized resources | No automatic enrollment, delegation, or broadened authority in this slice |
| ThoxBeam inside ThoxOS | Portable runtime engine engineered for ThoxKey | Separate from this Mini transport; no iOS port implemented here |
| ThoxKey | Future user-selected external workspace/model storage path | Roadmap only; storage device is not a usbmuxd host |
| ThoxWork / THOXY | Future workflow surfaces above the device-session service | No workspace or agent-platform integration in this POC |

Workload execution, transport selection, and workflow authority remain separate concerns. A connected device does not automatically authorize a cloud provider, another device, a filesystem path, or a tool.

See [architecture](poc/docs/ARCHITECTURE.md), [MVP catalog](mvp_catalog.md), and [development queue](development_queue.md).
