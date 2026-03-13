import AppKit
import Foundation

@MainActor
final class CaptureWindowViewModel: ObservableObject {
    @Published var note: String = ""
    @Published var hint: String = ""
    @Published var selectedFiles: [URL] = []
    @Published var resultMessage: String = ""
    @Published var isSubmitting: Bool = false

    var canSubmit: Bool {
        guard !isSubmitting else {
            return false
        }
        return !trimmedNote.isEmpty || !selectedFiles.isEmpty
    }

    func setSelectedFiles(_ urls: [URL]) {
        var deduplicated: [URL] = []
        for url in urls where !deduplicated.contains(url) {
            deduplicated.append(url)
        }
        selectedFiles = deduplicated
    }

    func addSelectedFiles(_ urls: [URL]) {
        setSelectedFiles(selectedFiles + urls)
    }

    func clearFiles() {
        selectedFiles = []
    }

    func applyResult(_ response: CaptureResponse) {
        var lines = ["Saved to \(response.inboxItemPath)"]
        if !response.entities.isEmpty {
            lines.append("Entities: \(response.entities.joined(separator: ", "))")
        }
        if !response.actions.isEmpty {
            lines.append("Actions: \(response.actions.joined(separator: ", "))")
        }
        if let followUp = response.followUp, !followUp.isEmpty {
            lines.append("Follow-up: \(followUp)")
        }
        resultMessage = lines.joined(separator: "\n")
    }

    func submit(using client: NativeCaptureClient) async {
        guard canSubmit else {
            return
        }

        isSubmitting = true
        defer { isSubmitting = false }

        do {
            if selectedFiles.isEmpty {
                let response = try await client.submit(
                    .text(contentText: trimmedNote, userHint: normalizedHint)
                )
                applyResult(response)
                return
            }

            var lastResponse: CaptureResponse?
            for fileURL in selectedFiles {
                lastResponse = try await client.submit(
                    .file(
                        fileURL: fileURL,
                        contentText: trimmedNote.isEmpty ? nil : trimmedNote,
                        userHint: normalizedHint
                    )
                )
            }

            if let lastResponse {
                applyResult(lastResponse)
                if selectedFiles.count > 1 {
                    resultMessage = "Captured \(selectedFiles.count) files\n\(resultMessage)"
                }
            }
        } catch {
            resultMessage = "Capture failed: \(error.localizedDescription)"
        }
    }

    private var trimmedNote: String {
        note.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private var normalizedHint: String? {
        let trimmed = hint.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }
}

@MainActor
final class AppState: ObservableObject {
    @Published var lastStatus: String = "Ready"
    @Published var isCaptureWindowVisible: Bool = true
    @Published var captureWindow = CaptureWindowViewModel()
    let client: NativeCaptureClient

    init(client: NativeCaptureClient? = nil) {
        self.client = client ?? AppState.buildDefaultClient()
    }

    func chooseFiles() {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = true
        panel.canChooseDirectories = false
        panel.canChooseFiles = true
        panel.prompt = "Attach"
        if panel.runModal() == .OK {
            captureWindow.addSelectedFiles(panel.urls)
        }
    }

    func captureClipboard() {
        let pasteboard = NSPasteboard.general
        if let text = pasteboard.string(forType: .string), !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            captureWindow.note = text
            lastStatus = "Loaded clipboard text"
        } else {
            lastStatus = "Clipboard is empty"
        }
    }

    func submitCapture() async {
        await captureWindow.submit(using: client)
        lastStatus = captureWindow.resultMessage.isEmpty ? "Ready" : captureWindow.resultMessage
    }

    private static func buildDefaultClient() -> NativeCaptureClient {
        let env = ProcessInfo.processInfo.environment
        let baseURL = URL(string: env["NANOBOT_NATIVE_CAPTURE_BASE_URL"] ?? "http://127.0.0.1:18792")!
        let client = NativeCaptureClient(baseURL: baseURL)
        if let token = env["NANOBOT_NATIVE_CAPTURE_TOKEN"], !token.isEmpty {
            try? client.storeToken(token)
        }
        return client
    }
}
