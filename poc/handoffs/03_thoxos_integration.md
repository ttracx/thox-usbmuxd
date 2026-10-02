# Agent handoff 03 — Integrate the qualified transport into ThoxOS

## Source and outcome

- Reference repository: https://github.com/ttracx/thox-usbmuxd
- Reference branch: `master`
- Source baseline: `af3372806f01a572f08105552f6072af0a2c4de2`
- Component: `poc/ios/`; protocol: `poc/PROTOCOL.md`.
- Destination: the **existing native ThoxOS iOS repository and target, to be discovered and verified**. No destination path, branch, project or target is assumed by this handoff.

Integrate one complete ThoxOS vertical slice: select a text document → explicitly send a bounded task to an authenticated ThoxMini → show execution status → retrieve and share its result → reconnect to the same durable job after interruption. Keep USBMux visibly experimental until real hardware qualification supports wider release.

The coordinator recorded **PASS: all 11 Swift protocol tests**, including the shared Python/CryptoKit fixture, and **PASS: unsigned simulator build, exit 0**, on baseline `af3372806f01a572f08105552f6072af0a2c4de2`, using Xcode 26.5 / iPhoneSimulator SDK 26.5 for arm64 and x86_64. See `poc/VALIDATION.md` for evidence. Simulator UI/runtime validation, native signing and physical USB qualification remain **NOT RUN**. These passes apply to the reference companion; they do not establish that the undiscovered destination app builds or that physical USB works.

## Discover the real destination first

1. Use the authorized GitHub connection or existing checked-out repositories to locate the maintained **native ThoxOS iOS app**. Similar names can refer to web, desktop, USB-drive or Mini editions; verify the app entry point and iOS target before selecting one.
2. Read repository-local `AGENTS.md` and release/build coordination guidance. In an authorized private integration record, capture repository URL, default branch, checkout path, current commit, dirty work and the person/agent owning its Xcode window. Keep internal repository names, paths and mappings out of this public fork.
3. Find the existing app entry point, scene lifecycle, Devices navigation, document workspace/import flow, task/approval store, provider or device registry, credential store, TXF modules/assets and target tests. Use the repository's actual conventions.
4. Record the destination paths in the private evidence block before writing files. The destination may already have suitable abstractions; reuse them rather than adding a competing device or navigation system.

Useful read-only commands from the discovered checkout:

```sh
git status --short
git remote -v
git rev-parse HEAD
rg --files -g AGENTS.md -g Package.swift -g project.yml -g '*.pbxproj' -g '*.xcscheme'
rg -n '@main|scenePhase|DeviceState|TXF|Keychain|fileImporter|UIDocumentPicker|approval|provider' --glob '*.swift'
```

Remote URLs and build logs should be reviewed for embedded credentials before sharing. Do not paste tokens or pairing keys into evidence.

## Extract and adapt these boundaries

| Reference source | Integration responsibility | Preserve |
| --- | --- | --- |
| `poc/ios/Sources/THOXWire/` and `Package.swift` | A small version-pinned protocol module consumed by the native target | Canonical PSK format; HMAC/HKDF/AES-GCM bytes; 1 MiB frame limit; duplicate-key rejection; sequence semantics |
| `Services/USBListener.swift` | Adapter behind the existing device transport boundary, or a narrow new boundary if none exists | Host-initiated connection; loopback port 49321; one connection; handshake deadline; queue confinement |
| `Stores/PairingKeyStore.swift` | Existing credential-store adapter with a dedicated device credential namespace | `WhenUnlockedThisDeviceOnly`; no iCloud sync or plaintext preference storage; explicit revocation |
| `Models/LabModel.swift` | Map state and operations into the real ThoxOS device/job stores | Persist submit UUID before send; explicit submit; no automatic resubmit; status/get/cancel behavior; foreground lifecycle |
| `Views/ContentView.swift` | Use as a behavior reference and map controls into existing TXF views | Honest mode/executor text, selection scope, progress, recovery and result sharing |
| `Tests/THOXWireTests/` and the shared fixture | Keep executable compatibility evidence with the integrated module | Both HMACs, both derived keys, directional ciphertext, replay/tamper/framing failure tests |

Prefer a pinned local Swift package or the destination's established vendoring policy. Do not add the reference `@main` app type to the shipping target. Do not copy `LabModel` wholesale into an unrelated singleton when the app already has an appropriate state store. Avoid importing the lab's bundle ID, signing settings or standalone navigation shell into production.

