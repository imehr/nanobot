import AppKit
import Foundation
import UniformTypeIdentifiers
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

        XCTAssertEqual(model.attachments.map(\.fileURL), [invoice, photo])
    }

    func testApplyingPastedFilePayloadAddsAttachment() {
        let model = CaptureWindowViewModel()
        let screenshot = URL(fileURLWithPath: "/tmp/screenshot.png")

        model.applyExtractedPayload(
            ExtractedExtensionPayload(contentText: nil, fileURL: screenshot)
        )

        XCTAssertEqual(model.attachments.count, 1)
        XCTAssertEqual(model.attachments.first?.fileURL, screenshot)
        XCTAssertEqual(model.attachments.first?.displayName, "screenshot.png")
        XCTAssertEqual(model.attachments.first?.kind, .image)
    }

    func testHandlePasteProvidersWithImageDataAddsAttachment() async throws {
        let appState = AppState()
        let image = NSImage(size: NSSize(width: 2, height: 2))
        image.lockFocus()
        NSColor.systemBlue.setFill()
        NSBezierPath(rect: NSRect(x: 0, y: 0, width: 2, height: 2)).fill()
        image.unlockFocus()

        let tiff = try XCTUnwrap(image.tiffRepresentation)
        let bitmap = try XCTUnwrap(NSBitmapImageRep(data: tiff))
        let pngData = try XCTUnwrap(bitmap.representation(using: .png, properties: [:]))
        let provider = NSItemProvider(item: pngData as NSSecureCoding, typeIdentifier: UTType.png.identifier)

        appState.handlePasteProviders([provider])

        for _ in 0..<20 {
            if !appState.captureWindow.attachments.isEmpty {
                break
            }
            try? await Task.sleep(for: .milliseconds(25))
        }

        XCTAssertEqual(appState.lastStatus, "Screenshot added")
        XCTAssertEqual(appState.captureWindow.attachments.count, 1)
        XCTAssertEqual(appState.captureWindow.attachments.first?.kind, .image)
        XCTAssertEqual(appState.captureWindow.attachments.first?.fileURL.pathExtension, "png")
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

    func testRemovingAttachmentLeavesRemainingItems() {
        let model = CaptureWindowViewModel()
        let screenshot = URL(fileURLWithPath: "/tmp/screenshot.png")
        let invoice = URL(fileURLWithPath: "/tmp/invoice.pdf")

        model.setSelectedFiles([screenshot, invoice])
        let screenshotID = try! XCTUnwrap(model.attachments.first(where: { $0.fileURL == screenshot })?.id)

        model.removeAttachment(id: screenshotID)

        XCTAssertEqual(model.attachments.map(\.fileURL), [invoice])
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
        XCTAssertEqual(model.lastCapturedItemURL?.path, "/Mehr/Personal/motorbike/bmw-c400gt.md")
    }

    func testApplyErrorShowsFailureMessage() {
        let model = CaptureWindowViewModel()

        model.applyError(
            NSError(domain: "NanobotCaptureTests", code: 1, userInfo: [NSLocalizedDescriptionKey: "network issue"])
        )

        XCTAssertEqual(model.resultMessage, "Capture failed: network issue")
    }
}
