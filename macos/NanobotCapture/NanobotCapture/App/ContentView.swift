import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Nanobot Capture")
                .font(.largeTitle.bold())
            Text("Native menu bar app, window, and Share extension scaffolding.")
                .foregroundStyle(.secondary)
            Text(appState.lastStatus)
                .font(.headline)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .padding(24)
    }
}
