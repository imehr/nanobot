import Foundation
import Security

protocol TokenStore {
    func readToken() throws -> String?
    func writeToken(_ token: String) throws
}

enum KeychainStoreError: Error {
    case unexpectedStatus(OSStatus)
    case invalidData
}

final class KeychainStore: TokenStore {
    private let service: String
    private let account: String

    init(
        service: String = "ai.nanobot.capture",
        account: String = "nativeCaptureAuthToken"
    ) {
        self.service = service
        self.account = account
    }

    func readToken() throws -> String? {
        var query = baseQuery()
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne

        var result: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        if status == errSecItemNotFound {
            return nil
        }
        guard status == errSecSuccess else {
            throw KeychainStoreError.unexpectedStatus(status)
        }
        guard
            let data = result as? Data,
            let token = String(data: data, encoding: .utf8)
        else {
            throw KeychainStoreError.invalidData
        }
        return token
    }

    func writeToken(_ token: String) throws {
        let data = Data(token.utf8)
        let status = SecItemCopyMatching(baseQuery() as CFDictionary, nil)
        if status == errSecSuccess {
            let updateStatus = SecItemUpdate(
                baseQuery() as CFDictionary,
                [kSecValueData as String: data] as CFDictionary
            )
            guard updateStatus == errSecSuccess else {
                throw KeychainStoreError.unexpectedStatus(updateStatus)
            }
            return
        }

        if status != errSecItemNotFound {
            throw KeychainStoreError.unexpectedStatus(status)
        }

        var addQuery = baseQuery()
        addQuery[kSecValueData as String] = data
        let addStatus = SecItemAdd(addQuery as CFDictionary, nil)
        guard addStatus == errSecSuccess else {
            throw KeychainStoreError.unexpectedStatus(addStatus)
        }
    }

    private func baseQuery() -> [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
    }
}
