# Development queue

Updated: 2026-10-02. Repository source delivery and physical validation are tracked separately. No completed state below substitutes for test/build evidence.

| ID | Task | Owner role | State | Acceptance |
|---|---|---|---|---|
| Q01 | Fork upstream and preserve licenses/source history | Repository maintainer | Delivery in progress | GitHub fork exists; upstream lineage and notices retained |
| Q02 | Add Mini session agent and durable jobs | Backend engineer | Source implementation | Local protocol/job/error tests pass at recorded commit |
| Q03 | Add standalone native iOS companion | iOS engineer | Source implementation | Xcode compile, install, and device validation still required |
| Q04 | Run local automated tests and review output | Validation owner | Pending recorded evidence | Command/environment/results attached to delivery |
| Q05 | Compile and install signed iOS development build | iOS release owner | NOT RUN | Recorded Xcode build and install on selected phone |
| Q06 | Qualify Mini USB role, cable, and power path | Hardware engineer | NOT RUN | B01–B04 pass in bench record |
| Q07 | Validate pairing, workload, reconnect, lifecycle | Joint iOS/backend owner | NOT RUN | B05–B15 pass with failures documented |
| Q08 | Qualify optional real inference | Model/runtime engineer | NOT RUN | B16 records model, memory, latency, and actual output |
| Q09 | Integrate service and TXF states into existing ThoxOS | ThoxOS app owner | Pending Q05–Q07 | Existing app build/test gate, correct executor disclosure |
| Q10 | Add Wi-Fi transport for same bounded workflow | Connectivity engineer | Proposed | Same acceptance contract over supported networking |
| Q11 | Evaluate qualified USB Ethernet route | Connectivity/hardware owner | Proposed | Specific phone/firmware/cable test matrix |
| Q12 | Review protocol, key lifecycle, and at-rest policy | Security reviewer | Pending before production | Findings resolved; no unauthenticated downgrade |
| Q13 | Plan native ThoxKey storage/runtime slice | ThoxBeam/iOS owners | Roadmap | User-selected files, signed app runtime, model compatibility plan |

## Working rules

Maintain `poc/PROTOCOL.md` alongside behavior changes. Record failures explicitly. Avoid duplicate job submission after uncertainty; reconnect and query known job IDs. Do not add cloud fallback or new workflow authority as a transport fix. Run validation locally; no GitHub Actions is required.

## Current qualification boundary

USB bench checks, signed iOS distribution, TestFlight upload, existing ThoxOS integration, and actual model performance have not been established by source delivery. Update this file only after collecting corresponding evidence.
