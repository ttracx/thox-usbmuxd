# Agent handoff 05 — QA and release evidence

## Assignment

Validate the existing experimental THOX USB POC across Python, native Swift, and the selected Mini/iPhone hardware. Produce reproducible evidence and an accurate readiness statement. Keep source delivery, native compilation, physical USB compatibility, and distribution as separate outcomes.

Repository: [ttracx/thox-usbmuxd](https://github.com/ttracx/thox-usbmuxd)  
Baseline branch: `master`  
Delivered baseline commit: `af3372806f01a572f08105552f6072af0a2c4de2`

Start from the current approved commit and record its SHA. The baseline is a traceability reference; do not reset over later team changes.

## Known evidence at handoff

| Check | Recorded state |
|---|---|
| Python automated tests | 34 passing at source-delivery checkpoint |
| Actual host CLI loopback demo | Encrypted workflow and reconnect demonstrated against the Python peer |
| Native Swift tests | 11 passing on Mac with Xcode 26.5 at commit `af3372806f01a572f08105552f6072af0a2c4de2` |
| Native iOS compilation | PASS: unsigned generic iOS Simulator build, Xcode 26.5, iPhoneSimulator26.5 SDK, arm64 and x86_64 at the baseline commit |
| Python↔Swift live interoperability | No successful result recorded in this handoff |
| Physical Mini↔iPhone USB | NOT RUN / no result recorded |
| Signed iOS installation / TestFlight | No successful result recorded in this handoff |

Read [recorded validation](../VALIDATION.md) and any newer evidence before rerunning checks. A Python peer exercising the CLI is useful transport evidence, but it does not establish native Swift interoperability.

## Copyable agent prompt

```text
You own QA and release evidence for ttracx/thox-usbmuxd. Baseline master commit:
af3372806f01a572f08105552f6072af0a2c4de2. Read the current PROTOCOL.md, root README,
poc/ios/README.md, existing tests, and BENCH_VALIDATION.md before testing.

Confirm the current commit and preserve other agents' changes. Run the Python suite,
native Swift tests, then a real Python↔Swift session before physical USB qualification.
Use the existing known-answer vectors and real framing/encryption. Never substitute a
Python-only peer or stubbed crypto for the interoperability gate.

Coordinate a bounded Mac/Xcode window with the build owner; do not interrupt another
project's build/export/upload. Compile the iOS target without signing first, then use
an authorized development signing setup for the selected real phone. Follow normal
device Trust/unlock prompts. Do not bypass them or expose the forwarding port publicly.

Record exact commands, commit, tool versions, exit status, sanitized logs, failures,
and remaining limits. Keep pairing secrets, phone UDIDs, and personal documents out of
committed artifacts. Do not add GitHub Actions. A source push, Swift test pass, unsigned
build, or simulator result is not a TestFlight upload or proof of real USB compatibility.

Own QA/evidence files only. Report implementation defects to the component owner with
a minimal reproduction before changing their source. Update readiness wording only
when the corresponding evidence exists.
```

## Owned paths and dependencies

- Primary ownership: `poc/VALIDATION.md`, `poc/docs/QA_RELEASE_EVIDENCE.md`, `poc/docs/BENCH_VALIDATION.md`, and sanitized evidence under `poc/evidence/` if needed. Update VALIDATION.md as the evidence index; retain the existing baseline results.
- Shared updates after coordination: actual completion states in `development_queue.md`; validation wording in the root README.
- Implementation owners retain `poc/host/`, `poc/ios/`, and `poc/PROTOCOL.md`. Request focused fixes; do not independently alter the wire contract.
- Dependency gates: accessible Mac with compatible Xcode, current source checkout, exclusive bounded build window, selected Mini/phone/cable/power hardware, and authorized development signing for a real-phone installation.
- Network deployment, signing identities, App Store Connect access, and TestFlight submission are separate operational dependencies. Never assume they are supplied by a repository fork.

## Validation sequence and acceptance

1. **Software regression.** Run `PYTHONPATH=poc/host python3 -m unittest discover -s poc/tests -v`. On the Mac, run `swift test` from `poc/ios`. Record actual counts; do not carry the checkpoint counts forward as a new result.
2. **Live Python↔Swift interoperability.** Run the production Python host session against the real Swift wire implementation over loopback. Verify handshake, authenticated ready, direction-specific sequences, status, job submission, result retrieval, and a fresh session on reconnect. Exercise wrong pairing key, replay/out-of-order frame, tampered authentication tag, split/coalesced frames, oversized input, and escaped control-heavy text at the supported limits. Confirm the current shared 1 MiB frame contract at both endpoints.
3. **Submission recovery.** Persist the request UUID on the client before transmission. Drop the connection after the host commits but before the response arrives. Reconnect and fetch that UUID as the job ID. Replay the same UUID/text/mode and verify the same job; change text or mode with that UUID and verify an explicit conflict.
4. **Inference isolation.** If local inference is configured, verify the 30-second parent deadline and child cleanup. Cancel a running job and ensure its child is terminated/reaped and late output cannot overwrite cancellation. Treat cancellation of actual model-server computation as a separate capability. Confirm queued work can progress after failure or cancellation.
5. **Native app build.** Build `poc/ios/ThoxUSBLab.xcodeproj`, scheme `ThoxUSBLab`, using the README's unsigned simulator command. Record warnings/errors and result. This gate establishes compilation only.
6. **Signed device bench.** Install through the authorized development workflow and complete `poc/docs/BENCH_VALIDATION.md` on the selected phone and Mini. Verify USB roles/power before connecting. Use explicit UDID targeting and a loopback-only iproxy listener. Keep the app in the foreground; test lock/background and reconnect behavior deliberately.
7. **Readiness record.** State the exact validated combination and any failed or untested cases. Real-inference claims require measured output, model/runtime identity, memory, latency, and resource behavior. Distribution claims require independent installation/upload/processing evidence.

Do not broaden tests after the concrete remaining risks and required gates are resolved. For a failure, retain the failing evidence, assign its owner, and rerun the focused gate after the fix.

## Evidence template

```markdown
# THOX USB POC validation run
Run ID:
UTC time / operator:
Repository / branch / tested commit:
Working tree status:
OS / Python / cryptography / Swift / Xcode / SDK versions:
Board / phone / OS / cable / power revisions (no public UDID):

| Gate | Exact command or steps | Exit/status | Evidence location | Limits |
|---|---|---|---|---|
| Python tests | | NOT RUN | | |
| Swift tests | | NOT RUN | | |
| Python↔Swift live session | | NOT RUN | | |
| Lost acknowledgment recovery | | NOT RUN | | |
| Cancellation/deadline cleanup | | NOT RUN | | |
| Unsigned iOS compilation | | NOT RUN | | |
| Signed phone install | | NOT RUN | | |
| Physical USB bench | | NOT RUN | | |
| Actual inference, if configured | | NOT RUN | | |
| TestFlight, if separately authorized/performed | | NOT RUN | | |

Failures and minimal reproductions:
Assigned fixes and retested commit:
Validated combinations:
Untested combinations:
Permitted readiness statement:
```

Until interoperability and bench evidence exists, describe the deliverable as an **experimental source POC with passing Python and Swift tests and a Python loopback workflow**. Replace that wording only with outcomes supported by the recorded evidence.
