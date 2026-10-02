# THOX USB POC v0.1.0

Experimental ThoxMini-to-ThoxOS iOS workflow, added alongside the upstream
libimobiledevice/usbmuxd source.

- Authenticated encrypted host-initiated transport over an iproxy-forwarded socket.
- Durable bounded jobs, idempotent submission, cancellation and reconnect recovery.
- Deterministic text analysis plus an optional operator-configured loopback inference endpoint.
- Standalone SwiftUI iOS app with Keychain pairing, document input and result sharing.
- 34 Python tests and 11 Swift protocol tests pass; unsigned iOS simulator build succeeds.
- Six role-specific integration handoffs, a coordinator guide and machine-readable task graph.

Physical USB interoperability, signed phone install, real model performance and
integration into the existing ThoxOS app remain outstanding. This prerelease is
for engineering evaluation. See poc/VALIDATION.md for exact evidence and
poc/handoffs/START_HERE.md for the completion plan.

Tag: `poc-v0.1.0` (the upstream project already has a `v0.1.0` tag).
