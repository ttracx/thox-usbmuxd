# Handoff 04 — Protocol, pairing lifecycle, and retained data

**Owner:** security/protocol engineer, collaborating with the Mini and iOS owners.  
**Repository:** <https://github.com/ttracx/thox-usbmuxd>  
**Work branch base:** current `origin/master`; implemented reference baseline `af3372806f01a572f08105552f6072af0a2c4de2`.  
**Current evidence:** 34 Python tests, 11 Swift/CryptoKit tests and the unsigned iOS simulator build passed at this baseline; see `poc/VALIDATION.md`. Physical USB operation and an independent protocol review remain unqualified.

## Assignment

Review the actual Python/Swift protocol and close concrete gaps needed to integrate this experimental transport into ThoxOS. Deliver a source-grounded review, fixes with regression tests, a pairing/rotation/revocation contract, and an explicit retained-data policy. Preserve the existing workload and authority boundaries unless a coordinated protocol change specifies otherwise.

The current custom protocol is a POC. Its use of standard cryptographic primitives and passing functional tests is not evidence of a completed production security review. Decide whether to retain and harden it or replace the custom handshake with a reviewed protocol that both platforms can support; record the engineering decision, compatibility costs, and migration behavior.

## Source and proposed ownership

| Source | Review focus |
|---|---|
| `poc/PROTOCOL.md` | Normative framing/session/job contract; update alongside wire changes |
| `poc/host/thox_usb/protocol.py` | Python parsing, HMAC proofs, HKDF derivation, AES-GCM, sequence and size checks |
| `poc/ios/Sources/THOXWire/` | Swift framing, strict JSON, CryptoKit session and error handling |
| `poc/fixtures/crypto-vector-v1.json` | Python/Swift deterministic interoperability fixture |
| `poc/ios/Tests/THOXWireTests/` | Native wire tests and matching fixture |
| `poc/host/thox_usb/__main__.py` | Key generation/loading, reconnect behavior, file permissions |
| `poc/host/thox_usb/jobs.py` | Request scope, idempotency, persistence, provider process/deadline/cancellation |
| `poc/ios/ThoxUSBLab/Stores/PairingKeyStore.swift` | Keychain storage and deletion |
| `poc/ios/ThoxUSBLab/Models/LabModel.swift` | Saved job ID, explicit submission, app lifecycle, lost-acknowledgement recovery |
| `poc/tests/` | Existing behavioral and adversarial regression tests |

Suggested new deliverables: `poc/security/REVIEW.md`, `poc/security/PAIRING_LIFECYCLE.md`, `poc/security/DATA_RETENTION.md`, and `poc/security/DEPENDENCIES.md`. Put additional Python tests under `poc/tests/`; coordinate Swift changes with the iOS owner. Do not change the wire contract in one language without updating the other, the fixture where needed, and the protocol document.

## Current protocol, exactly as implemented

| Property | Baseline behavior |
|---|---|
| Transport roles | Mini initiates TCP; iOS accepts while foregrounded; app requests then flow iOS → Mini |
| Pairing | Manually provisioned 32-byte random shared secret; identity is possession of that secret |
| Handshake | Fresh 32-byte nonces; separate server/client HMAC-SHA256 proofs; 10-second deadline |
| Session derivation | HKDF-SHA256 with both nonces as salt and directional context strings |
| Encryption | AES-256-GCM with separate directional keys; sequence-derived 12-byte nonce; direction/sequence in AAD |
| Replay/order | Exact next unsigned sequence required; each direction starts at zero after a new handshake |
| Framing | Four-byte big-endian length followed by JSON; maximum body 1,048,576 bytes |
| Input | Object-only frames; duplicate-key/nonfinite/invalid JSON rejected; Swift also explicitly limits nesting |
| Application scope | `ping`, `status`, `job_submit`, `job_get`, `job_cancel` only |
| Work limits | Text ≤65,536 UTF-8 bytes; one worker; 16 queued jobs; bounded provider response/result |
| Provider | Operator-fixed literal-loopback HTTP(S) `/v1/chat/completions`; no caller URL override, redirects, environment proxy, or implicit cloud fallback |

Validate the direction strings, embedded zero bytes, nonce layout, strict numeric handling, and sequence increment rules directly against both implementations and the shared fixture. Version 1 has no certificate/device-attestation identity and no ephemeral Diffie–Hellman exchange. A later compromise of the long-term PSK permits derivation of previously recorded session keys from the public handshake nonces; document that lack of forward secrecy when assessing suitability.

