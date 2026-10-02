// SPDX-License-Identifier: GPL-3.0-or-later
import Foundation

public enum WireError: Error, LocalizedError {
    case invalidFrame, invalidJSON, duplicateKey, invalidHandshake, authenticationFailed
    case invalidKey, invalidSequence, exhaustedSequence, messageTooLarge

    public var errorDescription: String? {
        switch self {
        case .invalidFrame: return "Invalid or oversized frame."
        case .invalidJSON: return "Invalid protocol JSON."
        case .duplicateKey: return "Duplicate JSON key rejected."
        case .invalidHandshake: return "Unexpected handshake message."
        case .authenticationFailed: return "Authentication failed. Check the pairing key on both devices."
        case .invalidKey: return "Pairing key must be standard base64 encoding exactly 32 bytes."
        case .invalidSequence: return "Message sequence rejected. Reconnect to establish a fresh session."
        case .exhaustedSequence: return "Session message limit reached. Reconnect."
        case .messageTooLarge: return "Message exceeds the protocol size limit."
        }
    }
}

public enum PairingKey {
    public static func decode(_ text: String) throws -> Data {
        let clean = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let bytes = Data(base64Encoded: clean), bytes.count == 32,
              bytes.base64EncodedString() == clean else { throw WireError.invalidKey }
        return bytes
    }
}
