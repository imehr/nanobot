import Foundation
import XCTest
@testable import NanobotCapture

final class NativeCaptureClientTests: XCTestCase {
    func testTextPayloadBuildsJSONRequest() throws {
        let client = NativeCaptureClient(
            baseURL: URL(string: "http://127.0.0.1:18792")!,
            session: StubHTTPSession(),
            tokenStore: StubTokenStore(token: "secret-token")
        )

        let request = try client.makeRequest(
            for: .text(
                contentText: "Front tire pressure is 35 psi",
                userHint: "bike"
            )
        )

        XCTAssertEqual(request.httpMethod, "POST")
        XCTAssertEqual(request.url?.absoluteString, "http://127.0.0.1:18792/capture")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer secret-token")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"), "application/json")

        let body = try XCTUnwrap(request.httpBody)
        let json = try XCTUnwrap(JSONSerialization.jsonObject(with: body) as? [String: String])
        XCTAssertEqual(json["content_text"], "Front tire pressure is 35 psi")
        XCTAssertEqual(json["user_hint"], "bike")
    }

    func testFilePayloadBuildsMultipartRequest() throws {
        let tempURL = FileManager.default.temporaryDirectory.appendingPathComponent("service-invoice.pdf")
        try Data("invoice".utf8).write(to: tempURL)
        defer { try? FileManager.default.removeItem(at: tempURL) }

        let client = NativeCaptureClient(
            baseURL: URL(string: "http://127.0.0.1:18792")!,
            session: StubHTTPSession(),
            tokenStore: StubTokenStore(token: "secret-token")
        )

        let request = try client.makeRequest(
            for: .file(
                fileURL: tempURL,
                contentText: "This invoice is for my bike",
                userHint: "bike"
            )
        )

        let contentType = try XCTUnwrap(request.value(forHTTPHeaderField: "Content-Type"))
        XCTAssertTrue(contentType.contains("multipart/form-data; boundary="))
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer secret-token")

        let body = try XCTUnwrap(request.httpBody)
        let bodyText = try XCTUnwrap(String(data: body, encoding: .utf8))
        XCTAssertTrue(bodyText.contains("name=\"content_text\""))
        XCTAssertTrue(bodyText.contains("This invoice is for my bike"))
        XCTAssertTrue(bodyText.contains("name=\"user_hint\""))
        XCTAssertTrue(bodyText.contains("bike"))
        XCTAssertTrue(bodyText.contains("filename=\"service-invoice.pdf\""))
    }

    func testMissingTokenDoesNotAttachAuthorizationHeader() throws {
        let client = NativeCaptureClient(
            baseURL: URL(string: "http://127.0.0.1:18792")!,
            session: StubHTTPSession(),
            tokenStore: StubTokenStore(token: nil)
        )

        let request = try client.makeRequest(
            for: .text(
                contentText: "Service centre is ABC Motorcycles",
                userHint: "bike"
            )
        )

        XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
    }
}

private final class StubTokenStore: TokenStore, @unchecked Sendable {
    private var token: String?

    init(token: String?) {
        self.token = token
    }

    func readToken() throws -> String? {
        token
    }

    func writeToken(_ token: String) throws {
        self.token = token
    }
}

private struct StubHTTPSession: HTTPSession {
    func data(for request: URLRequest) async throws -> (Data, URLResponse) {
        let response = HTTPURLResponse(
            url: try XCTUnwrap(request.url),
            statusCode: 200,
            httpVersion: nil,
            headerFields: nil
        )!
        return (Data("{}".utf8), response)
    }
}