The reference additions carry `GPL-3.0-or-later` notices. Preserve notices and record the destination's license/distribution compatibility decision before merging copied code into a release target. This handoff does not grant a different license or assert App Store distribution clearance.

## Required ThoxOS and TXF surfaces

Use the actual TXF tokens, components, fonts, spacing, accessibility and device-state contracts found in the destination. The lab uses system fonts and a provisional emerald/ink appearance; it is not a complete TXF implementation.

| Surface | Required behavior |
| --- | --- |
| Devices | Entry for the selected ThoxMini; experimental USB connection option; clear disconnected, waiting, authenticating, connected, paused and failed states |
| Pairing | Explain the selected device, import a trusted pairing key, show success without showing the key, and provide forget/revoke; authentication must not imply permission to read all files |
| Selected input | Show filename and byte count, allow changing the selection, enforce UTF-8 and 65,536-byte limit, and send nothing until the explicit task action |
| Execution location | Identify Mini as the task executor and label optional inference accurately; reflect actual capabilities and operator configuration, with no automatic cloud fallback |
| Task choice | Deterministic text analysis clearly distinguished from optional model inference; hide/disable unsupported inference |
| Submission / approval | Connect the explicit send action to the existing approval/task flow where present. Preserve selected-file scope; this POC introduces no generic shell, arbitrary path, endpoint override or model-controlled permission |
| Progress | Pending requests and durable queued/running/completed/failed/cancelled job state; actionable errors; cancel semantics that do not claim to stop remote provider computation already underway |
| Results | Return the job result to the originating task/workspace; share/export only on user action. Do not overwrite the source document |
| Recovery | Persist job ID before send; reconnect with fresh session keys; get the same job; never silently replay a lost submission |
| Revocation / lifecycle | Forgetting a key ends the session. Backgrounding closes the listener; returning can reestablish it. Existing accepted jobs remain on Mini |

Selected input already uses SwiftUI `.fileImporter` with `.plainText`, a security-scoped URL and a bounded read. Reuse the current workspace's selection mechanism when equivalent. A supported external drive may be selected through the system document provider, but this does not establish arbitrary raw-USB access or a ThoxKey executable-launch path. Do not conflate ThoxKey storage selection with Mini's host-initiated USBMux transport.

The reference persists one job ID in `THOXUSBLab.lastJobID`. A real multi-device workspace should persist a mapping scoped to the chosen device identity and workflow owner, using the application's existing store. Define that mapping before enabling more than one paired Mini. Do not reuse one last-job preference across all devices.

## Owned files and overlap rules

The integration agent owns only the discovered destination files listed in its private integration plan, plus a redacted public status summary. Keep those paths explicit in the private plan before parallel work begins. The standalone companion owner retains `poc/ios/**`; the host/protocol owner retains `poc/host/**`, `poc/PROTOCOL.md`, shared fixtures and Python tests. Pull the qualified companion revision instead of editing both copies independently.

Do not modify upstream usbmuxd source, unrelated native applications, other active release branches, signing credentials, App Groups, APNs settings, production model endpoints or deployment secrets. Do not introduce GitHub Actions. Do not interrupt another Xcode job. Existing app tests and archive gates must remain owned and coordinated through the destination's release workflow.

Protocol changes require coordinated host and iOS updates plus fresh interoperability evidence. Full TXF refactors, BLE/Wi-Fi fallback implementation, ThoxKey native inference, model installation and production multi-device trust design are separate slices; record them in the existing backlog rather than expanding this task silently.

## Implementation sequence

1. Complete destination discovery and record the exact base revision and file ownership.
2. Receive the qualified iOS module revision and evidence from handoff 01. Resolve open compiler/security defects before consumption.
3. Add the protocol module without the lab app target. Run its baseline package tests unchanged.
4. Adapt listener and Keychain access behind native interfaces. Add an experimental connection option to the existing Devices surface; preserve current default transport behavior.
5. Map device and job state to existing TXF/task contracts. Add explicit selected-file submission, executor display, result return, cancel and reconnect recovery as one end-to-end slice.
6. Add focused integration tests for permission scope, device-specific saved job IDs, background lifecycle and lost-response recovery. Reuse the shared wire fixture.
7. Run the discovered target's existing focused test/build commands in a coordinated Mac window. Record real target/scheme names; do not substitute `ThoxUSBLab` for evidence about shipping ThoxOS.
8. Qualify one signed-device physical USB workflow with the hardware owner and document exact device/cable/power versions.
9. Update the destination's `ecosystem_map.md`, `mvp_catalog.md` and `development_queue.md` where maintained, plus release/handoff notes. Report exact commits, changed paths, evidence and remaining gates to the coordinator.

