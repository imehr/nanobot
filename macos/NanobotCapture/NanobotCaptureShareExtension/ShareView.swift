import SwiftUI

import AppKit
import SwiftUI

@MainActor
final class ShareExtensionModel: ObservableObject {
    @Published var note: String = ""
    @Published var hint: String = ""
    @Published var attachmentSummary: String = "Preparing shared content..."
    @Published var resultMessage: String = ""
    @Published var isSubmitting: Bool = false

    private let extractor = ExtensionPayloadExtractor()
    private let client: NativeCaptureClient
    private var extractedPayload: ExtractedExtensionPayload?

    init(client: NativeCaptureClient? = nil) {
        let env = ProcessInfo.processInfo.environment
        let baseURL = URL(string: env["NANOBOT_NATIVE_CAPTURE_BASE_URL"] ?? "http://127.0.0.1:18792")!
        let resolvedClient = client ?? NativeCaptureClient(baseURL: baseURL)
        if let token = env["NANOBOT_NATIVE_CAPTURE_TOKEN"], !token.isEmpty {
            try? resolvedClient.storeToken(token)
        }
        self.client = resolvedClient
    }

    var canSubmit: Bool {
        guard !isSubmitting else {
            return false
        }
        if extractedPayload?.fileURL != nil {
            return true
        }
        return !(note.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && extractedPayload?.contentText == nil)
    }

    func load(items: [NSExtensionItem]) async {
        do {
            let payload = try await extractor.extract(from: items)
            extractedPayload = payload
            if let contentText = payload.contentText {
                note = contentText
                attachmentSummary = "Prepared shared text"
            } else if let fileURL = payload.fileURL {
                attachmentSummary = "Prepared \(fileURL.lastPathComponent)"
            }
        } catch {
            attachmentSummary = "Unsupported shared content"
        }
    }

    func submit() async -> Bool {
        guard canSubmit else {
            return false
        }

        isSubmitting = true
        defer { isSubmitting = false }

        do {
            let hintText = hint.trimmingCharacters(in: .whitespacesAndNewlines)
            let response: CaptureResponse
            if let fileURL = extractedPayload?.fileURL {
                response = try await client.submit(
                    .file(
                        fileURL: fileURL,
                        contentText: note.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? nil : note,
                        userHint: hintText.isEmpty ? nil : hintText
                    )
                )
            } else {
                response = try await client.submit(
                    .text(
                        contentText: note.trimmingCharacters(in: .whitespacesAndNewlines),
                        userHint: hintText.isEmpty ? nil : hintText
                    )
                )
            }
            resultMessage = "Captured to \(response.inboxItemPath)"
            return true
        } catch {
            resultMessage = "Capture failed: \(error.localizedDescription)"
            return false
        }
    }
}

struct ShareView: View {
    @ObservedObject var model: ShareExtensionModel
    let onCancel: () -> Void
    let onDone: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Send to Nanobot")
                .font(.title2.bold())

            Text(model.attachmentSummary)
                .foregroundStyle(.secondary)

            TextField("Context", text: $model.note, axis: .vertical)
                .textFieldStyle(.roundedBorder)
            TextField("Hint", text: $model.hint)
                .textFieldStyle(.roundedBorder)

            if !model.resultMessage.isEmpty {
                Text(model.resultMessage)
                    .foregroundStyle(.secondary)
            }

            HStack {
                Button("Cancel") {
                    onCancel()
                }
                Spacer()
                Button(model.isSubmitting ? "Sending..." : "Send to Nanobot") {
                    Task {
                        if await model.submit() {
                            onDone()
                        }
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(!model.canSubmit)
            }
        }
        .padding(20)
        .frame(minWidth: 360, minHeight: 220, alignment: .topLeading)
    }
}
