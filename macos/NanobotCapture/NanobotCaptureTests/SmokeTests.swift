import XCTest
@testable import NanobotCapture

final class SmokeTests: XCTestCase {
    func testAppStateStartsReady() {
        XCTAssertEqual(AppState().lastStatus, "Ready")
    }
}
