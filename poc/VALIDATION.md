# POC validation record

Date: 2026-10-02  
Tested source commit: `af3372806f01a572f08105552f6072af0a2c4de2`  
Repository: https://github.com/ttracx/thox-usbmuxd  
Scope: software POC; physical USB and product integration remain unqualified.

| Check | Result | Evidence / limit |
|---|---|---|
| GitHub fork lineage | PASS | `fork=true`; parent and source `libimobiledevice/usbmuxd` |
| GitHub Actions setting | Disabled | Repository actions permissions returned `enabled=false` |
| Python automated suite | PASS: 34 tests, zero failures | Python 3.12.14; cryptography 46.0.0; local loopback and isolated temporary directories |
| Actual Python CLI bridge demo | PASS | Encrypted handshake, analyze job, forced disconnect, new session, same persisted result |
| Swift protocol suite | PASS: 11 tests, zero failures | macOS arm64, Xcode 26.5 (17F42); shared Python/CryptoKit fixture passed |
| iOS app compile | PASS | Xcode 26.5, iPhoneSimulator26.5 SDK, generic iOS Simulator, arm64 and x86_64; code signing disabled |
| Live Python↔Swift network session | NOT RUN | Shared crypto fixture is verified; actual mixed-language socket session still needs QA |
| iOS UI/lifecycle execution | NOT RUN | Compilation is not an app runtime or UX test |
| Signed phone install / TestFlight | NOT RUN | No distribution upload or signing operation performed |
| Mini board / real iPhone USB | NOT RUN | No physical pair was connected in this validation |
| Real model inference | NOT RUN | Provider tests use controlled local HTTP fixtures, not a deployed language model |
| Existing ThoxOS integration | NOT IMPLEMENTED | Standalone lab app only |

## Reproduce Python checks

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r poc/host/requirements.txt
PYTHONPATH=poc/host python3 -m unittest discover -s poc/tests -v
python3 poc/scripts/demo.py
```

The test suite requires local loopback socket permissions. The execution sandbox
initially denied socket creation; the same tests were rerun with approved local
socket access. No external network endpoint is exercised by these tests.

Observed final suite output:

```text
Ran 34 tests in 0.668s
OK
```

Coverage includes framing fragmentation, coalescing, truncation, size rejection,
duplicate JSON keys, wrong pairing proof, replay and tamper rejection, maximum
escaped input, queue/input limits, private key files, durable reconnect, host
restart, idempotency conflicts, cancelled provider process cleanup, total provider
deadline, redirect denial, response bounds and error sanitization.

## Reproduce Apple checks

```bash
cd poc/ios
swift test
cd ../..
xcodebuild -project poc/ios/ThoxUSBLab.xcodeproj \
  -scheme ThoxUSBLab \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath /tmp/thox-usb-poc-derived \
  CODE_SIGNING_ALLOWED=NO build
```

Observed output:

```text
Test Suite 'All tests' passed
Executed 11 tests, with 0 failures (0 unexpected)
** BUILD SUCCEEDED **
Process completed with exit code 0
```

The unsigned build emitted the informational AppIntents metadata warning because
the lab app does not depend on AppIntents. This did not fail the build. No UI
launch or signed device installation was inferred from the successful compile.

The source was cloned into an isolated temporary Mac checkout and built using
its own DerivedData. Existing repositories, release archives and upload processes
were not changed. Temporary build paths are not durable delivery artifacts.

## Remaining qualification

Follow [agent handoffs](handoffs/START_HERE.md) and the
[hardware bench checklist](docs/BENCH_VALIDATION.md). Record each target's actual
hardware revision, phone model, OS version, cable, power role, dependency versions,
source SHA and expected/observed behavior. Treat the undocumented USBMux transport
as experimental until that evidence and the separate security review are complete.
