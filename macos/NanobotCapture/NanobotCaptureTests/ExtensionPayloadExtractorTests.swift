import AppKit
import XCTest
@testable import NanobotCapture

@MainActor
final class ExtensionPayloadExtractorTests: XCTestCase {
    func testExtractsURLPayload() async throws {
        let extractor = ExtensionPayloadExtractor()
        let provider = NSItemProvider(object: NSURL(string: "https://example.com/bike-service")!)

        let payload = try await extractor.extract(from: [provider])

        XCTAssertEqual(payload.contentText, "https://example.com/bike-service")
        XCTAssertNil(payload.fileURL)
    }

    func testExtractsTextPayload() async throws {
        let extractor = ExtensionPayloadExtractor()
        let provider = NSItemProvider(object: NSString(string: "Front tire pressure is 35 psi"))

        let payload = try await extractor.extract(from: [provider])

        XCTAssertEqual(payload.contentText, "Front tire pressure is 35 psi")
        XCTAssertNil(payload.fileURL)
    }

    func testExtractsFileURLPayload() async throws {
        let extractor = ExtensionPayloadExtractor()
        let fileURL = FileManager.default.temporaryDirectory.appendingPathComponent("service-invoice.pdf")
        try Data("invoice".utf8).write(to: fileURL)
        defer { try? FileManager.default.removeItem(at: fileURL) }

        let provider = NSItemProvider(contentsOf: fileURL)!
        let payload = try await extractor.extract(from: [provider])

        XCTAssertEqual(payload.fileURL?.lastPathComponent, "service-invoice.pdf")
    }

    func testExtractsImagePayloadToTemporaryFile() async throws {
        let extractor = ExtensionPayloadExtractor()
        let image = NSImage(size: NSSize(width: 24, height: 24))
        image.lockFocus()
        NSColor.systemOrange.setFill()
        NSBezierPath(rect: NSRect(x: 0, y: 0, width: 24, height: 24)).fill()
        image.unlockFocus()

        let provider = NSItemProvider(object: image)
        let payload = try await extractor.extract(from: [provider])

        XCTAssertNotNil(payload.fileURL)
        XCTAssertTrue(FileManager.default.fileExists(atPath: payload.fileURL!.path))
    }
}