## Pairing and authority work

The host `pair` command creates a new mode-`600` file using exclusive creation, prints its path by default, and reveals the secret only with `--reveal`. The iOS app stores one PSK as a nonsynchronizing Keychain item with `WhenUnlockedThisDeviceOnly` protection. Saving or forgetting the key stops the app listener. Apple's device trust/pairing is a separate mechanism and remains in force.

Close these concrete integration decisions:

1. **Device identity and workspace binding.** One shared key presently authorizes the whole configured workspace. Jobs have no caller/tenant identity field. Anyone holding that key and a known job UUID can read/cancel that job. Replacing the host key while reusing the workspace does not change job ownership or erase prior data. Define the intended single-owner model or add explicit binding/isolation before multi-device enrollment.
2. **Rotation and revocation.** Specify stopping active sessions, provisioning a new secret, clearing/replacing the app key, restarting with the selected key/workspace, and testing rejection of the old secret. A running bridge reads its key at startup; replacing the file alone does not revoke an existing session or change the in-memory key. A phone's “forget key” action does not remotely revoke copies on another device.
3. **Delivery of the first secret.** The current manual UI is the only implemented path. Decide the production enrollment channel and confirmation UX with the iOS owner. Do not describe a QR enrollment flow or fleet revocation service as delivered.
4. **Lost acknowledgements and device selection.** Preserve pre-send persistence of the submission UUID. Determine how the app's saved job ID is bound to a selected Mini and how the UI handles a changed pairing/workspace. Currently the app remembers one last job ID in preferences, independently of the pairing key.
5. **Session resource bounds.** Review incomplete-frame/slow-reader behavior, post-handshake idle timeouts, reconnect rate, parser depth consistency, and memory under maximum escaping/base64 expansion. The handshake deadline does not by itself bound every established-session read.

The current `status` fields are application descriptions, not attested hardware facts. Treat a loopback provider URL as a transport restriction: it does not independently prove that the separately configured inference server never forwards work elsewhere.

## Persistence and deletion work

The baseline has **no application encryption at rest**. `jobs.sqlite3` stores input text, mode, timestamps, status, result, and error; `artifacts/<job-id>.json` stores result JSON. Owner-only permissions and a workspace lock are implemented. They do not encrypt a copied SD card, protect against a compromised account, or limit total retained history.

There is no deletion API, retention scheduler, total database/disk quota, or guaranteed secure-erasure implementation in this POC. The 16-job queue bound is not a storage quota. Key rotation does not encrypt or delete existing records.

Deliver a practical policy and implementation plan covering:

- What persists, for how long, and where the owner can inspect/delete it.
- Whether the target requires volume encryption or application-level encryption, where keys live, and how recovery works.
- Consistent removal of SQLite records and matching artifacts, including crash recovery and backups. Do not equate deleting a row/file with verified physical erasure on flash storage.
- Behavior at low disk space, including artifact-written/database-update failure and orphan-artifact cleanup.
- Migration/versioning of the store and preservation of idempotency through a retention window.

Coordinate the policy with firmware provisioning so a distributable image contains neither a baked-in pairing secret nor retained user jobs.

## Job and provider behavior to preserve and verify

- A canonical lowercase request UUID is the submitted job's durable ID. Replay with identical text/mode returns the existing job; different content returns `conflict`. Distinguish this application idempotency from encrypted-frame replay rejection.
- Cancelled and terminal jobs cannot become completed because late output arrives. Cancellation terminates/reaps the owned inference client subprocess; it does not promise that the separately running model server stops computation.
- Provider work runs in a spawned child process. The parent enforces a 30-second total deadline and reaps the child before accepting another provider job. HTTP body is bounded to 262,144 bytes; serialized result JSON is bounded to 131,072 bytes.
- Restarted queued/running work becomes `failed` with `interrupted`; it is never automatically reissued to a model. Completed jobs remain retrievable.
- The iOS app uses a 15-second request deadline and saves a submission ID before writing the request. A lost response should trigger retrieval by saved ID, not blind resubmission.
- Error responses must not echo prompts, pairing keys, raw provider output, or unintended paths. Review logs, exception surfaces, test artifacts, and support bundles for those specific exposures.

