# THOX USB POC protocol v1

Status: experimental. The Linux/Mini host initiates a TCP stream to the iOS app listener, directly for loopback testing or through `iproxy` for USB. The iOS app sends application requests after the host-initiated connection is authenticated. No HTTP reverse forwarding is assumed.

Every frame is a 4-byte unsigned big-endian length followed by UTF-8 JSON. Maximum body length: 1048576 bytes (1 MiB; accommodates worst-case JSON escaping and base64 for 65536-byte text). Reject zero, oversized, non-object, duplicate-key JSON, and unexpected handshake messages. Handshake timeout: 10 seconds. The out-of-band pairing key is 32 random bytes, encoded as standard base64. It is never sent over the connection.

Handshake (client = Mini; server = iOS):
1. Client sends `{"type":"hello","version":1,"nonce":"BASE64_32_BYTES"}`.
2. Server generates a fresh 32-byte nonce and sends `{"type":"hello_ack","version":1,"nonce":"BASE64_32_BYTES","proof":"BASE64_HMAC"}`. Proof = HMAC-SHA256(PSK, UTF8("server\\0") || clientNonce || serverNonce), where `\\0` denotes one zero byte.
3. Client verifies proof and sends `{"type":"auth","proof":"BASE64_HMAC"}`. Proof = HMAC-SHA256(PSK, UTF8("client\\0") || clientNonce || serverNonce).
4. Server verifies proof. Both sides derive two 32-byte keys with HKDF-SHA256(input=PSK, salt=clientNonce || serverNonce, info=UTF8("THOX-USB-POC-v1/client") or UTF8("THOX-USB-POC-v1/server")). Client key encrypts Mini→iOS; server key encrypts iOS→Mini. Server sends its first encrypted message `{"type":"ready","version":1}`.

Encrypted frame JSON: `{"seq":0,"data":"BASE64_CIPHERTEXT_PLUS_16_BYTE_TAG"}`. Use AES-256-GCM; nonce = four zero bytes followed by the unsigned 64-bit big-endian sequence. AAD = UTF8("THOX-USB-POC-v1/") || UTF8(direction: "client" or "server") || zero byte || the 8-byte sequence. Each direction starts at sequence 0; accept only the exact next sequence and increment only after authentication succeeds. A new handshake creates new keys on reconnect. Any authentication, sequence, framing, or JSON error closes the connection. This is a POC protocol requiring independent review before production.

Application requests (iOS→Mini): `{"type":"request","id":"UUID","op":"status","args":{}}`.
Responses (Mini→iOS): `{"type":"response","id":"UUID","ok":true,"result":{}}` or `{"type":"response","id":"UUID","ok":false,"error":{"code":"invalid_request","message":"..."}}`.

Operations:
- `ping`: returns `{"pong":true}`.
- `status`: returns device, version, transport, capabilities (array), executor.
- `job_submit`: args `{"text":"...","mode":"analyze"}` or mode `"inference"`; returns persisted job `{id,status,mode,created_at,updated_at,result,error}`. The request UUID is the durable job ID; persist it on iOS before sending. Repeating that submission UUID with identical text/mode returns the same job, while a differing payload is rejected. Text limit: 65536 UTF-8 bytes. Analyze is deterministic word/line/character statistics and SHA-256, explicitly not LLM output. Inference is optional, configured by the operator on the Mini only.
- `job_get`: args `{"job_id":"UUID"}`; returns job.
- `job_cancel`: args `{"job_id":"UUID"}`; returns job; terminal jobs unchanged.

Job states: queued, running, completed, failed, cancelled. Results survive link loss in SQLite on Mini. Inference jobs are never blindly retried after process restart; unfinished jobs become failed with an interrupted error. Optional inference runs in a child process with a 30-second total deadline; cancellation terminates that client process and discards late provider results; the POC does not promise cancellation of provider computation already in progress. No shell, arbitrary filesystem, endpoint override, or cloud fallback operation exists.
