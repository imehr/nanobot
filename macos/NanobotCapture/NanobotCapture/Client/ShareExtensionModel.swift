import Foundation

enum ShareResultState: Equatable {
    case idle
    case success
    case failure
}

@MainActor
final class ShareExtensionModel: ObservableObject {
    @Published var note: String = ""
    @Published var hint: String = ""
    @Published var attachmentSummary: String = "Preparing shared content..."
    @Published var resultMessage: String = ""
    @Published var isSubmitting: Bool = false
    @Published var resultState: ShareResultState = .idle

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
        if resultState == .success {
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
            resultState = .failure
        }
    }

    func submit() async -> Bool {
        guard canSubmit else {
            return false
        }

        isSubmitting = true
        resultState = .idle
        defer { isSubmitting = false }

        do {
            let hintText = hint.trimmingCharacters(in: .whitespacesAndNewlines)
            let queued: CaptureResponse
            if let fileURL = extractedPayload?.fileURL {
                queued = try await client.submit(
                    .file(
                        fileURL: fileURL,
                        contentText: note.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? nil : note,
                        userHint: hintText.isEmpty ? nil : hintText
                    )
                )
            } else {
                queued = try await client.submit(
                    .text(
                        contentText: note.trimmingCharacters(in: .whitespacesAndNewlines),
                        userHint: hintText.isEmpty ? nil : hintText
                    )
                )
            }

            resultMessage = "Queued \(queued.captureId)"
            let finalStatus = try await pollForTerminalStatus(queued.captureId)
            resultMessage = describe(status: finalStatus)
            resultState = finalStatus.status == "failed" ? .failure : .success
            return finalStatus.status != "failed"
        } catch {
            resultState = .failure
            resultMessage = "Capture failed: \(error.localizedDescription)"
            return false
        }
    }

    func describe(status: CaptureStatusResponse) -> String {
        switch status.status {
        case "completed":
            return "Saved to Mehr: \(status.primaryPath)"
        case "needs_input":
            return status.followUp ?? "Capture needs more input"
        case "failed":
            return "Capture failed: \(status.error ?? "Unknown error")"
        case "retracted":
            return "Capture retracted"
        default:
            return "Queued \(status.captureId)"
        }
    }

    func setExtractedPayloadForTesting(_ payload: ExtractedExtensionPayload) {
        extractedPayload = payload
    }

    private func pollForTerminalStatus(_ captureID: String) async throws -> CaptureStatusResponse {
        for _ in 0..<40 {
            let status = try await client.fetchCapture(captureID)
            if ["completed", "failed", "needs_input", "retracted"].contains(status.status) {
                return status
            }
            try await Task.sleep(for: .milliseconds(350))
        }
        return try await client.fetchCapture(captureID)
    }
}
