import Foundation

protocol HTTPSession {
    func data(for request: URLRequest) async throws -> (Data, URLResponse)
}

extension URLSession: HTTPSession {}

struct CaptureResponse: Decodable {
    let inboxItemPath: String
    let entities: [String]
    let actions: [String]
    let followUp: String?
}

enum NativeCaptureClientError: Error {
    case invalidResponse
    case serverError(statusCode: Int, message: String)
    case filePayloadRequired
}

final class NativeCaptureClient {
    private let captureURL: URL
    private let session: HTTPSession
    private let tokenStore: TokenStore

    init(
        baseURL: URL,
        session: HTTPSession = URLSession.shared,
        tokenStore: TokenStore = KeychainStore()
    ) {
        self.captureURL = baseURL.appendingPathComponent("capture")
        self.session = session
        self.tokenStore = tokenStore
    }

    func currentToken() throws -> String? {
        try tokenStore.readToken()
    }

    func storeToken(_ token: String) throws {
        try tokenStore.writeToken(token)
    }

    func makeRequest(for payload: CapturePayload) throws -> URLRequest {
        var request = URLRequest(url: captureURL)
        request.httpMethod = "POST"

        if let token = try tokenStore.readToken(), !token.isEmpty {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        if payload.usesMultipart {
            let boundary = "NanobotCaptureBoundary\(UUID().uuidString)"
            request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
            request.httpBody = try payload.multipartData(boundary: boundary)
        } else {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try payload.jsonData()
        }

        return request
    }

    func submit(_ payload: CapturePayload) async throws -> CaptureResponse {
        let request = try makeRequest(for: payload)
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw NativeCaptureClientError.invalidResponse
        }
        guard (200..<300).contains(httpResponse.statusCode) else {
            let message = String(data: data, encoding: .utf8) ?? ""
            throw NativeCaptureClientError.serverError(statusCode: httpResponse.statusCode, message: message)
        }
        return try JSONDecoder().decode(CaptureResponse.self, from: data)
    }
}
