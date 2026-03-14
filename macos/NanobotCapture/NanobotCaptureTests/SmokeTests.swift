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
            primaryPath: "/Mehr/Projects/nanobot/decisions.md",
            canonicalPaths: ["/Mehr/Work/projects/nanobot/index.md"],
            archivePaths: [],
            projectMemoryPaths: ["/Mehr/Projects/nanobot/decisions.md"],
            followUp: nil,
            error: nil,
            queuedAt: "2026-03-14T10:00:00"
        )

        XCTAssertEqual(
            AppState.describe(status: status),
            "Saved to Project Memory: /Mehr/Projects/nanobot/decisions.md"
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

    func testProjectMemoryStatusIsRecognized() {
        let status = CaptureStatusResponse(
            captureId: "cap-1",
            status: "completed",
            sourceChannel: "telegram",
            captureType: "text",
            inboxItemPath: "/tmp/item",
            primaryPath: "/Mehr/Projects/nanobot/decisions.md",
            canonicalPaths: [],
            archivePaths: [],
            projectMemoryPaths: ["/Mehr/Projects/nanobot/decisions.md"],
            followUp: nil,
            error: nil,
            queuedAt: nil
        )

        XCTAssertTrue(AppState.isProjectMemoryCapture(status))
    }
}
