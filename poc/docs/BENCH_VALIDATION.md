# Physical-device validation

**Overall status: NOT RUN.** This record is a checklist, not a claim of compatibility. Software tests, simulator runs, and source inspection cannot establish a working USB data/power path on a real ThoxMini and iPhone.

## Evidence header

| Field | Value |
|---|---|
| Tested commit | NOT RECORDED |
| Operator and UTC time | NOT RECORDED |
| Mini board/revision and enclosure/port revision | NOT RECORDED |
| Mini OS/kernel, Python, usbmuxd, iproxy versions | NOT RECORDED |
| iPhone model and iOS version | NOT RECORDED |
| iOS app version/build and signing identity | NOT RECORDED |
| Cable/adapter and power supply | NOT RECORDED |
| Power/data role measurements | NOT RECORDED |
| Model/runtime/quantization, when applicable | NOT RECORDED |

## Required acceptance checks

| ID | Check | Acceptance evidence | Status |
|---|---|---|---|
| B01 | Hardware role and power | Qualified Mini host role; stable power; no conflicting power sources | NOT RUN |
| B02 | Native app build | Xcode build succeeds for the target SDK; signed app installs on the phone | NOT RUN |
| B03 | Phone enumeration and trust | Correct device is identified; normal system Trust flow completed if requested | NOT RUN |
| B04 | Explicit target forwarding | iproxy connects only to the selected UDID; local listener is loopback-only | NOT RUN |
| B05 | Valid application pairing | Matching key reaches ready state and reports Mini status | NOT RUN |
| B06 | Invalid application pairing | Wrong key is rejected; no job data is accepted or returned | NOT RUN |
| B07 | Basic workload | Submit known text; statistics/digest match the test input | NOT RUN |
| B08 | Cable disconnect recovery | Disconnect after submission; reconnect; retrieve the job/result by ID | NOT RUN |
| B09 | App suspension recovery | Background/lock/unlock sequence observed; reconnect and retrieve durable work | NOT RUN |
| B10 | Mini restart recovery | Completed results persist; unfinished work has an explicit interrupted outcome | NOT RUN |
| B11 | Cancellation | Cancel pending/running job; late output cannot change it to completed | NOT RUN |
| B12 | Malformed/oversized input | Session/request rejects invalid frames/text without crashing the service | NOT RUN |
| B13 | Unplug/replug repetitions | Record 20 cycles, failures, recovery actions, and time to reconnect | NOT RUN |
| B14 | No-internet operation | Analysis completes with internet unavailable; no inference fallback occurs | NOT RUN |
| B15 | Resource behavior | Record peak RSS, CPU, temperature, power, and latency during qualified jobs | NOT RUN |
| B16 | Optional real inference | Installed model completes test prompt; record runtime/model and measured latency/memory | NOT RUN |

For B16, report **NOT CONFIGURED** if there is no local inference server. Never present B07 statistics as model inference evidence.

## Promotion rule

Complete B01–B15 on the chosen hardware/OS combination before marking that combination as a validated USB POC. B16 is additionally required before making an inference claim. A pass does not imply compatibility with untested phone models, iOS releases, adapters, or power supplies.

Capture minimal logs and measurements in an access-controlled evidence location. Redact phone UDIDs and personal content from shareable reports. Never attach pairing keys. Keep failures alongside passes so reviewers can reproduce limits.

App Review, TestFlight distribution, production security review, accessibility validation, and integration into the existing ThoxOS app remain independent delivery gates.
