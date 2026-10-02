# Agent handoff 01 — Finish and qualify the iOS companion

## Source and objective

- Repository: https://github.com/ttracx/thox-usbmuxd
- Published branch: `master`
- Source baseline: `af3372806f01a572f08105552f6072af0a2c4de2`
- Owned component: `poc/ios/`
- App: **ThoxOS USB Lab**, bundle `ai.thox.thoxos.usblab`, scheme `ThoxUSBLab`, iOS 17 minimum.

Finish the standalone companion and prepare a reproducible hardware qualification run. On baseline `af3372806f01a572f08105552f6072af0a2c4de2`, the coordinating agent recorded **PASS: all 11 Swift tests**, including the shared Python/CryptoKit fixture, and **PASS: unsigned iOS simulator build, exit 0**, using Xcode 26.5 / iPhoneSimulator SDK 26.5 for arm64 and x86_64. See `poc/VALIDATION.md` for the command and log evidence. Simulator UI/runtime validation, native signing and physical hardware qualification remain **NOT RUN**. A build pass does not establish that physical USB works; reuse matching baseline evidence before starting another Xcode job.

## Existing implementation

| Source | Responsibility |
| --- | --- |
| `poc/ios/Sources/THOXWire/` | Strict JSON, incremental length framing, PSK validation, server handshake, directional AES-GCM channel |
| `poc/ios/ThoxUSBLab/Services/USBListener.swift` | Single Network.framework listener at IPv4 loopback `127.0.0.1:49321`; serial queue; 10-second handshake timeout |
| `poc/ios/ThoxUSBLab/Stores/PairingKeyStore.swift` | Generic-password Keychain item; `WhenUnlockedThisDeviceOnly`; save/load/remove |
| `poc/ios/ThoxUSBLab/Models/LabModel.swift` | Foreground lifecycle, request correlation, 15-second request deadlines, selected document, durable job ID, status and result state |
| `poc/ios/ThoxUSBLab/Views/ContentView.swift` | Pairing, listener controls, plain-text file importer, explicit submit, refresh/cancel and ShareLink |
| `poc/ios/ThoxUSBLab/App/ThoxUSBLabApp.swift` | App state ownership and scene-phase forwarding |
| `poc/ios/Tests/THOXWireTests/` | Eleven protocol tests and the copied shared Python cryptographic vector |
| `poc/ios/project.yml`, `poc/ios/scripts/generate_project.py` | Alternative deterministic project generation inputs |
| `poc/ios/ThoxUSBLab.xcodeproj/` | Checked-in project and shared scheme |

Mini initiates the TCP connection through `iproxy`. The iOS app sends application requests only after mutual pairing proof. This is not an iOS HTTP client forwarding requests to a Mini API. Read `poc/PROTOCOL.md` before changing transport code.

The app imports one user-selected nonempty UTF-8 plain-text file of at most 65,536 bytes. A bounded read and security-scoped URL are already implemented. Selection alone does not submit content; the user must press **Send selected text to Mini**. `analyze` returns statistics and SHA-256, with explicit non-LLM labeling. `inference` appears only when advertised by the Mini service.

The lowercased `job_submit` request UUID is saved as the durable job ID **before transmission**. On reconnect, the app requests `status` and `job_get` for that saved ID. It does not resend a submission. Backgrounding stops the socket; returning from background restarts an enabled listener. A transient inactive→active change does not intentionally restart it.

## Owned files and overlap rules

You may edit `poc/ios/**` and append evidence to this handoff. Keep the checked-in Xcode project, `project.yml` and generator consistent if source layout or settings change. Preserve SPDX/license notices.

Do not edit `poc/host/**`, Python tests, `poc/PROTOCOL.md`, shared `poc/fixtures/**`, upstream usbmuxd source, root tracking documents, or shipping ThoxOS files. A protocol mismatch must be reported to the coordinating agent for one coordinated change on both sides. Do not silently change frame limits, proof labels, HKDF info, AAD, sequence semantics or job-ID ownership to make one platform pass.

Coordinate the Apple build window with the existing build owner. Use separate derived-data and Swift build directories. Do not interrupt another archive/export/upload, change signing identities, register bundle IDs, install profiles, or upload to TestFlight as part of the unsigned compile gate. The initial team setting is `DVJ6Z5343U`; it is not evidence that provisioning exists.

## Reproduce the source and build

Use a fresh worktree or checkout; preserve existing work. From a fresh clone:

```sh
git clone --branch master https://github.com/ttracx/thox-usbmuxd.git
cd thox-usbmuxd
git switch -c poc/ios-qualification origin/master
git rev-parse HEAD
```

From the repository root on the coordinated Mac:

