import SwiftUI

struct CaptureWindowView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        let model = appState.captureWindow

        VStack(alignment: .leading, spacing: 20) {
            VStack(alignment: .leading, spacing: 8) {
                Text("Nanobot Capture")
                    .font(.largeTitle.bold())
                Text("Drop in a note, attach files, and send the raw material into the local-only nanobot capture pipeline.")
                    .foregroundStyle(.secondary)
            }

            VStack(alignment: .leading, spacing: 10) {
                Text("Context")
                    .font(.headline)
                TextEditor(text: $appState.captureWindow.note)
                    .font(.body)
                    .frame(minHeight: 150)
                    .padding(10)
                    .background(.background.secondary, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
            }

            VStack(alignment: .leading, spacing: 10) {
                Text("Hint")
                    .font(.headline)
                TextField("bike, house, expense, subscription", text: $appState.captureWindow.hint)
                    .textFieldStyle(.roundedBorder)
            }

            VStack(alignment: .leading, spacing: 12) {
                Text("Attachments")
                    .font(.headline)
                FileDropZone(files: model.selectedFiles) { urls in
                    appState.captureWindow.addSelectedFiles(urls)
                }

                HStack {
                    Button("Choose Files") {
                        appState.chooseFiles()
                    }
                    Button("Clear") {
                        appState.captureWindow.clearFiles()
                    }
                    .disabled(model.selectedFiles.isEmpty)
                    Spacer()
                    Text("\(model.selectedFiles.count) selected")
                        .foregroundStyle(.secondary)
                }

                if !model.selectedFiles.isEmpty {
                    VStack(alignment: .leading, spacing: 6) {
                        ForEach(model.selectedFiles, id: \.path) { url in
                            Text(url.lastPathComponent)
                                .font(.callout)
                        }
                    }
                    .padding(12)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(.background.secondary, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
                }
            }

            HStack {
                Text(appState.lastStatus)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
                Spacer()
                Button(model.isSubmitting ? "Capturing..." : "Capture to Nanobot") {
                    Task {
                        await appState.submitCapture()
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(!model.canSubmit)
            }

            if !model.resultMessage.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Result")
                        .font(.headline)
                    Text(model.resultMessage)
                        .font(.body)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .padding(16)
                .background(.background.secondary, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
            }
        }
        .padding(24)
        .frame(minWidth: 620, minHeight: 640, alignment: .topLeading)
    }
}
