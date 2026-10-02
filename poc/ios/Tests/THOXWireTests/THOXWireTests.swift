// SPDX-License-Identifier: GPL-3.0-or-later
import XCTest
import CryptoKit
@testable import THOXWire

final class THOXWireTests: XCTestCase {
    private let key = Data((0..<32).map(UInt8.init))
    private let clientNonce = Data((32..<64).map(UInt8.init))
    private let serverNonce = Data((64..<96).map(UInt8.init))

    func testPythonInteroperabilityVector() throws {
        let url = try XCTUnwrap(Bundle.module.url(forResource: "crypto-vector-v1", withExtension: "json"))
        let vector = try JSONDecoder().decode([String: String].self, from: Data(contentsOf: url))
        func bytes(_ name: String) throws -> Data {
            try XCTUnwrap(Data(base64Encoded: try XCTUnwrap(vector[name])))
        }
        let psk = try bytes("pair_key")
        let client = try bytes("client_nonce")
        let server = try bytes("server_nonce")
        for direction in ["client", "server"] {
            let derived = HKDF<SHA256>.deriveKey(
                inputKeyMaterial: SymmetricKey(data: psk), salt: client + server,
                info: Data("THOX-USB-POC-v1/\(direction)".utf8), outputByteCount: 32
            )
            XCTAssertEqual(derived.withUnsafeBytes { Data($0) }, try bytes("\(direction)_key"))
            let proof = HMAC<SHA256>.authenticationCode(
                for: Data(direction.utf8) + Data([0]) + client + server,
                using: SymmetricKey(data: psk)
            )
            XCTAssertEqual(Data(proof), try bytes("\(direction)_proof"))
        }
        let handshake = try ServerHandshake(key: psk, nonce: server)
        let ack = try handshake.accept(["type": "hello", "version": 1, "nonce": client.base64EncodedString()])
        XCTAssertEqual(ack["proof"] as? String, vector["server_proof"])
        let ready = try handshake.accept(["type": "auth", "proof": try XCTUnwrap(vector["client_proof"])])
        XCTAssertEqual(ready["data"] as? String, vector["server_seq0_ciphertext"])
        XCTAssertEqual(StrictJSON.integer(ready["seq"]), 0)
        let peer = try EncryptedChannel(key: psk, clientNonce: client, serverNonce: server, role: .client)
        let plaintext = try peer.decrypt(["seq": 0, "data": try XCTUnwrap(vector["server_seq0_ciphertext"])])
        XCTAssertEqual(String(data: try StrictJSON.encode(plaintext), encoding: .utf8), vector["server_seq0_plaintext"])
        XCTAssertTrue(handshake.isAuthenticated)
    }

    func testTCPFragmentationAndCoalescing() throws {
        let one = try FrameCodec.encode(["a": "é"])
        let two = try FrameCodec.encode(["b": 3])
        var codec = FrameCodec()
        var messages = [[String: Any]]()
        for byte in one + two { messages += try codec.append(Data([byte])) }
        XCTAssertEqual(messages.count, 2)
        XCTAssertEqual(messages[0]["a"] as? String, "é")
        var coalesced = FrameCodec()
        XCTAssertEqual(try coalesced.append(one + two).count, 2)
    }

    func testFrameLengthRejectedBeforeBody() {
        for header in [Data([0, 0, 0, 0]), Data([0, 16, 0, 1]), Data([255, 255, 255, 255])] {
            var codec = FrameCodec()
            XCTAssertThrowsError(try codec.append(header))
        }
    }

    func testStrictJSONRejectsDuplicateAndEscapedDuplicateKeys() {
        for text in [#"{"id":1,"id":2}"#, #"{"id":1,"\u0069d":2}"#, #"{"args":{"x":1,"x":2}}"#, "[]", "null"] {
            XCTAssertThrowsError(try StrictJSON.decode(Data(text.utf8)))
        }
    }

    func testJSONDepthIsBounded() {
        let text = String(repeating: "{\"x\":", count: 35) + "1" + String(repeating: "}", count: 35)
        XCTAssertThrowsError(try StrictJSON.decode(Data(text.utf8)))
    }

    func testIntegersDoNotAcceptBooleanOrFraction() throws {
        let object = try StrictJSON.decode(Data(#"{"boolean":true,"fraction":0.5,"sequence":12,"negative":-1}"#.utf8))
        XCTAssertNil(StrictJSON.integer(object["boolean"]))
        XCTAssertNil(StrictJSON.integer(object["fraction"]))
        XCTAssertNil(StrictJSON.integer(object["negative"]))
        XCTAssertEqual(StrictJSON.integer(object["sequence"]), 12)
    }

    func testWrongPairingProofFailsClosed() throws {
        let handshake = try ServerHandshake(key: key, nonce: serverNonce)
        _ = try handshake.accept(["type": "hello", "version": 1, "nonce": clientNonce.base64EncodedString()])
        XCTAssertThrowsError(try handshake.accept(["type": "auth", "proof": Data(repeating: 0, count: 32).base64EncodedString()]))
        XCTAssertFalse(handshake.isAuthenticated)
    }

    func testUnexpectedHandshakeOrderRejected() throws {
        let handshake = try ServerHandshake(key: key)
        XCTAssertThrowsError(try handshake.accept(["type": "auth", "proof": "invalid"]))
        XCTAssertFalse(handshake.isAuthenticated)
    }

    func testAuthenticatedRoundTripReplayAndDirectionSeparation() throws {
        let server = try EncryptedChannel(key: key, clientNonce: clientNonce, serverNonce: serverNonce, role: .server)
        let client = try EncryptedChannel(key: key, clientNonce: clientNonce, serverNonce: serverNonce, role: .client)
        let frame = try server.encrypt(["type": "request", "text": "Portable private work."])
        XCTAssertThrowsError(try server.decrypt(frame)) // Reflection uses a different key/AAD.
        XCTAssertEqual(try client.decrypt(frame)["text"] as? String, "Portable private work.")
        XCTAssertThrowsError(try client.decrypt(frame)) // Replay cannot consume a second sequence.
        let response = try client.encrypt(["type": "response", "ok": true])
        XCTAssertEqual(try server.decrypt(response)["ok"] as? Bool, true)
    }

    func testTamperingDoesNotAdvanceReceiveSequence() throws {
        let server = try EncryptedChannel(key: key, clientNonce: clientNonce, serverNonce: serverNonce, role: .server)
        let client = try EncryptedChannel(key: key, clientNonce: clientNonce, serverNonce: serverNonce, role: .client)
        let original = try server.encrypt(["type": "ready", "version": 1])
        var modified = original
        var bytes = try XCTUnwrap(Data(base64Encoded: try XCTUnwrap(original["data"] as? String)))
        bytes[bytes.startIndex] ^= 1
        modified["data"] = bytes.base64EncodedString()
        XCTAssertThrowsError(try client.decrypt(modified))
        XCTAssertEqual(try client.decrypt(original)["type"] as? String, "ready")
    }

    func testPairingKeyValidation() throws {
        XCTAssertEqual(try PairingKey.decode(key.base64EncodedString()), key)
        XCTAssertThrowsError(try PairingKey.decode("not a key"))
        XCTAssertThrowsError(try PairingKey.decode(Data(repeating: 0, count: 31).base64EncodedString()))
        XCTAssertThrowsError(try PairingKey.decode(String(key.base64EncodedString().dropLast())))
    }
}
