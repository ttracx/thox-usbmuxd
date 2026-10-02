// SPDX-License-Identifier: GPL-3.0-or-later
import Foundation

/// A TCP receive is not a frame. This decoder retains partial headers/bodies and
/// emits every complete frame, checking lengths before waiting for more bytes.
public struct FrameCodec {
    private var buffer = Data()
    public init() {}

    public mutating func append(_ bytes: Data) throws -> [[String: Any]] {
        // Network.framework reads at most 64 KiB per call; reject misuse as well.
        guard bytes.count <= 65_536 else { throw WireError.invalidFrame }
        buffer.append(bytes)
        var result = [[String: Any]]()
        while buffer.count >= 4 {
            let length = buffer.prefix(4).reduce(UInt32(0)) { ($0 << 8) | UInt32($1) }
            guard length > 0, length <= StrictJSON.maximumBytes else { throw WireError.invalidFrame }
            let total = 4 + Int(length)
            guard buffer.count >= total else { break }
            result.append(try StrictJSON.decode(Data(buffer.dropFirst(4).prefix(Int(length)))))
            buffer = Data(buffer.dropFirst(total))
        }
        guard buffer.count <= StrictJSON.maximumBytes + 4 else { throw WireError.invalidFrame }
        return result
    }

    public static func encode(_ dictionary: [String: Any]) throws -> Data {
        let body = try StrictJSON.encode(dictionary)
        let count = UInt32(body.count)
        var frame = Data([
            UInt8((count >> 24) & 255), UInt8((count >> 16) & 255),
            UInt8((count >> 8) & 255), UInt8(count & 255)
        ])
        frame.append(body)
        return frame
    }
}
