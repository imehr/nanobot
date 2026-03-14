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

    func testQueuedAndCompletedMessagesUseQueueStatus() {
        let model = CaptureWindowViewModel()

        model.applyQueued(
            [
                CaptureResponse(
                    captureId: "cap-123",
                    status: "queued",
                    inboxItemPath: "/tmp/inbox/item.md",
                    entities: [],
                    actions: ["saved original", "queued"],
                    followUp: nil
                )
            ]
        )

        XCTAssertEqual(model.resultMessage, "Queued 1 capture(s): cap-123")

        model.applyStatus(
            CaptureStatusResponse(
                captureId: "cap-123",
                status: "completed",
                sourceChannel: "telegram",
                captureType: "text",
                inboxItemPath: "/tmp/inbox/item.md",
                primaryPath: "/Mehr/Personal/motorbike/bmw-c400gt.md",
                canonicalPaths: ["/Mehr/Personal/motorbike/bmw-c400gt.md"],
                archivePaths: [],
                followUp: nil,
                error: nil,
                queuedAt: "2026-03-14T10:00:00"
            )
        )

        XCTAssertEqual(
            model.resultMessage,
            "Saved to Mehr: /Mehr/Personal/motorbike/bmw-c400gt.md"
        )
    }

    func testApplyErrorShowsFailureMessage() {
        let model = CaptureWindowViewModel()

        model.applyError(
            NSError(domain: "NanobotCaptureTests", code: 1, userInfo: [NSLocalizedDescriptionKey: "network issue"])
        )

        XCTAssertEqual(model.resultMessage, "Capture failed: network issue")
    }
}
