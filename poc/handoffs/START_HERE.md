# Agent handoff: finish and integrate the THOX USB POC

Repository: https://github.com/ttracx/thox-usbmuxd  
Default branch: `master`  
Implemented baseline: `af3372806f01a572f08105552f6072af0a2c4de2`  
Upstream baseline: `3ded00c9985a5108cfc7591a309f9a23d57a8cba`  
Handoff date: 2026-10-02

The POC exists and is published. This pack assigns the remaining native-device,
hardware, security, and product integration work. It does not claim those tasks
have been completed. Start from the latest fork `master`, retain the baseline
above for comparison, and read [current validation](../VALIDATION.md).

## What is already implemented

- Linux/Python Mini host connecting through loopback iproxy to an iOS listener.
- Mutual shared-key authentication, directional encrypted messages, strict framing and replay rejection.
- Durable SQLite jobs with client-known submission IDs, duplicate submission protection, cancellation and reconnect recovery.
- Deterministic text analysis; optional fixed loopback model endpoint with a bounded client subprocess.
- Standalone SwiftUI iOS app with document selection, Keychain pairing, job controls and result sharing.
- 34 passing Python tests and 11 passing Swift protocol tests, including the shared Python/CryptoKit vector.
- Hardware-free demo exercising the real Python CLI bridge. A simulated iOS peer is used in that demo.

This is an application transport/workflow POC. There is no Mini flash image,
existing ThoxOS integration, production key enrollment, or qualified phone
compatibility matrix in this delivery. Check VALIDATION.md for the latest native
compile result and remaining physical gates.

## Assignments

| Agent | Handoff | Owns | Depends on |
|---|---|---|---|
| Coordinator | This file and tasks.json | Branch integration, evidence, target discovery | None |
| iOS | [01_ios_companion.md](01_ios_companion.md) | Native app, lifecycle, signed development install | POC baseline |
| Mini firmware | [02_mini_host_firmware.md](02_mini_host_firmware.md) | Host packaging, supervised services, USB/power bench | POC baseline |
| ThoxOS integration | [03_thoxos_integration.md](03_thoxos_integration.md) | Existing app adapter and TXF presentation | iOS compile; can discover target immediately |
| Security/protocol | [04_security_protocol.md](04_security_protocol.md) | Key lifecycle, protocol review, data boundaries | POC baseline |
| QA/release | [05_qa_release.md](05_qa_release.md) | Cross-language live test, real USB matrix, release evidence | Software QA ready now; iOS + Mini for bench; integration + security before distribution |
| Transport/Key roadmap | [06_transport_thoxkey_roadmap.md](06_transport_thoxkey_roadmap.md) | Wi-Fi, USB Ethernet, native Key storage design | Core service contract; each is a separate slice |

Run iOS, Mini, security, integration discovery and software QA in parallel. Merge contract
changes through one coordinator so both languages and fixtures change together.
The shared hardware acceptance gate follows the iOS and Mini work. Product
integration can proceed behind an experimental feature flag, but enabling it
for customers requires the integrated app's own tests and device evidence.

In tasks.json, `depends_on` gates the start of work; `completion_requires` gates
final acceptance. A ready task's `ready_scope` defines what can begin while its
completion prerequisites remain open.

## First coordinator actions

1. Clone the fork, read AGENTS.md, record current SHA and clean working tree.
2. Resolve the active ThoxOS iOS repository/build target and the current Mini image repository from their source and release owner. Do not infer the target from a similarly named repository. Record internal mappings only in an authorized private workspace.
3. Claim tasks in [tasks.json](tasks.json) with a branch and owner. Shared contract edits require coordination.
4. Check Mac build ownership before starting Xcode. Use a separate checkout and DerivedData; do not stop existing builds/uploads.
5. Collect real-device evidence before describing USB connectivity as validated.

## Copy-paste coordinator prompt

```text
Continue the THOX USB POC at https://github.com/ttracx/thox-usbmuxd.
Read AGENTS.md, poc/handoffs/START_HERE.md, poc/VALIDATION.md and
poc/handoffs/tasks.json. Start from current master and record its SHA.
The implemented baseline is af3372806f01a572f08105552f6072af0a2c4de2.
Assign the six bounded handoffs to separate agents and isolate their branches.
Resolve the active ThoxOS iOS and Mini provisioning targets from live source;
keep private target details out of this public fork. Preserve upstream licenses.
Run native and hardware gates without interrupting another build/release owner.
Integrate the shared service through existing ThoxOS/TXF device and job surfaces.
Do not describe a mock, unsigned compile, or simulator result as real USB evidence.
Update the task graph, development queue and validation evidence after each merge.
Return actual commit/PR URLs, exact test outcomes, device matrix, and remaining blockers.
```

## Shared acceptance workflow

Pair a qualified Mini and phone, open the signed app, import a small plain-text
document, submit analysis with its UUID saved before transmission, observe the
Mini result, disconnect, reconnect and retrieve the same job. Repeat while the
app backgrounds/returns and while the host restarts. Verify a wrong pairing key
fails without submitting work. Run inference only after identifying the actual
local model/runtime and recording its resource and performance results.

## Completion report required from every agent

```text
Task/owner/branch:
Starting SHA / final SHA / PR:
Owned files changed:
Behavior delivered:
Commands + exit codes + test counts:
Device/OS/build/runtime versions (if used):
Evidence paths (redacted; no keys or user documents):
Known limitations and exact remaining blocker:
Next dependent task:
```

Use `poc-v0.1.0` for the POC prerelease tag namespace; upstream already has a
`v0.1.0` tag. Never overwrite upstream tags to label THOX work.