```sh
xcodebuild -version
swift --version
swift test --package-path poc/ios --scratch-path /tmp/thox-wire-ios-agent
xcodebuild -project poc/ios/ThoxUSBLab.xcodeproj \
  -scheme ThoxUSBLab \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath /tmp/thox-usblab-ios-agent \
  CODE_SIGNING_ALLOWED=NO build
```

The package can also be tested with `cd poc/ios && swift test`. Tests require Apple CryptoKit; Linux source checks are not an equivalent execution gate. Keep complete command exit codes and log paths. If regeneration is necessary, use one generator intentionally, review its diff, and revalidate the checked-in scheme:

```sh
python3 poc/ios/scripts/generate_project.py
```

## Finish in this order

1. Read `AGENTS.md` wherever present, the baseline source, `poc/PROTOCOL.md`, `poc/VALIDATION.md`, and current `poc/docs/BENCH_VALIDATION.md`.
2. Reuse the coordinator's current compile evidence if it matches the actual commit and source digest. Resolve real compiler errors before expanding the feature scope.
3. Run all eleven Swift protocol tests. The Python vector must match both proof HMACs, both HKDF keys, encrypted server sequence zero and the decrypted ready message. Never update the vector merely to hide a mismatch.
4. Build the simulator target unsigned. Check startup and basic UI separately if a simulator window is assigned; a successful compile alone is not a UI test.
5. Exercise the selected-document path: UTF-8/Unicode, nonempty boundary at 65,536 bytes, oversize rejection, invalid UTF-8, selection cancellation, and no outbound document transfer before submit.
6. Exercise pairing save/load/forget and lifecycle behavior. Ensure secrets are absent from logs, screenshots, test fixtures and preferences. Only the public deterministic fixture belongs in source control.
7. Coordinate the hardware owner for a signed-device bench run. Use the root README and bench plan; record the iPhone/iOS version, Mini board/OS, usbmuxd/iproxy versions, cable topology, USB host/data role and power arrangement.
8. Exercise job submission, refresh, cancellation, cable removal, background/foreground, app restart and lost acknowledgement recovery. Preserve results on Mini and prevent duplicate automatic submissions.
9. Record remaining gaps and pass the validated component revision to the ThoxOS integration owner. The standalone app still needs real brand assets and release packaging before distribution.

## Acceptance criteria

- `swift test` exits zero with all eleven baseline tests executed and no skipped interoperability test; added tests cover concrete fixes.
- The unsigned simulator build exits zero for the reported Xcode/SDK versions and exact commit.
- Pairing failures, replay, authentication failures and invalid framing close the connection; keys never appear in diagnostics.
- One selected document produces one durable Mini job, and disconnect/reconnect retrieves that same job ID without automatic resubmission.
- Displayed task mode and executor are accurate; deterministic analysis is never presented as model output.
- Background suspension and file-selection flows behave as documented, with accessible controls and readable status text.
- Hardware acceptance is explicitly **NOT RUN**, **FAIL** or **PASS** with evidence. No inference from simulator success to physical usbmuxd compatibility.

## Evidence template

```text
Agent / date:
Repository / branch:
Baseline commit: af3372806f01a572f08105552f6072af0a2c4de2
Tested commit / dirty-source digest:
Owned changed files:
macOS / Xcode / SDK / Swift versions:
Build-window owner and completion:
Swift baseline: PASS, 11 tests, Xcode 26.5 — see poc/VALIDATION.md; changed-revision command / exit code / log path:
Unsigned iOS baseline: PASS, exit 0, Xcode 26.5 / iPhoneSimulator 26.5, arm64+x86_64 — see poc/VALIDATION.md; changed-revision command / exit code / log path:
Simulator UI: NOT RUN | FAIL | PASS — evidence:
Signing/provisioning: NOT RUN | FAIL | PASS — evidence:
Physical USB: NOT RUN | FAIL | PASS — device/OS/topology/logs:
Document boundary and explicit-send checks:
Pairing/invalid-key/replay checks:
Background/reconnect/lost-ack recovery:
Secrets redacted and synthetic document used:
Remaining blockers / next owner:
```

## Copy-paste kickoff prompt

```text
You own the iOS companion qualification slice in https://github.com/ttracx/thox-usbmuxd, branch master, source baseline af3372806f01a572f08105552f6072af0a2c4de2. Read poc/handoffs/01_ios_companion.md and the actual source before edits. Work in an isolated branch/worktree. Own poc/ios only; preserve protocol compatibility and do not edit host, shared protocol, upstream source, or shipping ThoxOS code. Coordinate with the current Mac build owner before starting Xcode. Reuse matching build evidence, fix compiler/test failures, run swift test and the documented unsigned xcodebuild command, then qualify document selection, Keychain pairing, lifecycle and durable job recovery. Record exact commit, commands, exit codes and log paths. Signing and physical USB are NOT RUN unless you actually execute and evidence them. Deliver a small reviewed change with an updated evidence block and a clear handoff to the integration owner. Do not send external messages or upload a release.
```
