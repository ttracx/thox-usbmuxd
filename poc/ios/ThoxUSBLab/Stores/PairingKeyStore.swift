// SPDX-License-Identifier: GPL-3.0-or-later
import Foundation
import Security

enum PairingKeyStore {
    private static let service = "ai.thox.thoxos.usblab.pairing"
    private static let account = "mini-psk-v1"

    static func load() throws -> Data? {
        var query = identity
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess, let data = result as? Data, data.count == 32 else {
            throw failure(status)
        }
        return data
    }

    static func save(_ data: Data) throws {
        guard data.count == 32 else { throw failure(errSecParam) }
        let attributes: [String: Any] = [
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        ]
        let update = SecItemUpdate(identity as CFDictionary, attributes as CFDictionary)
        if update == errSecItemNotFound {
            var item = identity
            attributes.forEach { item[$0.key] = $0.value }
            let status = SecItemAdd(item as CFDictionary, nil)
            guard status == errSecSuccess else { throw failure(status) }
        } else if update != errSecSuccess { throw failure(update) }
    }

    static func remove() throws {
        let status = SecItemDelete(identity as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else { throw failure(status) }
    }

    private static var identity: [String: Any] {
        [kSecClass as String: kSecClassGenericPassword,
         kSecAttrService as String: service, kSecAttrAccount as String: account,
         kSecAttrSynchronizable as String: false]
    }

    private static func failure(_ status: OSStatus) -> NSError {
        NSError(domain: "THOXKeychain", code: Int(status), userInfo: [
            NSLocalizedDescriptionKey: "Pairing key storage failed (\(status)). Unlock the device and try again."
        ])
    }
}
