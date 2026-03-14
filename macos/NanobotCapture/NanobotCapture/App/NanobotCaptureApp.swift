import SwiftUI

@main
struct NanobotCaptureApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        Window("Nanobot Capture", id: "capture-window") {
            ContentView()
                .environmentObject(appState)
                .frame(minWidth: 980, minHeight: 760)
        }
        .defaultSize(width: 1180, height: 820)

        MenuBarExtra("Nanobot", systemImage: "tray.and.arrow.down.fill") {
            MenuBarCaptureView()
                .environmentObject(appState)
        }
        .menuBarExtraStyle(.window)
    }
}
