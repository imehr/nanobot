import Foundation

protocol HTTPSession: Sendable {
    func data(for request: URLRequest) async throws -> (Data, URLResponse)
}

extension URLSession: HTTPSession {}

struct CaptureResponse: Decodable {
    let captureId: String
    let status: String
    let inboxItemPath: String
    let entities: [String]
    let actions: [String]
    let followUp: String?
}

struct CaptureStatusResponse: Decodable, Identifiable, Equatable {
    let captureId: String
    let status: String
    let sourceChannel: String
    let captureType: String
    let inboxItemPath: String
    let primaryPath: String
    let canonicalPaths: [String]
    let archivePaths: [String]
    let followUp: String?
    let error: String?
    let queuedAt: String?

    var id: String { captureId }
}

private struct RecentCapturesResponse: Decodable {
    let captures: [CaptureStatusResponse]
}

enum NativeCaptureClientError: Error {
    case invalidResponse
    case serverError(statusCode: Int, message: String)
    case filePayloadRequired
}

final class NativeCaptureClient: @unchecked Sendable {
    private let baseURL: URL
    private let captureURL: URL
    private let session: HTTPSession
    private let tokenStore: TokenStore

    init(
        baseURL: URL,
        session: HTTPSession = URLSession.shared,
        tokenStore: TokenStore = KeychainStore()
    ) {
        self.baseURL = baseURL
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
        return try await decode(CaptureResponse.self, request: request)
    }

    func fetchCapture(_ captureID: String) async throws -> CaptureStatusResponse {
        var request = URLRequest(url: baseURL.appendingPathComponent("captures").appendingPathComponent(captureID))
        request.httpMethod = "GET"
        try applyAuthorization(to: &request)
        return try await decode(CaptureStatusResponse.self, request: request)
    }

    func fetchRecentCaptures() async throws -> [CaptureStatusResponse] {
        var request = URLRequest(url: baseURL.appendingPathComponent("captures/recent"))
        request.httpMethod = "GET"
        try applyAuthorization(to: &request)
        let response = try await decode(RecentCapturesResponse.self, request: request)
        return response.captures
    }

    func retractCapture(_ captureID: String) async throws -> CaptureStatusResponse {
        var request = URLRequest(
            url: baseURL.appendingPathComponent("captures").appendingPathComponent(captureID).appendingPathComponent("retract")
        )
        request.httpMethod = "POST"
        try applyAuthorization(to: &request)
        return try await decode(CaptureStatusResponse.self, request: request)
    }

    func retryCapture(_ captureID: String) async throws -> CaptureStatusResponse {
        var request = URLRequest(
            url: baseURL.appendingPathComponent("captures").appendingPathComponent(captureID).appendingPathComponent("retry")
        )
        request.httpMethod = "POST"
        try applyAuthorization(to: &request)
        return try await decode(CaptureStatusResponse.self, request: request)
    }

    private func applyAuthorization(to request: inout URLRequest) throws {
        if let token = try tokenStore.readToken(), !token.isEmpty {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
    }

    private func decode<T: Decodable>(_ type: T.Type, request: URLRequest) async throws -> T {
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw NativeCaptureClientError.invalidResponse
        }
        guard (200..<300).contains(httpResponse.statusCode) else {
            let message = String(data: data, encoding: .utf8) ?? ""
            throw NativeCaptureClientError.serverError(statusCode: httpResponse.statusCode, message: message)
        }
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(type, from: data)
    }
}
