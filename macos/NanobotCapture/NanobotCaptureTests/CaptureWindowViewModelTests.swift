import Foundation
import XCTest
@testable import NanobotCapture

@MainActor
final class CaptureWindowViewModelTests: XCTestCase {
    func testNoteAndHintAreStored() {
        let model = CaptureWindowViewModel()

        model.note = "This is the regular bike service centre"
        model.hint = "bike"

        XCTAssertEqual(model.note, "This is the regular bike service centre")
        XCTAssertEqual(model.hint, "bike")
    }

    func testSelectingFilesDeduplicatesByURL() {
        let model = CaptureWindowViewModel()
        let invoice = URL(fileURLWithPath: "/tmp/invoice.pdf")
        let photo = URL(fileURLWithPath: "/tmp/photo.jpg")

        model.setSelectedFiles([invoice, invoice, photo])

        XCTAssertEqual(model.selectedFiles, [invoice, photo])
    }

    func testSubmitEnabledRequiresNoteOrFilesAndNoSubmissionInFlight() {
        let model = CaptureWindowViewModel()

        XCTAssertFalse(model.canSubmit)

        model.note = "Remember this service invoice"
        XCTAssertTrue(model.canSubmit)

        model.isSubmitting = true
        XCTAssertFalse(model.canSubmit)

        model.isSubmitting = false
        model.note = "   "
        model.setSelectedFiles([URL(fileURLWithPath: "/tmp/invoice.pdf")])
        XCTAssertTrue(model.canSubmit)
    }

    func testResultMessageIncludesRoutingSummary() {
        let model = CaptureWindowViewModel()

        model.applyResult(
            CaptureResponse(
                inboxItemPath: "/tmp/inbox/item.md",
                entities: ["personal/bike"],
                actions: ["saved_original", "updated_history"],
                followUp: "Mark this as personal or business?"
            )
        )

        XCTAssertEqual(
            model.resultMessage,
            "Saved to /tmp/inbox/item.md\nEntities: personal/bike\nActions: saved_original, updated_history\nFollow-up: Mark this as personal or business?"
        )
    }
}
