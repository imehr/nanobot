import XCTest
@testable import NanobotCapture

@MainActor
final class SmokeTests: XCTestCase {
    func testAppStateStartsReady() {
        XCTAssertEqual(AppState().lastStatus, "Ready")
    }
}
