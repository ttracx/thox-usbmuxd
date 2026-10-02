# Architecture and constraints

Status: experimental design and POC implementation. Physical-device compatibility must be established separately.

## Vertical slice

| Layer | Responsibility | Boundary |
|---|---|---|
| iOS frontend | Store pairing secret in Keychain, listen while active, show session state, submit/check/cancel jobs | Standalone SwiftUI POC; existing ThoxOS app integration remains pending |
| USB transport | Mini/Linux runs usbmuxd; iproxy forwards loopback port 49322 to iOS listener port 49321 | Mini initiates the connection; no automatic iPhone-to-Mini HTTP forwarding |
| Application session | Mutual proof of possession, session key derivation, authenticated encryption, bounded frames | Shared secret is provisioned out of band; protocol needs independent security review |
| Mini backend | Validate operations, maintain jobs and results in SQLite | No generic shell, arbitrary file access, caller-supplied endpoints, or cloud fallback |
| Workload | Deterministic text statistics by default; optional local OpenAI-compatible inference | Statistics are not LLM output; inference requires a separately provisioned runtime/model |

The wire contract is authoritative in [PROTOCOL.md](../PROTOCOL.md). Every reconnect performs a fresh authenticated handshake. Connection loss does not delete jobs. Restarted incomplete inference jobs are marked failed rather than automatically resubmitted. Cancelling a job suppresses later results but does not guarantee that a provider stops computation already underway.

## Hardware roles

For usbmuxd, the Mini must act as USB **host**, and the iPhone is the USB **device**. A firmware configuration that exposes Mini as a USB peripheral is a different data role and is not sufficient for this path.

Before connecting a prototype, validate the specific board, enclosure port wiring, OTG/USB-C role negotiation, cable, and power arrangement. Do not infer compatibility from connector shape. Avoid powering two sources into an unqualified path. Establish stable enumeration and power first, then test the app session.

The Pi Zero 2 W variant is a constrained target; a large microSD card provides persistent capacity rather than corresponding RAM. Measure each proposed workload on the actual board and power supply. An optional C6 mesh controller can coordinate connectivity but does not substitute for the host compute needed by the backend and model.

## iOS lifecycle and trust

The companion uses a foreground listener. iOS can suspend the application after it leaves the foreground. Do not treat a connected cable as a guarantee of uninterrupted background execution. Mini owns durable work; after returning to the app, reconnect and query the saved job identifier.

Apple device trust, unlock, and accessory restrictions still apply. The operator follows system prompts through the normal UI. The POC does not bypass those controls or claim that application pairing replaces them.

An [Apple DTS response](https://developer.apple.com/forums/thread/790192) describes USBMux as undocumented, advises against depending on it, and identifies standard networking through USB Ethernet as a possible alternative. Treat USBMux as an experimental transport that can change between OS releases. Distribution suitability and App Review outcomes have not been established for this prototype. Wi-Fi and qualified USB networking remain separate candidate production transports behind the same application service boundary.

## Security boundary

- Pairing uses a fresh 32-byte random shared secret, copied privately to iOS Keychain and a restricted Mini-side file.
- The application protocol uses HMAC-SHA256 proofs, HKDF-SHA256 keys, and AES-256-GCM with directional sequences. Peer identity is possession of the shared secret; this is not a certificate/device-attestation system.
- Invalid proofs, replayed sequences, malformed frames, and authentication failures close the session.
- Job text and results remain sensitive at rest. SQLite storage in this POC is not encrypted by the application. The host requires a dedicated owner-only workspace; operating-system account permissions and storage protection remain necessary.
- App/session encryption does not isolate work from a compromised Mini or an unlocked, compromised phone. No HIPAA, GDPR, or other compliance claim follows from this prototype.
- Revoke a pairing by stopping the bridge, replacing the Mini key, clearing/replacing the app's stored key, and reconnecting deliberately. No fleet enrollment or remote-revocation service is provided.

Keep connection metadata, phone identifiers, prompts, results, and pairing secrets out of public issue reports. Collect only evidence needed to diagnose a specific failure.

## ThoxKey is a different path

This transport prototype targets a computing Mini acting as USB host. A storage-based ThoxKey does not become an independent host or inference processor by adding usbmuxd. A future ThoxKey/iOS slice would use user-selected external-storage files and an iOS-compatible runtime packaged with ThoxOS. It would need separate file-access, lifecycle, model, and hardware qualification.

ThoxBeam remains the portable runtime engine inside ThoxOS. This repository does not implement ThoxBeam for iOS and does not add a new customer-facing platform.

## Primary references

- [usbmuxd upstream](https://github.com/libimobiledevice/usbmuxd)
- [libusbmuxd and iproxy upstream](https://github.com/libimobiledevice/libusbmuxd)
- [Apple DTS: USB communication with a pre-OS system](https://developer.apple.com/forums/thread/790192)
- [Apple: app lifecycle](https://developer.apple.com/documentation/uikit/managing-your-app-s-life-cycle)
- [Apple: external storage devices on iPhone](https://support.apple.com/guide/iphone/external-storage-devices-iph95baac91f/ios)

Bench evidence should record the exact dependency versions rather than assuming current upstream behavior applies to every distribution package.
