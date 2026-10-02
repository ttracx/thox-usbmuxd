# Development queue

Updated: 2026-10-02. Repository source delivery and physical validation are tracked separately. No completed state below substitutes for test/build evidence.

See [validation](poc/VALIDATION.md), [agent handoffs](poc/handoffs/START_HERE.md), and the [task graph](poc/handoffs/tasks.json). Software results below refer to commit `af3372806f01a572f08105552f6072af0a2c4de2`.

| ID | Task | Owner role | State | Acceptance |
|---|---|---|---|---|
| Q01 | Fork upstream and preserve licenses/source history | Repository maintainer | DONE | Fork lineage verified; upstream source and notices retained |
| Q02 | Add Mini session agent and durable jobs | Backend engineer | Implemented; software PASS | 34 Python tests and actual CLI loopback/reconnect demo pass |
| Q03 | Add standalone native iOS companion | iOS engineer | Implemented; unsigned compile PASS | Xcode 26.5 simulator build passes; runtime/device checks remain |
| Q04 | Run local automated tests and review output | Validation owner | PASS: 34 Python + 11 Swift | Commands, environment and results recorded in VALIDATION.md |
| Q05 | Compile and install signed iOS development build | iOS release owner | Signed phone install NOT RUN | Unsigned simulator build passed; selected phone needs signed install evidence |
| Q06 | Qualify Mini USB role, cable, and power path | Hardware engineer | NOT RUN | B01–B04 pass in bench record |
| Q07 | Validate pairing, workload, reconnect, lifecycle | Joint iOS/backend owner | NOT RUN | B05–B15 pass with failures documented |
| Q08 | Qualify optional real inference | Model/runtime engineer | NOT RUN | B16 records model, memory, latency, and actual output |
| Q09 | Integrate service and TXF states into existing ThoxOS | ThoxOS app owner | Discovery ready; customer enablement pending Q05–Q07 and Q12 | Existing app build/test gate, correct executor disclosure |
| Q10 | Add Wi-Fi transport for same bounded workflow | Connectivity engineer | Proposed | Same acceptance contract over supported networking |
| Q11 | Evaluate qualified USB Ethernet route | Connectivity/hardware owner | Proposed | Specific phone/firmware/cable test matrix |
| Q12 | Review protocol, key lifecycle, and at-rest policy | Security reviewer | Pending before production | Findings resolved; no unauthenticated downgrade |
| Q13 | Plan native ThoxKey storage/runtime slice | ThoxBeam/iOS owners | Roadmap | User-selected files, signed app runtime, model compatibility plan |
| Q14 | Exercise live Python-to-Swift network session | QA and iOS owners | NOT RUN | Real implementations interoperate, reject invalid sessions, and recover the same job |

## Working rules

Maintain `poc/PROTOCOL.md` alongside behavior changes. Record failures explicitly. Avoid duplicate job submission after uncertainty; reconnect and query known job IDs. Do not add cloud fallback or new workflow authority as a transport fix. Run validation locally; no GitHub Actions is required.

## Current qualification boundary

USB bench checks, signed iOS distribution, TestFlight upload, existing ThoxOS integration, and actual model performance have not been established by source delivery. Update this file only after collecting corresponding evidence.
