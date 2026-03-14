import XCTest
@testable import NanobotCapture

@MainActor
final class SmokeTests: XCTestCase {
    func testAppStateStartsReady() {
        XCTAssertEqual(AppState().lastStatus, "Ready")
    }

    func testDescribeCompletedStatusUsesPrimaryPath() {
        let status = CaptureStatusResponse(
            captureId: "cap-1",
            status: "completed",
            sourceChannel: "telegram",
            captureType: "text",
            inboxItemPath: "/tmp/item",
            primaryPath: "/Mehr/Personal/motorbike/bmw-c400gt.md",
            canonicalPaths: ["/Mehr/Personal/motorbike/bmw-c400gt.md"],
            archivePaths: [],
            followUp: nil,
            error: nil,
            queuedAt: "2026-03-14T10:00:00"
        )

        XCTAssertEqual(
            AppState.describe(status: status),
            "Saved to Mehr: /Mehr/Personal/motorbike/bmw-c400gt.md"
        )
    }

    func testCaptureWindowUsesPinnedBottomActionBarLayout() {
        XCTAssertEqual(CaptureWindowLayout.actionBarMode, .fixedBottom)
        XCTAssertTrue(CaptureWindowLayout.usesPersistentHeader)
        XCTAssertTrue(CaptureWindowLayout.usesPersistentFooter)
        XCTAssertGreaterThanOrEqual(CaptureWindowLayout.editorMinHeight, 160)
        XCTAssertGreaterThan(CaptureWindowLayout.wideContentBreakpoint, 900)
        XCTAssertEqual(CaptureWindowLayout.mode(for: 1280), .wide)
        XCTAssertEqual(CaptureWindowLayout.mode(for: 820), .compact)
    }
}
