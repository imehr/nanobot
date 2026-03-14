import SwiftUI

struct CaptureWindowView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        let model = appState.captureWindow

        VStack(spacing: 0) {
            header

            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    composer

                    if !model.resultMessage.isEmpty {
                        resultCard(model.resultMessage)
                    }

                    recentCaptures
                }
                .padding(24)
            }

            footer(model)
        }
        .frame(minWidth: 920, minHeight: 720, alignment: .topLeading)
        .task {
            await appState.refreshRecentCaptures()
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Nanobot Capture")
                .font(.largeTitle.bold())
            Text("Drop in a note, attach files, and send the raw material into the local-only nanobot capture pipeline.")
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(24)
        .background(.regularMaterial)
    }

    private var composer: some View {
        HStack(alignment: .top, spacing: 24) {
            VStack(alignment: .leading, spacing: 16) {
                Text("Context")
                    .font(.headline)
                TextEditor(text: $appState.captureWindow.note)
                    .font(.body)
                    .frame(minHeight: 260)
                    .padding(10)
                    .background(.background.secondary, in: RoundedRectangle(cornerRadius: 14, style: .continuous))

                Text("Hint")
                    .font(.headline)
                TextField("bike, house, expense, subscription", text: $appState.captureWindow.hint)
                    .textFieldStyle(.roundedBorder)
            }
            .frame(maxWidth: .infinity, alignment: .topLeading)

            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Text("Attachments")
                        .font(.headline)
                    Spacer()
                    Text("\(appState.captureWindow.selectedFiles.count) item\(appState.captureWindow.selectedFiles.count == 1 ? "" : "s")")
                        .foregroundStyle(.secondary)
                }

                Text("Paste screenshots, drag files, or attach receipts and PDFs.")
                    .foregroundStyle(.secondary)

                FileDropZone(files: appState.captureWindow.selectedFiles) { urls in
                    appState.captureWindow.addSelectedFiles(urls)
                }

                HStack {
                    Button("Choose Files") {
                        appState.chooseFiles()
                    }
                    Button("Paste Clipboard") {
                        appState.captureClipboard()
                    }
                    Button("Clear") {
                        appState.captureWindow.clearFiles()
                    }
                    .disabled(appState.captureWindow.selectedFiles.isEmpty)
                }

                if !appState.captureWindow.selectedFiles.isEmpty {
                    VStack(alignment: .leading, spacing: 10) {
                        ForEach(appState.captureWindow.selectedFiles, id: \.path) { url in
                            VStack(alignment: .leading, spacing: 4) {
                                Text(url.lastPathComponent)
                                    .font(.body.bold())
                                Text("Attachment")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(12)
                            .background(.background.secondary, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
                        }
                    }
                }
            }
            .frame(width: 320, alignment: .topLeading)
        }
    }

    private func resultCard(_ message: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Result")
                .font(.headline)
            Text(message)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(16)
        .background(.background.secondary, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
    }

    private var recentCaptures: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Text("Recent Captures")
                    .font(.headline)
                Spacer()
                Button("Refresh") {
                    Task {
                        await appState.refreshRecentCaptures()
                    }
                }
            }

            if appState.recentCaptures.isEmpty {
                Text("No recent captures yet.")
                    .foregroundStyle(.secondary)
            } else {
                VStack(spacing: 12) {
                    ForEach(appState.recentCaptures) { capture in
                        VStack(alignment: .leading, spacing: 8) {
                            HStack(alignment: .firstTextBaseline) {
                                Text(capture.captureId)
                                    .font(.caption.monospaced())
                                    .foregroundStyle(.secondary)
                                Spacer()
                                Text(capture.status.replacingOccurrences(of: "_", with: " "))
                                    .font(.caption.bold())
                            }

                            Text(capture.primaryPath.isEmpty ? capture.inboxItemPath : capture.primaryPath)
                                .font(.callout)
                                .textSelection(.enabled)

                            Text("Source: \(capture.sourceChannel)")
                                .font(.caption)
                                .foregroundStyle(.secondary)

                            HStack {
                                if !capture.primaryPath.isEmpty {
                                    Button("Reveal") {
                                        appState.reveal(capture.primaryPath)
                                    }
                                }
                                if capture.status == "failed" {
                                    Button("Retry") {
                                        Task { await appState.retryCapture(capture.captureId) }
                                    }
                                }
                                if ["completed", "needs_input", "failed"].contains(capture.status) {
                                    Button("Retract") {
                                        Task { await appState.retractCapture(capture.captureId) }
                                    }
                                }
                                Spacer()
                            }
                        }
                        .padding(14)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(.background.secondary, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
                    }
                }
            }
        }
    }

    private func footer(_ model: CaptureWindowViewModel) -> some View {
        HStack {
            HStack(spacing: 10) {
                if model.isSubmitting {
                    ProgressView()
                        .controlSize(.small)
                }
                Text(appState.lastStatus)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }
            Spacer()
            Button(model.isSubmitting ? "Capturing..." : "Capture to Nanobot") {
                Task {
                    await appState.submitCapture()
                }
            }
            .buttonStyle(.borderedProminent)
            .disabled(!model.canSubmit)
        }
        .padding(24)
        .background(.regularMaterial)
    }
}
