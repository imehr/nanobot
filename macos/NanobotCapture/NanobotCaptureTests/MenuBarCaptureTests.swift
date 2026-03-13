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

    func testResultRenderingIncludesFollowUp() {
        let model = MenuBarCaptureViewModel()

        model.applyResult(
            CaptureResponse(
                inboxItemPath: "/tmp/inbox/item.md",
                entities: ["personal/bike"],
                actions: ["saved_original"],
                followUp: "Classify this as personal or business?"
            )
        )

        XCTAssertEqual(
            model.resultMessage,
            "Saved to /tmp/inbox/item.md\npersonal/bike\nsaved_original\nFollow-up: Classify this as personal or business?"
        )
    }
}
