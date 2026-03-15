import AppKit
import XCTest
import UniformTypeIdentifiers
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

    func testExtractsRTFPayload() async throws {
        let extractor = ExtensionPayloadExtractor()
        let text = "Front tire pressure is 35 psi"
        let rtfData = try NSAttributedString(string: text).data(
            from: NSRange(location: 0, length: text.count),
            documentAttributes: [.documentType: NSAttributedString.DocumentType.rtf]
        )
        let provider = NSItemProvider()
        provider.registerDataRepresentation(forTypeIdentifier: UTType.rtf.identifier, visibility: .all) { completion in
            completion(rtfData, nil)
            return nil
        }

        let payload = try await extractor.extract(from: [provider])

        XCTAssertEqual(payload.contentText, text)
        XCTAssertNil(payload.fileURL)
    }

    func testExtractsHTMLPayload() async throws {
        let extractor = ExtensionPayloadExtractor()
        let htmlData = Data("<p>Front tire pressure is <b>35 psi</b></p>".utf8)
        let provider = NSItemProvider()
        provider.registerDataRepresentation(forTypeIdentifier: UTType.html.identifier, visibility: .all) { completion in
            completion(htmlData, nil)
            return nil
        }

        let payload = try await extractor.extract(from: [provider])

        XCTAssertEqual(payload.contentText, "Front tire pressure is 35 psi")
        XCTAssertNil(payload.fileURL)
    }

    func testExtractsRTFDPayload() async throws {
        let extractor = ExtensionPayloadExtractor()
        let text = "This note came from Notes Send Copy"
        let rtfdData = try NSAttributedString(string: text).data(
            from: NSRange(location: 0, length: text.count),
            documentAttributes: [.documentType: NSAttributedString.DocumentType.rtfd]
        )
        let provider = NSItemProvider()
        provider.registerDataRepresentation(forTypeIdentifier: UTType.rtfd.identifier, visibility: .all) { completion in
            completion(rtfdData, nil)
            return nil
        }

        let payload = try await extractor.extract(from: [provider])

        XCTAssertEqual(payload.contentText, text)
        XCTAssertNil(payload.fileURL)
    }

    func testExtractsFlatRTFDPayload() async throws {
        let extractor = ExtensionPayloadExtractor()
        let text = "This note came from Notes Send Copy"
        let rtfdData = try NSAttributedString(string: text).data(
            from: NSRange(location: 0, length: text.count),
            documentAttributes: [.documentType: NSAttributedString.DocumentType.rtfd]
        )
        let provider = NSItemProvider()
        provider.registerDataRepresentation(forTypeIdentifier: UTType.flatRTFD.identifier, visibility: .all) { completion in
            completion(rtfdData, nil)
            return nil
        }

        let payload = try await extractor.extract(from: [provider])

        XCTAssertEqual(payload.contentText, text)
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
