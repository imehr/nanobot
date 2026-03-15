import AppKit
import Foundation
import UniformTypeIdentifiers

struct ExtractedExtensionPayload {
    let contentText: String?
    let fileURL: URL?
}

enum ExtensionPayloadExtractorError: Error {
    case unsupportedPayload
    case failedToLoadPayload
}

@MainActor
final class ExtensionPayloadExtractor {
    private let preferredTextTypes: [UTType] = [
        .rtfd,
        .flatRTFD,
        .rtf,
        .html,
        .plainText,
        .utf8PlainText,
        .text,
    ]

    func extract(from items: [NSExtensionItem]) async throws -> ExtractedExtensionPayload {
        let providers = items.flatMap { $0.attachments ?? [] }
        return try await extract(from: providers)
    }

    func extract(from providers: [NSItemProvider]) async throws -> ExtractedExtensionPayload {
        for provider in providers {
            if provider.hasItemConformingToTypeIdentifier(UTType.fileURL.identifier) {
                let url = try await loadURL(from: provider, typeIdentifier: UTType.fileURL.identifier)
                return ExtractedExtensionPayload(contentText: nil, fileURL: try copyToTemporaryLocation(url))
            }

            if provider.hasItemConformingToTypeIdentifier(UTType.url.identifier) {
                let url = try await loadURL(from: provider, typeIdentifier: UTType.url.identifier)
                return ExtractedExtensionPayload(contentText: url.absoluteString, fileURL: nil)
            }

            for textType in preferredTextTypes where provider.hasItemConformingToTypeIdentifier(textType.identifier) {
                let text = try await loadText(from: provider, typeIdentifier: textType.identifier)
                return ExtractedExtensionPayload(contentText: text, fileURL: nil)
            }

            if provider.hasItemConformingToTypeIdentifier(UTType.image.identifier) {
                let data = try await loadImageData(from: provider, typeIdentifier: UTType.image.identifier)
                return ExtractedExtensionPayload(contentText: nil, fileURL: try writeTemporaryFile(data: data, ext: "png"))
            }
        }

        throw ExtensionPayloadExtractorError.unsupportedPayload
    }

    private func loadURL(from provider: NSItemProvider, typeIdentifier: String) async throws -> URL {
        try await withCheckedThrowingContinuation { continuation in
            provider.loadItem(forTypeIdentifier: typeIdentifier, options: nil) { item, error in
                if let error {
                    continuation.resume(throwing: error)
                    return
                }
                if let url = item as? URL {
                    continuation.resume(returning: url)
                    return
                }
                if let data = item as? Data,
                   let url = NSURL(absoluteURLWithDataRepresentation: data, relativeTo: nil) as URL? {
                    continuation.resume(returning: url)
                    return
                }
                continuation.resume(throwing: ExtensionPayloadExtractorError.failedToLoadPayload)
            }
        }
    }

    private func loadText(from provider: NSItemProvider, typeIdentifier: String) async throws -> String {
        try await withCheckedThrowingContinuation { continuation in
            provider.loadItem(forTypeIdentifier: typeIdentifier, options: nil) { item, error in
                if let error {
                    continuation.resume(throwing: error)
                    return
                }
                if let text = item as? String {
                    if let normalizedText = Self.normalizeText(text, typeIdentifier: typeIdentifier) {
                        continuation.resume(returning: normalizedText)
                    } else {
                        continuation.resume(returning: text)
                    }
                    return
                }
                if let text = item as? NSString {
                    let stringValue = text as String
                    if let normalizedText = Self.normalizeText(stringValue, typeIdentifier: typeIdentifier) {
                        continuation.resume(returning: normalizedText)
                    } else {
                        continuation.resume(returning: stringValue)
                    }
                    return
                }
                if let attributedText = item as? NSAttributedString {
                    continuation.resume(returning: attributedText.string)
                    return
                }
                if let data = item as? Data, let text = Self.decodeText(data: data, typeIdentifier: typeIdentifier) {
                    continuation.resume(returning: text)
                    return
                }
                if let url = item as? URL,
                   let data = try? Data(contentsOf: url),
                   let text = Self.decodeText(data: data, typeIdentifier: typeIdentifier) {
                    continuation.resume(returning: text)
                    return
                }
                continuation.resume(throwing: ExtensionPayloadExtractorError.failedToLoadPayload)
            }
        }
    }

    private func loadImageData(from provider: NSItemProvider, typeIdentifier: String) async throws -> Data {
        try await withCheckedThrowingContinuation { continuation in
            provider.loadItem(forTypeIdentifier: typeIdentifier, options: nil) { item, error in
                if let error {
                    continuation.resume(throwing: error)
                    return
                }
                if let data = item as? Data {
                    continuation.resume(returning: data)
                    return
                }
                if let url = item as? URL, let data = try? Data(contentsOf: url) {
                    continuation.resume(returning: data)
                    return
                }
                if let image = item as? NSImage,
                   let tiff = image.tiffRepresentation,
                   let bitmap = NSBitmapImageRep(data: tiff),
                   let png = bitmap.representation(using: .png, properties: [:]) {
                    continuation.resume(returning: png)
                    return
                }
                continuation.resume(throwing: ExtensionPayloadExtractorError.failedToLoadPayload)
            }
        }
    }

    private func copyToTemporaryLocation(_ url: URL) throws -> URL {
        let tempDirectory = FileManager.default.temporaryDirectory
            .appendingPathComponent("NanobotCaptureShare", isDirectory: true)
        try FileManager.default.createDirectory(at: tempDirectory, withIntermediateDirectories: true)
        let tempURL = tempDirectory.appendingPathComponent(url.lastPathComponent)
        if FileManager.default.fileExists(atPath: tempURL.path) {
            try FileManager.default.removeItem(at: tempURL)
        }
        try FileManager.default.copyItem(at: url, to: tempURL)
        return tempURL
    }

    private func writeTemporaryFile(data: Data, ext: String) throws -> URL {
        let tempURL = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
            .appendingPathExtension(ext)
        try data.write(to: tempURL)
        return tempURL
    }

    nonisolated private static func normalizeText(_ text: String, typeIdentifier: String) -> String? {
        guard let data = text.data(using: .utf8) else {
            return nil
        }
        return decodeRichText(data: data, typeIdentifier: typeIdentifier)
    }

    nonisolated private static func decodeText(data: Data, typeIdentifier: String) -> String? {
        if let attributedText = decodeRichText(data: data, typeIdentifier: typeIdentifier) {
            return attributedText
        }

        return String(data: data, encoding: .utf8)
            ?? String(data: data, encoding: .utf16)
            ?? String(data: data, encoding: .unicode)
    }

    nonisolated private static func decodeRichText(data: Data, typeIdentifier: String) -> String? {
        let documentType: NSAttributedString.DocumentType?
        switch typeIdentifier {
        case UTType.rtfd.identifier, UTType.flatRTFD.identifier:
            documentType = .rtfd
        case UTType.rtf.identifier:
            documentType = .rtf
        case UTType.html.identifier:
            documentType = .html
        default:
            documentType = nil
        }

        guard let documentType else {
            return nil
        }

        let attributedText = try? NSAttributedString(
            data: data,
            options: [.documentType: documentType],
            documentAttributes: nil
        )
        return attributedText?.string.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
