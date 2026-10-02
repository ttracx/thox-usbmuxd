# Agent working agreement

This repository is an experimental fork of libimobiledevice/usbmuxd. Read
`poc/handoffs/START_HERE.md`, `poc/PROTOCOL.md`, and `poc/VALIDATION.md` first.

- Preserve upstream source, history, AUTHORS, COPYING files, and README.upstream.md.
- THOX additions live in `poc/`. Do not patch upstream C transport to work around an app protocol defect.
- Run local validation; GitHub Actions is disabled for this fork.
- Keep upstream USBMux limitations and hardware results explicit. Software tests are not proof of a real USB connection or production readiness.
- Pairing secrets, real documents, phone IDs, signing assets and internal repository details do not belong in this public fork.
- Use one branch per owned handoff. Do not reset, kill, or overwrite another agent's work or processes. Coordinate Apple build windows with the active release owner; use isolated DerivedData.
- Wire changes require Python and Swift changes, shared fixtures, negative tests, and a version decision together.
- Keep jobs idempotent, durably recoverable, bounded and cancellable. Do not enable arbitrary shell, file paths, endpoint overrides, cloud fallback, or wider device authority as a connectivity fix.
- Update ecosystem_map.md, mvp_catalog.md, development_queue.md and evidence when behavior changes.
- The fork default branch is `master`. Resolve each integration target's real default branch; do not assume it is the same.
- New POC source is GPL-3.0-or-later. Preserve upstream file licenses and review distribution requirements before incorporating code into another distribution.

Owner authorization covers implementing the POC and preparing integration work.
Read the active task before release, flashing hardware, changing existing product
targets or uploading signed distributions; do not treat a handoff as evidence
those operations have already been completed.
