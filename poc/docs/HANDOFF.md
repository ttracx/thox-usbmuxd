# Engineering handoff

This fork adds a bounded USB connectivity POC to upstream usbmuxd. The intended user action is: open the iOS companion, connect a qualified Mini, submit text, and retrieve the result even after the link is interrupted.

## Repository ownership boundaries

- Upstream daemon code retains its original project structure, documentation, and licenses.
- THOX implementation lives under `poc/`; the root THOX README directs developers to that slice.
- `poc/PROTOCOL.md` defines the session and job contract. Update it in the same change as wire behavior.
- Keep `ecosystem_map.md`, `mvp_catalog.md`, and `development_queue.md` aligned with actual delivery evidence.
- Run checks locally. Do not add GitHub Actions as part of routine validation.

## First engineering pass

1. Set up the Python environment and run the documented unit-test command from the root README.
2. Build `poc/ios/ThoxUSBLab.xcodeproj`, scheme `ThoxUSBLab`, on a Mac using the root README command. Run native protocol tests with `cd poc/ios` followed by `swift test`. Record the Xcode version, SDK, scheme, and results. A simulator build does not validate USB.
3. Install a signed development build on the selected phone; complete application pairing privately.
4. Start iproxy with an explicit UDID and loopback-only listener, then start the Mini bridge.
5. Complete the physical-device checklist, preserving failures as well as passes.

## Existing ThoxOS integration

The standalone iOS client is a source POC. To integrate it into the shipping ThoxOS app:

1. Place the connection service behind the app's device-session interface; retain the host-initiated direction.
2. Map connection, pairing, disconnected, job-running, failed, cancelled, and completed states into TXF device components.
3. Display the actual executor and workload type. Distinguish deterministic analysis from a configured model.
4. Scope each workflow to the selected paired device and requested operation; preserve existing approval and revocation boundaries.
5. Handle foreground transitions with reconnect and job lookup. Do not promise continuous background connectivity.
6. Integrate approved brand assets and fonts from the established app sources, then validate accessibility and text scaling.
7. Compile and test in the existing repository before signing or uploading a release.

No existing ThoxOS source, signing credentials, release build, or TestFlight upload is implied by this fork.

## Operating and recovery notes

| Symptom | Check |
|---|---|
| Phone absent from device list | Cable data capability, Mini host role, power, unlocked phone, normal Trust/accessory flow |
| Forwarding fails | Explicit UDID, running usbmuxd, listener port 49321, installed iproxy command syntax |
| Session cannot authenticate | Same current 32-byte base64 key on both endpoints; replace pairing deliberately if uncertain |
| Session closes after switching apps | Foreground lifecycle; return to companion and reconnect |
| Job lost from app view | Retrieve using the saved job ID and the same Mini workspace; do not resubmit blindly |
| Inference unavailable | Optional endpoint/model were not configured or did not pass capability/runtime checks |
| Cancelled provider remains busy | Provider-side computation cancellation is not guaranteed; POC discards late output |

Pairing keys and workspace contents are local secrets/data. Reuse the same dedicated owner-only workspace to retain jobs; its directory mode must be `700`. The pairing command prints a path by default; `--reveal` exposes the newly generated key only when explicitly requested from a private operator terminal. Never resolve a connection failure by disabling authentication, exposing the forwarding port publicly, or bypassing system trust prompts.

## Release and evidence

For each candidate, record commit, dependency versions, local test outcomes, iOS build outcome, and the completed bench record. Until those checks are performed, use the phrase **experimental source POC**. A repository push or tag by itself is not a hardware or distribution release.
