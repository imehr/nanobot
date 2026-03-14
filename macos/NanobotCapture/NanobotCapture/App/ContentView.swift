import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        CaptureWindowView()
            .environmentObject(appState)
            .onAppear {
                appState.closeExtraCaptureWindows()
            }
    }
}
