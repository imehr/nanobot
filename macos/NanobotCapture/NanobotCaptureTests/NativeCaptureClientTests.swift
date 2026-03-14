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

    func testSubmitDecodesSnakeCaseQueuedResponse() async throws {
        let data = """
        {
          "capture_id": "cap-123",
          "status": "queued",
          "inbox_item_path": "/tmp/item",
          "entities": [],
          "actions": ["saved original", "queued"],
          "follow_up": null
        }
        """.data(using: .utf8)!

        let client = NativeCaptureClient(
            baseURL: URL(string: "http://127.0.0.1:18792")!,
            session: StubHTTPSession(responseData: data),
            tokenStore: StubTokenStore(token: "secret-token")
        )

        let response = try await client.submit(.text(contentText: "Bike note", userHint: "bike"))

        XCTAssertEqual(response.captureId, "cap-123")
        XCTAssertEqual(response.status, "queued")
        XCTAssertEqual(response.inboxItemPath, "/tmp/item")
    }

    func testFetchRecentCapturesDecodesStatusPayload() async throws {
        let data = """
        {
          "captures": [
            {
              "capture_id": "cap-1",
              "status": "completed",
              "source_channel": "telegram",
              "capture_type": "text",
              "inbox_item_path": "/tmp/item",
              "primary_path": "/Mehr/Personal/motorbike/bmw-c400gt.md",
              "canonical_paths": ["/Mehr/Personal/motorbike/bmw-c400gt.md"],
              "archive_paths": [],
              "follow_up": null,
              "error": null,
              "queued_at": "2026-03-14T10:00:00"
            }
          ]
        }
        """.data(using: .utf8)!

        let client = NativeCaptureClient(
            baseURL: URL(string: "http://127.0.0.1:18792")!,
            session: StubHTTPSession(responseData: data),
            tokenStore: StubTokenStore(token: "secret-token")
        )

        let captures = try await client.fetchRecentCaptures()

        XCTAssertEqual(captures.count, 1)
        XCTAssertEqual(captures[0].captureId, "cap-1")
        XCTAssertEqual(captures[0].sourceChannel, "telegram")
        XCTAssertEqual(captures[0].primaryPath, "/Mehr/Personal/motorbike/bmw-c400gt.md")
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
    var responseData: Data = Data("{}".utf8)

    func data(for request: URLRequest) async throws -> (Data, URLResponse) {
        let response = HTTPURLResponse(
            url: try XCTUnwrap(request.url),
            statusCode: 200,
            httpVersion: nil,
            headerFields: nil
        )!
        return (responseData, response)
    }
}
