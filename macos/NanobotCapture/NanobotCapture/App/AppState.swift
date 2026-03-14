import AppKit
import Foundation

@MainActor
final class MenuBarCaptureViewModel: ObservableObject {
    @Published var note: String = ""
    @Published var hint: String = ""
    @Published var resultMessage: String = ""
    @Published var isSubmitting: Bool = false

    var canSubmit: Bool {
        !isSubmitting && !note.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    @discardableResult
    func loadClipboardText(_ text: String?) -> Bool {
        guard let text, !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            return false
        }
        note = text
        return true
    }

    func payload() -> CapturePayload? {
        let trimmed = note.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            return nil
        }
        let hintValue = hint.trimmingCharacters(in: .whitespacesAndNewlines)
        return .text(contentText: trimmed, userHint: hintValue.isEmpty ? nil : hintValue)
    }

    func applyQueued(_ response: CaptureResponse) {
        resultMessage = "Queued \(response.captureId)"
    }

    func applyStatus(_ response: CaptureStatusResponse) {
        resultMessage = AppState.describe(status: response)
    }
}

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

    func payloads() -> [CapturePayload] {
        let normalizedHint = normalizedHint
        if selectedFiles.isEmpty {
            guard !trimmedNote.isEmpty else {
                return []
            }
            return [.text(contentText: trimmedNote, userHint: normalizedHint)]
        }
        return selectedFiles.map { fileURL in
            .file(
                fileURL: fileURL,
                contentText: trimmedNote.isEmpty ? nil : trimmedNote,
                userHint: normalizedHint
            )
        }
    }

    func applyQueued(_ responses: [CaptureResponse]) {
        let ids = responses.map(\.captureId).joined(separator: ", ")
        resultMessage = "Queued \(responses.count) capture(s): \(ids)"
    }

    func applyStatus(_ response: CaptureStatusResponse) {
        resultMessage = AppState.describe(status: response)
    }

    func applyError(_ error: Error) {
        resultMessage = "Capture failed: \(error.localizedDescription)"
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
    @Published var menuBarCapture = MenuBarCaptureViewModel()
    @Published var recentCaptures: [CaptureStatusResponse] = []

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

    func refreshRecentCaptures() async {
        do {
            recentCaptures = try await client.fetchRecentCaptures()
        } catch {
            lastStatus = "Could not load recent captures"
        }
    }

    func submitCapture() async {
        let payloads = captureWindow.payloads()
        guard !payloads.isEmpty else {
            return
        }

        captureWindow.isSubmitting = true
        lastStatus = "Queuing capture..."
        defer { captureWindow.isSubmitting = false }

        do {
            var queuedResponses: [CaptureResponse] = []
            for payload in payloads {
                queuedResponses.append(try await client.submit(payload))
            }
            captureWindow.applyQueued(queuedResponses)
            lastStatus = "Processing capture..."

            let terminalStatuses = try await pollForTerminalStatuses(queuedResponses.map(\.captureId))
            if let latest = terminalStatuses.last {
                captureWindow.applyStatus(latest)
                lastStatus = Self.describe(status: latest)
            }
            await refreshRecentCaptures()
        } catch {
            captureWindow.applyError(error)
            lastStatus = captureWindow.resultMessage
        }
    }

    func loadClipboardIntoMenuBar() {
        let text = NSPasteboard.general.string(forType: .string)
        if menuBarCapture.loadClipboardText(text) {
            lastStatus = "Loaded clipboard text"
        } else {
            lastStatus = "Clipboard is empty"
        }
    }

    func submitMenuBarCapture() async {
        guard let payload = menuBarCapture.payload() else {
            return
        }

        menuBarCapture.isSubmitting = true
        lastStatus = "Queuing capture..."
        defer { menuBarCapture.isSubmitting = false }

        do {
            let queued = try await client.submit(payload)
            menuBarCapture.applyQueued(queued)
            let finalStatus = try await pollForTerminalStatus(queued.captureId)
            menuBarCapture.applyStatus(finalStatus)
            lastStatus = Self.describe(status: finalStatus)
            await refreshRecentCaptures()
        } catch {
            menuBarCapture.resultMessage = "Capture failed: \(error.localizedDescription)"
            lastStatus = menuBarCapture.resultMessage
        }
    }

    func openCaptureWindowFromMenuBar() {
        if !menuBarCapture.note.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            captureWindow.note = menuBarCapture.note
        }
        if !menuBarCapture.hint.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            captureWindow.hint = menuBarCapture.hint
        }
        NSApp.activate(ignoringOtherApps: true)
        if let window = NSApp.windows.first {
            window.makeKeyAndOrderFront(nil)
        }
    }

    func retractCapture(_ captureID: String) async {
        do {
            let status = try await client.retractCapture(captureID)
            lastStatus = Self.describe(status: status)
            await refreshRecentCaptures()
        } catch {
            lastStatus = "Could not retract capture"
        }
    }

    func retryCapture(_ captureID: String) async {
        do {
            _ = try await client.retryCapture(captureID)
            lastStatus = "Retry queued"
            await refreshRecentCaptures()
        } catch {
            lastStatus = "Could not retry capture"
        }
    }

    func reveal(_ path: String) {
        NSWorkspace.shared.activateFileViewerSelecting([URL(fileURLWithPath: path)])
    }

    private func pollForTerminalStatuses(_ captureIDs: [String]) async throws -> [CaptureStatusResponse] {
        var statuses: [CaptureStatusResponse] = []
        for captureID in captureIDs {
            statuses.append(try await pollForTerminalStatus(captureID))
        }
        return statuses
    }

    private func pollForTerminalStatus(_ captureID: String) async throws -> CaptureStatusResponse {
        for _ in 0..<40 {
            let status = try await client.fetchCapture(captureID)
            if Self.isTerminal(status.status) {
                return status
            }
            lastStatus = "Processing capture..."
            try await Task.sleep(for: .milliseconds(350))
        }
        return try await client.fetchCapture(captureID)
    }

    private static func isTerminal(_ status: String) -> Bool {
        ["completed", "failed", "needs_input", "retracted"].contains(status)
    }

    static func describe(status: CaptureStatusResponse) -> String {
        switch status.status {
        case "completed":
            return "Saved to Mehr: \(status.primaryPath)"
        case "needs_input":
            return status.followUp ?? "Capture needs more input"
        case "failed":
            return "Capture failed: \(status.error ?? "Unknown error")"
        case "retracted":
            return "Capture retracted"
        case "processing":
            return "Processing capture..."
        default:
            return "Queued \(status.captureId)"
        }
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