## Start the review from current master

```bash
git clone https://github.com/ttracx/thox-usbmuxd.git thox-usbmuxd-security
cd thox-usbmuxd-security
git fetch origin master
git show --no-patch --format=fuller af3372806f01a572f08105552f6072af0a2c4de2
git switch -c agent/security-protocol-review origin/master
git rev-parse HEAD
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r poc/host/requirements.txt
PYTHONPATH=poc/host python3 -m unittest discover -s poc/tests -v
python3 poc/scripts/demo.py
python3 -m pip freeze
```

On the authorized Mac checkout, run native tests and the unsigned simulator compilation. Keep this coordinated with other Xcode owners; do not interrupt their builds.

```bash
swift test --package-path poc/ios --scratch-path /tmp/thox-wire-security-agent
xcodebuild -project poc/ios/ThoxUSBLab.xcodeproj \
  -scheme ThoxUSBLab \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath /tmp/thox-usblab-security-agent \
  CODE_SIGNING_ALLOWED=NO build
```

A fixture match checks implementation interoperability for the supplied case; it is not a complete proof of protocol security. Add cases tied to specific review findings, including damaged/truncated frames, timeout/resource exhaustion, old-key rejection, job-ID reuse conflicts, workspace isolation, and power-loss recovery where applicable.

## Dependency and redistribution review

Create an inventory from a clean fork checkout and the actual distributable packages. Upstream README identifies `COPYING.GPLv3`; the THOX POC source headers and Python metadata declare `GPL-3.0-or-later`. The Python dependency pin is `cryptography==46.0.0`; the Swift package uses Apple frameworks and has no declared third-party package dependencies in this baseline. These facts do not establish the license status of every transitive dependency or the finished app/image.

Useful inventory commands from the clean checkout:

```bash
git ls-files '*COPYING*' '*LICENSE*' '*NOTICE*'
rg -n 'SPDX-License-Identifier|license|License' poc/host/pyproject.toml poc/host poc/ios/Package.swift
python3 -m pip show cryptography
python3 -m pip freeze
```

Record per-component license/version/source, preserved notices, modifications, shipped binary boundaries, and how the intended distribution supplies the required source/license materials. Have the actual integration/distribution arrangement reviewed before combining POC code with a differently licensed ThoxOS target or shipping an image/app. Do not infer that separate processes remove every obligation, that all THOX code must change license, or that an App Store submission is automatically accepted/rejected. This handoff requests a concrete dependency/distribution review rather than giving a blanket legal conclusion.

## Acceptance evidence and integration handoff

Deliver a finding register with source path, reproducible case, practical impact, owner, fix decision, and retest evidence. Include:

1. Python and native test logs with tested commit, interpreter/Xcode/SDK versions, and the same protocol fixture revision.
2. Documented protocol decision, reviewed invariants, and remaining limitations, including PSK identity and lack of forward secrecy if version 1 is retained.
3. Demonstrated old-key rejection, explicit active-session revocation behavior, and approved workspace/job ownership semantics.
4. Storage inventory, retention/deletion/encryption decision, and failure/backup behavior, with implemented work clearly separated from planned work.
5. Cancellation/timeout tests showing no orphan inference client process, no late completed result, and no automatic retry after restart.
6. Dependency/notice inventory and a recorded decision for the actual release packaging.
7. A coordinated integration commit or small reviewable commits, matching Python/Swift contract updates, and handoff notes for firmware and iOS owners.

No production security or compliance claim follows solely from this test suite. Report which integration gates are satisfied and which concrete work remains.

## Kickoff prompt

> Own the security/protocol integration pass for `ttracx/thox-usbmuxd` at `af3372806f01a572f08105552f6072af0a2c4de2`. Read this handoff and both protocol implementations. Reproduce the existing tests, review the PSK handshake and session bounds, and either harden the current design or propose a reviewed replacement with a migration plan. Close pairing rotation/revocation, workspace/job ownership, retained-data handling, and the actual dependency/distribution review. Preserve idempotent submission, cancellation, process deadlines, and explicit local-provider configuration. Coordinate shared changes with the iOS and Mini owners, add regression tests for concrete findings, and deliver tested commits plus source-grounded evidence. Do not claim that the POC provides at-rest encryption, forward secrecy, fleet revocation, or completed production review unless your implementation and evidence establish it.
