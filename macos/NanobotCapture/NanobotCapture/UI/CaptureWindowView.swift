import SwiftUI
import UniformTypeIdentifiers

enum CaptureWindowMode: Equatable {
    case wide
    case compact
}

enum CaptureWindowActionBarMode: Equatable {
    case fixedBottom
}

enum CaptureWindowLayout {
    static let actionBarMode: CaptureWindowActionBarMode = .fixedBottom
    static let usesPersistentHeader = true
    static let usesPersistentFooter = true
    static let editorMinHeight: CGFloat = 220
    static let wideContentBreakpoint: CGFloat = 980

    static func mode(for width: CGFloat) -> CaptureWindowMode {
        width >= wideContentBreakpoint ? .wide : .compact
    }
}

struct CaptureWindowView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        let model = appState.captureWindow

        VStack(spacing: 0) {
            header
            Divider()

            GeometryReader { proxy in
                ScrollView {
                    VStack(alignment: .leading, spacing: 24) {
                        content(for: CaptureWindowLayout.mode(for: proxy.size.width))

                        if !model.resultMessage.isEmpty {
                            resultCard(model)
                        }

                        recentCaptures
                    }
                    .padding(24)
                    .frame(maxWidth: .infinity, alignment: .topLeading)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }

            Divider()
            footer(model: model)
        }
        .frame(minWidth: 980, minHeight: 760, alignment: .topLeading)
        .task {
            await appState.refreshRecentCaptures()
        }
        .onPasteCommand(of: [UTType.image, UTType.png, UTType.tiff, UTType.fileURL, UTType.url, UTType.plainText]) { providers in
            appState.handlePasteProviders(providers)
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Nanobot Capture")
                .font(.system(size: 34, weight: .bold))
            Text("Drop in a note, attach files, and send the raw material into the local-only nanobot capture pipeline.")
                .font(.title3)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 24)
        .padding(.top, 24)
        .padding(.bottom, 20)
        .background(.regularMaterial)
    }

    @ViewBuilder
    private func content(for mode: CaptureWindowMode) -> some View {
        switch mode {
        case .wide:
            HStack(alignment: .top, spacing: 24) {
                contextColumn
                    .frame(maxWidth: .infinity, alignment: .topLeading)
                attachmentsColumn
                    .frame(width: 360, alignment: .topLeading)
            }
        case .compact:
            VStack(alignment: .leading, spacing: 24) {
                contextColumn
                attachmentsColumn
            }
        }
    }

    private var contextColumn: some View {
        VStack(alignment: .leading, spacing: 20) {
            VStack(alignment: .leading, spacing: 10) {
                Text("Context")
                    .font(.title3.bold())
                CaptureContextEditor(text: $appState.captureWindow.note) { pasteboard in
                    appState.handleAttachmentPasteboard(pasteboard)
                }
                .frame(minHeight: CaptureWindowLayout.editorMinHeight)
                .padding(14)
                .background(Color(NSColor.controlBackgroundColor), in: RoundedRectangle(cornerRadius: 18, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 18, style: .continuous)
                        .stroke(Color.secondary.opacity(0.14), lineWidth: 1)
                )
            }

            VStack(alignment: .leading, spacing: 10) {
                Text("Hint")
                    .font(.headline)
                TextField("bike, house, expense, subscription", text: $appState.captureWindow.hint)
                    .textFieldStyle(.roundedBorder)
            }
        }
    }

    private var attachmentsColumn: some View {
        CaptureAttachmentPanel(
            attachments: appState.captureWindow.attachments,
            onDropFiles: { urls in
                appState.captureWindow.addSelectedFiles(urls)
            },
            onChooseFiles: {
                appState.chooseFiles()
            },
            onPasteClipboard: {
                appState.captureClipboard()
            },
            onClear: {
                appState.captureWindow.clearFiles()
            },
            onRemoveAttachment: { id in
                appState.captureWindow.removeAttachment(id: id)
            }
        )
    }

    private func resultCard(_ model: CaptureWindowViewModel) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Result")
                .font(.headline)
            Text(model.resultMessage)
                .frame(maxWidth: .infinity, alignment: .leading)
                .textSelection(.enabled)
            if let resultURL = model.lastCapturedItemURL {
                Link(destination: resultURL) {
                    Text(resultURL.path)
                        .font(.system(.callout, design: .monospaced))
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                Button("Reveal in Finder") {
                    appState.revealCaptureWindowResultInFinder()
                }
            }
        }
        .padding(18)
        .background(Color(NSColor.controlBackgroundColor), in: RoundedRectangle(cornerRadius: 18, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .stroke(Color.secondary.opacity(0.14), lineWidth: 1)
        )
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
                                if AppState.isProjectMemoryCapture(capture) {
                                    Text("Project Memory")
                                        .font(.caption2.weight(.semibold))
                                        .padding(.horizontal, 8)
                                        .padding(.vertical, 3)
                                        .background(Color.accentColor.opacity(0.12), in: Capsule())
                                }
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
                                } else if !capture.inboxItemPath.isEmpty {
                                    Button("Reveal") {
                                        appState.reveal(capture.inboxItemPath)
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
                        .background(Color(NSColor.controlBackgroundColor), in: RoundedRectangle(cornerRadius: 16, style: .continuous))
                        .overlay(
                            RoundedRectangle(cornerRadius: 16, style: .continuous)
                                .stroke(Color.secondary.opacity(0.14), lineWidth: 1)
                        )
                    }
                }
            }
        }
    }

    private func footer(model: CaptureWindowViewModel) -> some View {
        HStack(spacing: 12) {
            if model.isSubmitting {
                ProgressView()
                    .controlSize(.small)
            }
            Text(appState.lastStatus)
                .foregroundStyle(.secondary)
                .lineLimit(3)
            Spacer()
            Button(model.isSubmitting ? "Capturing..." : "Capture to Nanobot") {
                Task {
                    await appState.submitCapture()
                }
            }
            .buttonStyle(.borderedProminent)
            .disabled(!model.canSubmit)
        }
        .padding(.horizontal, 24)
        .padding(.vertical, 16)
        .background(.regularMaterial)
    }
}
