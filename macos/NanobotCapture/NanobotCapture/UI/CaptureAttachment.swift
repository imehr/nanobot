import Foundation
import UniformTypeIdentifiers

enum CaptureAttachmentKind: Equatable {
    case image
    case file

    static func infer(from fileURL: URL) -> CaptureAttachmentKind {
        guard
            let type = UTType(filenameExtension: fileURL.pathExtension),
            type.conforms(to: .image)
        else {
            return .file
        }
        return .image
    }
}

struct CaptureAttachment: Identifiable, Equatable {
    let id: UUID
    let fileURL: URL
    let displayName: String
    let kind: CaptureAttachmentKind

    init(fileURL: URL, id: UUID = UUID()) {
        self.id = id
        self.fileURL = fileURL
        self.displayName = fileURL.lastPathComponent
        self.kind = CaptureAttachmentKind.infer(from: fileURL)
    }
}
