// SPDX-License-Identifier: GPL-3.0-or-later
import Foundation
import CryptoKit
import Security

public final class EncryptedChannel {
    public enum Role { case client, server }
    private let outgoingKey: SymmetricKey
    private let incomingKey: SymmetricKey
    private let outgoingDirection: String
    private let incomingDirection: String
    private var sendSequence: UInt64 = 0
    private var receiveSequence: UInt64 = 0

    public init(key: Data, clientNonce: Data, serverNonce: Data, role: Role) throws {
        guard key.count == 32, clientNonce.count == 32, serverNonce.count == 32 else {
            throw WireError.invalidKey
        }
        let salt = clientNonce + serverNonce
        let input = SymmetricKey(data: key)
        func derive(_ direction: String) -> SymmetricKey {
            HKDF<SHA256>.deriveKey(
                inputKeyMaterial: input, salt: salt,
                info: Data("THOX-USB-POC-v1/\(direction)".utf8), outputByteCount: 32
            )
        }
        outgoingDirection = role == .server ? "server" : "client"
        incomingDirection = role == .server ? "client" : "server"
        outgoingKey = derive(outgoingDirection)
        incomingKey = derive(incomingDirection)
    }

    public func encrypt(_ message: [String: Any]) throws -> [String: Any] {
        guard sendSequence < UInt64.max else { throw WireError.exhaustedSequence }
        let plaintext = try StrictJSON.encode(message)
        let sequenceBytes = Self.bytes(sendSequence)
        let sealed = try AES.GCM.seal(
            plaintext, using: outgoingKey,
            nonce: AES.GCM.Nonce(data: Data(repeating: 0, count: 4) + sequenceBytes),
            authenticating: Self.aad(outgoingDirection, sequenceBytes)
        )
        let envelope: [String: Any] = [
            "seq": NSNumber(value: sendSequence),
            "data": (sealed.ciphertext + sealed.tag).base64EncodedString()
        ]
        _ = try StrictJSON.encode(envelope) // Base64 overhead must also fit.
        sendSequence += 1
        return envelope
    }

    public func decrypt(_ envelope: [String: Any]) throws -> [String: Any] {
        guard Set(envelope.keys) == Set(["seq", "data"]),
              let sequence = StrictJSON.integer(envelope["seq"]),
              sequence == receiveSequence, sequence < UInt64.max else {
            throw WireError.invalidSequence
        }
        guard let encoded = envelope["data"] as? String,
              let combined = Data(base64Encoded: encoded), combined.count >= 16,
              combined.base64EncodedString() == encoded else { throw WireError.invalidJSON }
        let sequenceBytes = Self.bytes(sequence)
        let plaintext: Data
        do {
            let box = try AES.GCM.SealedBox(
                nonce: AES.GCM.Nonce(data: Data(repeating: 0, count: 4) + sequenceBytes),
                ciphertext: combined.dropLast(16), tag: combined.suffix(16)
            )
            plaintext = try AES.GCM.open(
                box, using: incomingKey, authenticating: Self.aad(incomingDirection, sequenceBytes)
            )
        } catch { throw WireError.authenticationFailed }
        let message = try StrictJSON.decode(plaintext)
        receiveSequence += 1
        return message
    }

    private static func bytes(_ value: UInt64) -> Data {
        Data((0..<8).reversed().map { UInt8((value >> ($0 * 8)) & 255) })
    }

    private static func aad(_ direction: String, _ sequence: Data) -> Data {
        Data("THOX-USB-POC-v1/\(direction)".utf8) + Data([0]) + sequence
    }
}

/// iOS is the authenticated application server even though application requests
/// subsequently travel from iOS to the host. A PSK never crosses this connection.
public final class ServerHandshake {
    private enum State { case hello, authentication, ready }
    private var state: State = .hello
    private let key: Data
    private let serverNonce: Data
    private var clientNonce: Data?
    public private(set) var channel: EncryptedChannel?
    public var isAuthenticated: Bool { channel != nil }

    public init(key: Data, nonce: Data? = nil) throws {
        guard key.count == 32 else { throw WireError.invalidKey }
        self.key = key
        if let nonce {
            guard nonce.count == 32 else { throw WireError.invalidHandshake }
            serverNonce = nonce
        } else {
            var bytes = [UInt8](repeating: 0, count: 32)
            guard SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes) == errSecSuccess else {
                throw WireError.authenticationFailed
            }
            serverNonce = Data(bytes)
        }
    }

    /// Returns hello_ack for hello, and encrypted ready for successful auth.
    public func accept(_ message: [String: Any]) throws -> [String: Any] {
        switch state {
        case .hello:
            guard Set(message.keys) == Set(["type", "version", "nonce"]),
                  message["type"] as? String == "hello", StrictJSON.integer(message["version"]) == 1,
                  let encoded = message["nonce"] as? String,
                  let nonce = Data(base64Encoded: encoded), nonce.count == 32,
                  nonce.base64EncodedString() == encoded else { throw WireError.invalidHandshake }
            clientNonce = nonce
            state = .authentication
            let proof = HMAC<SHA256>.authenticationCode(
                for: Self.proofInput("server", nonce, serverNonce), using: SymmetricKey(data: key)
            )
            return ["type": "hello_ack", "version": 1, "nonce": serverNonce.base64EncodedString(),
                    "proof": Data(proof).base64EncodedString()]
        case .authentication:
            guard Set(message.keys) == Set(["type", "proof"]), message["type"] as? String == "auth",
                  let encoded = message["proof"] as? String,
                  let proof = Data(base64Encoded: encoded), proof.count == 32,
                  proof.base64EncodedString() == encoded, let clientNonce else {
                throw WireError.invalidHandshake
            }
            guard HMAC<SHA256>.isValidAuthenticationCode(
                proof, authenticating: Self.proofInput("client", clientNonce, serverNonce),
                using: SymmetricKey(data: key)
            ) else { throw WireError.authenticationFailed }
            let established = try EncryptedChannel(
                key: key, clientNonce: clientNonce, serverNonce: serverNonce, role: .server
            )
            let ready = try established.encrypt(["type": "ready", "version": 1])
            channel = established
            state = .ready
            return ready
        case .ready:
            throw WireError.invalidHandshake
        }
    }

    private static func proofInput(_ role: String, _ clientNonce: Data, _ serverNonce: Data) -> Data {
        Data(role.utf8) + Data([0]) + clientNonce + serverNonce
    }
}
