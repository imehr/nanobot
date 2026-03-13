import SwiftUI

struct MenuBarCaptureView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Quick Capture")
                .font(.title3.bold())

            TextField("Paste or type a note", text: $appState.menuBarCapture.note, axis: .vertical)
                .textFieldStyle(.roundedBorder)

            TextField("Hint", text: $appState.menuBarCapture.hint)
                .textFieldStyle(.roundedBorder)

            HStack {
                Button("Clipboard") {
                    appState.loadClipboardIntoMenuBar()
                }
                Button("Open Window") {
                    appState.openCaptureWindowFromMenuBar()
                }
                Spacer()
            }

            Button(appState.menuBarCapture.isSubmitting ? "Capturing..." : "Capture") {
                Task {
                    await appState.submitMenuBarCapture()
                }
            }
            .buttonStyle(.borderedProminent)
            .disabled(!appState.menuBarCapture.canSubmit)

            if !appState.menuBarCapture.resultMessage.isEmpty {
                Text(appState.menuBarCapture.resultMessage)
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(16)
        .frame(width: 320)
    }
}
