// SPDX-License-Identifier: GPL-3.0-or-later
import Foundation
import CoreFoundation

/// Foundation validates JSON syntax; a second bounded walk rejects duplicate keys,
/// including escaped equivalents such as "id" and "\u0069d".
public enum StrictJSON {
    public static let maximumBytes = 1_048_576

    public static func decode(_ data: Data) throws -> [String: Any] {
        guard !data.isEmpty, data.count <= maximumBytes,
              String(data: data, encoding: .utf8) != nil,
              let object = try? JSONSerialization.jsonObject(with: data),
              let dictionary = object as? [String: Any] else { throw WireError.invalidJSON }
        var scanner = KeyScanner(bytes: Array(data))
        try scanner.value(depth: 0)
        scanner.whitespace()
        guard scanner.index == scanner.bytes.count else { throw WireError.invalidJSON }
        return dictionary
    }

    public static func encode(_ dictionary: [String: Any]) throws -> Data {
        guard JSONSerialization.isValidJSONObject(dictionary) else { throw WireError.invalidJSON }
        let data = try JSONSerialization.data(withJSONObject: dictionary, options: [.sortedKeys])
        guard !data.isEmpty, data.count <= maximumBytes else { throw WireError.messageTooLarge }
        return data
    }

    public static func integer(_ value: Any?) -> UInt64? {
        guard let number = value as? NSNumber,
              CFGetTypeID(number) != CFBooleanGetTypeID(),
              // Require integer JSON syntax, not floats rounded to an integer.
              !["f", "d"].contains(String(cString: number.objCType)),
              !number.stringValue.hasPrefix("-") else { return nil }
        return UInt64(number.stringValue)
    }
}

private struct KeyScanner {
    let bytes: [UInt8]
    var index = 0

    mutating func whitespace() {
        while index < bytes.count, [9, 10, 13, 32].contains(bytes[index]) { index += 1 }
    }

    mutating func value(depth: Int) throws {
        guard depth <= 32 else { throw WireError.invalidJSON }
        whitespace()
        guard index < bytes.count else { throw WireError.invalidJSON }
        switch bytes[index] {
        case 123: // Object.
            index += 1
            var keys = Set<String>()
            whitespace()
            if consume(125) { return }
            while true {
                whitespace()
                let key = try string()
                guard keys.insert(key).inserted else { throw WireError.duplicateKey }
                whitespace()
                guard consume(58) else { throw WireError.invalidJSON }
                try value(depth: depth + 1)
                whitespace()
                if consume(125) { return }
                guard consume(44) else { throw WireError.invalidJSON }
            }
        case 91: // Array.
            index += 1
            whitespace()
            if consume(93) { return }
            while true {
                try value(depth: depth + 1)
                whitespace()
                if consume(93) { return }
                guard consume(44) else { throw WireError.invalidJSON }
            }
        case 34:
            _ = try string()
        default:
            let start = index
            while index < bytes.count, ![9, 10, 13, 32, 44, 93, 125].contains(bytes[index]) { index += 1 }
            guard index > start else { throw WireError.invalidJSON }
        }
    }

    mutating func consume(_ byte: UInt8) -> Bool {
        guard index < bytes.count, bytes[index] == byte else { return false }
        index += 1
        return true
    }

    mutating func string() throws -> String {
        let start = index
        guard consume(34) else { throw WireError.invalidJSON }
        while index < bytes.count {
            let byte = bytes[index]
            index += 1
            if byte == 92 {
                guard index < bytes.count else { throw WireError.invalidJSON }
                index += 1
            } else if byte == 34 {
                return try JSONDecoder().decode(String.self, from: Data(bytes[start..<index]))
            }
        }
        throw WireError.invalidJSON
    }
}