## Reference gates

These commands validate the **reference companion**, not the undiscovered destination app. Run from the reference repository root after the build window is handed over:

```sh
swift test --package-path poc/ios --scratch-path /tmp/thox-wire-integration-agent
xcodebuild -project poc/ios/ThoxUSBLab.xcodeproj \
  -scheme ThoxUSBLab \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath /tmp/thox-usblab-integration-agent \
  CODE_SIGNING_ALLOWED=NO build
```

For the destination, discover the actual workspace/project and scheme and record its exact commands in the evidence block. Follow its established signing and archive process only when the release owner hands off that gate. No TestFlight submission is implied by an unsigned simulator build.

## Acceptance criteria

- The destination repository/target and base commit are verified, with focused file ownership and preserved unrelated work.
- Baseline wire tests pass unchanged, and the existing native app's relevant tests/build pass on the integrated commit.
- USB transport appears in the existing ThoxOS Devices/workspace flow with actual TXF components and accessible states.
- The user selects a bounded document and explicitly authorizes transmission; no content is sent during selection or pairing.
- One task produces one durable job; the result returns to the originating workflow; backgrounding or cable loss does not cause automatic resubmission.
- Credential revocation ends the local session; no pairing secret appears in preferences, logs, analytics or screenshots.
- Execution location and analysis/inference labels match actual behavior. No automatic cloud fallback or expanded tool authority is introduced.
- Hardware, native signing and release status remain explicitly evidence-based. A source merge does not certify production USB compatibility.

## Private evidence template

Copy this template into the authorized private destination workspace. Do not commit the populated template to this public fork. A public update may report gate outcomes, test counts, the public companion revision, and an opaque internal evidence identifier approved for disclosure. Exclude private repository names/URLs, checkout paths, target mappings, credentials and raw internal logs.

```text
Agent / date:
Reference repo / baseline: https://github.com/ttracx/thox-usbmuxd @ af3372806f01a572f08105552f6072af0a2c4de2
Qualified companion revision / upstream evidence: af3372806f01a572f08105552f6072af0a2c4de2; 11 Swift tests and unsigned simulator build PASS — see poc/VALIDATION.md
Destination repo / branch / checkout:
Destination base commit / integrated commit:
Discovered native workspace/project / target / scheme:
Discovered TXF package/assets / task store / device registry:
Owned destination files / excluded concurrent ownership:
License notices preserved / distribution decision recorded:
Swift wire tests command / exit code / log:
Destination tests command / exit code / log:
Destination unsigned build command / exit code / log:
Selected input / explicit-send / execution-location evidence:
Device-scoped job ID / background / lost-ack recovery evidence:
Signing: NOT RUN | FAIL | PASS — evidence:
Physical USB: NOT RUN | FAIL | PASS — hardware/topology/evidence:
TestFlight/release: NOT RUN | FAIL | PASS — evidence:
Documentation updates / open gates / next owner:
```

## Copy-paste kickoff prompt

```text
Integrate the qualified ThoxMini USB companion slice into the existing native ThoxOS iOS app. Reference: https://github.com/ttracx/thox-usbmuxd, branch master, source baseline af3372806f01a572f08105552f6072af0a2c4de2. Read poc/handoffs/03_thoxos_integration.md and discover the real destination repository, iOS target, TXF components, device registry, workflow store and file-selection path before editing. Do not invent a destination path or target. Obtain handoff 01's tested revision/evidence, then adapt THOXWire, USBListener, Keychain and state handling into the existing architecture without copying the standalone @main app. Own only explicitly listed destination files. Preserve protocol bytes, scoped file selection, explicit send, executor disclosure, persisted submission UUID, no automatic replay, foreground lifecycle and revocation. Retain license notices and record distribution compatibility. Coordinate Xcode usage; do not overlap another release job, add GitHub Actions, change credentials or send external messages. Run actual destination tests/build and report exact commits, commands, exit codes and evidence. Signing/hardware/release remain NOT RUN until separately executed. Deliver one coherent Devices-to-result workflow and update the existing ecosystem/MVP/backlog documents.
```
