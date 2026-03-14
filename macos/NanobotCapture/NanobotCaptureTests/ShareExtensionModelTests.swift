import Foundation
import XCTest
@testable import NanobotCapture

@MainActor
final class ShareExtensionModelTests: XCTestCase {
    func testDescribeCompletedStatusUsesCanonicalPath() {
        let model = ShareExtensionModel(client: NativeCaptureClient(baseURL: URL(string: "http://127.0.0.1:18792")!))
        let status = CaptureStatusResponse(
            captureId: "cap-1",
            status: "completed",
            sourceChannel: "telegram",
            captureType: "image",
            inboxItemPath: "/tmp/item",
            primaryPath: "/Mehr/Personal/motorbike/bmw-c400gt.md",
            canonicalPaths: ["/Mehr/Personal/motorbike/bmw-c400gt.md"],
            archivePaths: [],
            followUp: nil,
            error: nil,
            queuedAt: "2026-03-14T10:00:00"
        )

        XCTAssertEqual(model.describe(status: status), "Saved to Mehr: /Mehr/Personal/motorbike/bmw-c400gt.md")
    }
}
