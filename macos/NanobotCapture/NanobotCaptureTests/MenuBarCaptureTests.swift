import XCTest
@testable import NanobotCapture

@MainActor
final class MenuBarCaptureTests: XCTestCase {
    func testPasteTextFlowStoresNote() {
        let model = MenuBarCaptureViewModel()

        model.note = "Book the regular bike service"
        model.hint = "bike"

        XCTAssertEqual(model.note, "Book the regular bike service")
        XCTAssertEqual(model.hint, "bike")
    }

    func testClipboardActionLoadsIncomingText() {
        let model = MenuBarCaptureViewModel()

        let loaded = model.loadClipboardText("Front tire pressure is 35 psi")

        XCTAssertTrue(loaded)
        XCTAssertEqual(model.note, "Front tire pressure is 35 psi")
    }

    func testQueuedAndCompletedResultRenderingUsesQueueStatus() {
        let model = MenuBarCaptureViewModel()

        model.applyQueued(
            CaptureResponse(
                captureId: "cap-123",
                status: "queued",
                inboxItemPath: "/tmp/inbox/item.md",
                entities: [],
                actions: ["saved original", "queued"],
                followUp: nil
            )
        )

        XCTAssertEqual(model.resultMessage, "Queued cap-123")

        model.applyStatus(
            CaptureStatusResponse(
                captureId: "cap-123",
                status: "needs_input",
                sourceChannel: "telegram",
                captureType: "text",
                inboxItemPath: "/tmp/inbox/item.md",
                primaryPath: "/tmp/inbox/item.md",
                canonicalPaths: [],
                archivePaths: [],
                followUp: "Classify this as personal or business?",
                error: nil,
                queuedAt: "2026-03-14T10:00:00"
            )
        )

        XCTAssertEqual(model.resultMessage, "Classify this as personal or business?")
    }
}
