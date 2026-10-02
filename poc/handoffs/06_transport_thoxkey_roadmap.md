# Agent handoff 06 — Transport and ThoxKey follow-on slices

## Assignment

Plan and implement separately scoped follow-on paths after the current USB POC evidence is reviewed. Reuse the bounded job service where appropriate while preserving execution location, authentication, and workflow authority. These paths are proposed; this handoff does not claim they are implemented.

Repository baseline: [ttracx/thox-usbmuxd](https://github.com/ttracx/thox-usbmuxd), branch `master`, commit `af3372806f01a572f08105552f6072af0a2c4de2`.

The active source POC has 34 passing Python tests, 11 passing native Swift tests on Mac with Xcode 26.5 at the baseline commit, and an actual encrypted host CLI loopback/reconnect demo. An unsigned iOS simulator build also passed with Xcode 26.5 and the iPhoneSimulator26.5 SDK for arm64 and x86_64; see [validation](../VALIDATION.md). Physical USB compatibility has no result recorded. These facts establish no Wi-Fi, USB Ethernet, or ThoxKey/iOS compatibility.

## Scope boundaries

| Slice | Proposed implementation | Explicit dependency |
|---|---|---|
| Wi-Fi | Authenticated app-to-Mini networking on the chosen local network | A separately designed endpoint/discovery/pairing flow and iOS network permission handling |
| USB Ethernet | The same bounded application workflow over a qualified USB network interface | Exact iPhone, adapter/gadget implementation, firmware, cable, power, and addressing qualification |
| ThoxKey storage | User-selected external workspace/model data accessed by a native ThoxOS integration | Compatible external drive, security-scoped file access, and an iOS-compatible runtime packaged with the app |

Wi-Fi and USB Ethernet do not require usbmuxd or iproxy. Do not implement them by opening the existing loopback-only bridge to the LAN. Establish and review a separate authenticated service boundary. USB Ethernet uses network semantics; the Mini's USB data role may differ from its host role in the usbmuxd experiment and must be verified for the selected design.

ThoxKey's current storage-based role is separate. Connecting it does not launch a desktop Rust executable on iOS, supply independent host compute, or automatically create a usbmuxd connection. ThoxBeam remains the portable runtime engine within ThoxOS; an iOS execution path requires an iOS-compatible runtime included in the app and separately validated model support.

## Copyable agent prompt

```text
Own the follow-on transport and ThoxKey roadmap for ttracx/thox-usbmuxd.
Read ecosystem_map.md, mvp_catalog.md, development_queue.md, PROTOCOL.md, and current
validation evidence. Baseline master is af3372806f01a572f08105552f6072af0a2c4de2;
preserve newer changes and record the actual commit used.

Produce three distinct vertical slices: Wi-Fi networking, qualified USB Ethernet,
and ThoxKey external-storage/native-iOS execution. Clearly mark proposed work and
unvalidated hardware. Rank using the existing 1–5 weighted priority formula.

Reuse the bounded jobs/status/cancellation contract only where its authority model
fits. Design a separate network endpoint for Wi-Fi/Ethernet; do not widen the existing
loopback bridge or assume its shared-key experiment is production-ready. Preserve
executor disclosure, deliberate pairing, scoped requests, revocation, and no implicit
cloud fallback. Review current official platform documentation before implementation.

ThoxKey is a selected-files integration with an iOS-compatible runtime packaged inside
ThoxOS. Do not claim iOS can run the desktop launcher from the drive. Prove file access,
removal/reconnect behavior, model compatibility, memory use, and output persistence as
separate gates. Do not treat storage capacity as available inference RAM.

Own roadmap documents and newly agreed adapter paths. Coordinate with current host,
iOS, protocol, hardware, and QA owners before editing shared code. Deliver a small
complete slice with meaningful tests and measured evidence. Keep the established
customer hierarchy and update the ecosystem/MVP/development documents. No GitHub
Actions and no claims of TestFlight or production compatibility without evidence.
```

## Owned paths and dependency gates

- Primary ownership: `poc/docs/TRANSPORT_ROADMAP.md` and `poc/docs/THOXKEY_IOS_PLAN.md`.
- Shared planning updates: `ecosystem_map.md`, `mvp_catalog.md`, and `development_queue.md`, coordinated with the delivery owner.
- Proposed adapter code paths, created only after interface agreement: `poc/transports/` and a corresponding isolated iOS device-session adapter. Current `poc/host/`, `poc/ios/`, and `poc/PROTOCOL.md` remain owned by their implementation agents.
- Wi-Fi gate: select the listening endpoint, authenticated enrollment method, discovery policy, peer identity/revocation semantics, iOS permission flow, and reachable-network threat model before writing a LAN listener.
- USB Ethernet gate: select one physical implementation and document its USB/power/network roles. A generic claim that iOS supports Ethernet does not qualify a custom gadget.
- ThoxKey gate: select supported iPhone/iOS/drive formatting/power combinations and one actual native runtime/model pair. Verify current platform behavior using official documentation and device tests.
- Existing ThoxOS integration gate: access the current app repository and its TXF components. A standalone demonstration is not a shipping app integration.

## Minimum acceptance by slice

### Wi-Fi

Pair one selected Mini, show its identity and executor, submit a bounded job, stream or poll progress as specified, cancel, disconnect, and retrieve the same durable result after reconnect. Reject an unpaired caller and revoked peer. Obtain required local-network permissions through normal platform UI. Internet unavailability must not trigger a provider switch. Record the network topology and access scope without publishing private addresses or keys.

### USB Ethernet

First prove stable enumeration, assigned addressing, reachability, and safe power roles with the exact adapter/firmware combination. Then run the same approved job workflow over ordinary networking with usbmuxd/iproxy absent from that path. Verify cable removal, reattachment, device lock/background transitions, and peer authentication. Report the tested compatibility matrix rather than a general claim of support for every USB-C phone or cable.

### ThoxKey native storage

Use the system file picker to select a workspace or model-data file. Handle security-scoped access deliberately; read only the selected scope, validate imported packages, and fail clearly when access is revoked or the drive is removed. Run the qualified native model with the iPhone as the disclosed executor, then save a new approved artifact to the chosen location. Test reconnect, insufficient space, incompatible model, excessive memory requirements, and interrupted writes. A successful file-copy demonstration is not inference evidence.

## Proposed order

Review the USB POC results first. Use the existing weighted MVP catalog to prioritize a Wi-Fi slice and existing ThoxOS integration. Evaluate USB Ethernet in parallel only once a specific hardware candidate is available. Keep ThoxKey storage/runtime work independent so its native execution and file-access requirements do not become assumptions in the Mini connectivity implementation.

## Evidence and decision template

```markdown
# Follow-on slice decision
Slice: Wi-Fi / USB Ethernet / ThoxKey native storage
State: PROPOSED / IMPLEMENTED / VALIDATED ON LISTED COMBINATION
Repository / branch / commit:
Owner / dependencies / decision date:
Market / feasibility / speed / strategy scores (1–5):
Weighted priority:

Frontend behavior:
Backend or file-access boundary:
Workload and actual executor:
Pairing / permissions / revocation:
Hardware / OS / runtime / model combination:
Current official references reviewed:

| Acceptance case | Command or steps | Observed result | Evidence | Remaining limit |
|---|---|---|---|---|
| Initial access and authentication | | NOT RUN | | |
| Complete bounded workflow | | NOT RUN | | |
| Disconnect/reconnect | | NOT RUN | | |
| Cancellation or interrupted write | | NOT RUN | | |
| Invalid/revoked access | | NOT RUN | | |
| No unintended provider/network fallback | | NOT RUN | | |
| Resource and hardware behavior | | NOT RUN | | |

Go / hold decision and evidence:
Permitted product wording:
Next bounded implementation task:
```
