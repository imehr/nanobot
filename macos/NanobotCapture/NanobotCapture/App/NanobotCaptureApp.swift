import SwiftUI

@main
struct NanobotCaptureApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup("Nanobot Capture") {
            ContentView()
                .environmentObject(appState)
                .frame(minWidth: 560, minHeight: 420)
        }
    }
}
