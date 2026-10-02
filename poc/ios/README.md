# ThoxOS USB Lab for iOS

An isolated SwiftUI developer POC for ThoxMini ↔ iOS transport. It does not modify the shipping ThoxOS app. Minimum iOS 17; bundle `ai.thox.thoxos.usblab`; scheme `ThoxUSBLab`. The custom PSK protocol is experimental and requires independent review before production.

## Build

Open `ThoxUSBLab.xcodeproj` in Xcode, select your development team, and build for a connected iPhone. The checked-in project uses the local `THOXWire` package and no third-party dependencies. Team `DVJ6Z5343U` is the initial setting; signing/provisioning and registration remain operator tasks.

```sh
xcodebuild -project ThoxUSBLab.xcodeproj -scheme ThoxUSBLab \
  -destination 'generic/platform=iOS Simulator' CODE_SIGNING_ALLOWED=NO build
swift test
```

`project.yml` supports regeneration using XcodeGen. `python3 scripts/generate_project.py` regenerates the checked-in minimal project without extra dependencies. The Python generator and XcodeGen describe the same app target and local package.

## Pair and use

1. Generate a fresh 32-byte pairing key using the host CLI. Transfer it by a trusted path.
2. Open USB Lab, paste the standard base64 key, and choose **Save key**. The key is stored using `WhenUnlockedThisDeviceOnly` Keychain protection. It is never sent across the socket or saved in preferences.
3. Choose **Start USB listener**, keep the app in the foreground, and start host `iproxy` plus the Mini service as documented in the POC root README. Mini initiates the TCP connection. The listener binds IPv4 loopback `127.0.0.1:49321`.
4. Choose a UTF-8 plain text file no larger than 65,536 bytes. File access is scoped to the user selection; only pressing **Send selected text to Mini** sends its contents.
5. Choose **Analyze text** for deterministic statistics and a SHA-256 digest. This mode is not LLM inference. **Model inference** only appears when advertised by Mini; verify the displayed execution destination first.
6. Use **Refresh**, **Cancel job**, or the share control. The last accepted job ID survives app restarts; Mini stores the job and result. When the app reconnects it requests that saved job again.

Backgrounding stops the socket. Returning to the foreground restarts the listener if it was enabled. The host must reconnect. Requests, especially job submission, are never replayed automatically. The app saves the submission UUID as the job ID before sending, allowing `job_get` recovery if Mini accepted the job but its acknowledgement was lost. Refresh the saved job before submitting again; if Mini never accepted it, refresh returns not found.

## Security and scope

- Single connection, 10-second handshake deadline, 15-second request deadline, no secret logs.
- HMAC-SHA256 mutual PSK proof; HKDF directional keys; AES-GCM; exact sequence checks.
- 1,048,576-byte frames; incremental TCP parsing; duplicate JSON keys and excessive nesting rejected.
- No broad file access, raw USB API, shell execution, background entitlement, or automatic cloud fallback.
- Saved job ID uses preferences; pairing key uses Keychain; document text and displayed results are memory-only until explicitly shared.
- SwiftUI uses an emerald/ink lab appearance with system fonts. Branded font assets are not bundled; this is not a claim of full TXF conformance.
- There is no app icon set or App Store packaging in this developer build. Shipping ThoxOS integration, accessibility/UI validation on hardware, signing, and TestFlight are subsequent gates.

## Validation

`THOXWireTests` covers framing fragmentation/coalescing, invalid lengths, duplicate JSON keys, nesting, strict sequences, invalid pairing, handshake order, wrong proofs, AES-GCM tampering, replay, reflection and the shared Python interoperability vector (HMAC, HKDF, ciphertext and plaintext). Tests require Apple CryptoKit on macOS. This source delivery alone is not evidence that Xcode, simulator, physical USB or iOS background/reconnect tests passed; see the root validation report for actual execution evidence.

© 2026 THOX.ai LLC. All rights reserved, subject to applicable licenses.
THOX.ai™ and THOX product names and logos are trademarks of THOX.ai LLC.
Other marks belong to their respective owners.
