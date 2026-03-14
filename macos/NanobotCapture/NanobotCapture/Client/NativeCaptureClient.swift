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
    let projectMemoryPaths: [String]
    let followUp: String?

    init(
        captureId: String,
        status: String,
        inboxItemPath: String,
        entities: [String],
        actions: [String],
        projectMemoryPaths: [String] = [],
        followUp: String?
    ) {
        self.captureId = captureId
        self.status = status
        self.inboxItemPath = inboxItemPath
        self.entities = entities
        self.actions = actions
        self.projectMemoryPaths = projectMemoryPaths
        self.followUp = followUp
    }

    private enum CodingKeys: String, CodingKey {
        case captureId, status, inboxItemPath, entities, actions, projectMemoryPaths, followUp
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        captureId = try container.decode(String.self, forKey: .captureId)
        status = try container.decode(String.self, forKey: .status)
        inboxItemPath = try container.decode(String.self, forKey: .inboxItemPath)
        entities = try container.decode([String].self, forKey: .entities)
        actions = try container.decode([String].self, forKey: .actions)
        projectMemoryPaths = try container.decodeIfPresent([String].self, forKey: .projectMemoryPaths) ?? []
        followUp = try container.decodeIfPresent(String.self, forKey: .followUp)
    }
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
    let projectMemoryPaths: [String]
    let followUp: String?
    let error: String?
    let queuedAt: String?

    var id: String { captureId }

    init(
        captureId: String,
        status: String,
        sourceChannel: String,
        captureType: String,
        inboxItemPath: String,
        primaryPath: String,
        canonicalPaths: [String],
        archivePaths: [String],
        projectMemoryPaths: [String] = [],
        followUp: String?,
        error: String?,
        queuedAt: String?
    ) {
        self.captureId = captureId
        self.status = status
        self.sourceChannel = sourceChannel
        self.captureType = captureType
        self.inboxItemPath = inboxItemPath
        self.primaryPath = primaryPath
        self.canonicalPaths = canonicalPaths
        self.archivePaths = archivePaths
        self.projectMemoryPaths = projectMemoryPaths
        self.followUp = followUp
        self.error = error
        self.queuedAt = queuedAt
    }

    private enum CodingKeys: String, CodingKey {
        case captureId, status, sourceChannel, captureType, inboxItemPath, primaryPath
        case canonicalPaths, archivePaths, projectMemoryPaths, followUp, error, queuedAt
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        captureId = try container.decode(String.self, forKey: .captureId)
        status = try container.decode(String.self, forKey: .status)
        sourceChannel = try container.decode(String.self, forKey: .sourceChannel)
        captureType = try container.decode(String.self, forKey: .captureType)
        inboxItemPath = try container.decode(String.self, forKey: .inboxItemPath)
        primaryPath = try container.decode(String.self, forKey: .primaryPath)
        canonicalPaths = try container.decodeIfPresent([String].self, forKey: .canonicalPaths) ?? []
        archivePaths = try container.decodeIfPresent([String].self, forKey: .archivePaths) ?? []
        projectMemoryPaths = try container.decodeIfPresent([String].self, forKey: .projectMemoryPaths) ?? []
        followUp = try container.decodeIfPresent(String.self, forKey: .followUp)
        error = try container.decodeIfPresent(String.self, forKey: .error)
        queuedAt = try container.decodeIfPresent(String.self, forKey: .queuedAt)
    }
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
    private let explicitToken: String?

    init(
        baseURL: URL,
        session: HTTPSession = URLSession.shared,
        tokenStore: TokenStore = KeychainStore(),
        token: String? = nil
    ) {
        self.baseURL = baseURL
        self.captureURL = baseURL.appendingPathComponent("capture")
        self.session = session
        self.tokenStore = tokenStore
        let trimmedToken = token?.trimmingCharacters(in: .whitespacesAndNewlines)
        self.explicitToken = (trimmedToken?.isEmpty == false) ? trimmedToken : nil
    }

    func currentToken() throws -> String? {
        if let explicitToken {
            return explicitToken
        }
        return try tokenStore.readToken()
    }

    func storeToken(_ token: String) throws {
        try tokenStore.writeToken(token)
    }

    func makeRequest(for payload: CapturePayload) throws -> URLRequest {
        var request = URLRequest(url: captureURL)
        request.httpMethod = "POST"

        if let token = try authorizationToken() {
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
        if let token = try authorizationToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
    }

    private func authorizationToken() throws -> String? {
        if let explicitToken {
            return explicitToken
        }
        guard let token = try tokenStore.readToken(), !token.isEmpty else {
            return nil
        }
        return token
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
