import Foundation

enum CapturePayload {
    case text(contentText: String, userHint: String?)
    case file(fileURL: URL, contentText: String?, userHint: String?)

    var contentText: String? {
        switch self {
        case let .text(contentText, _):
            return contentText
        case let .file(_, contentText, _):
            return contentText
        }
    }

    var userHint: String? {
        switch self {
        case let .text(_, userHint):
            return userHint
        case let .file(_, _, userHint):
            return userHint
        }
    }

    var fileURL: URL? {
        switch self {
        case .text:
            return nil
        case let .file(fileURL, _, _):
            return fileURL
        }
    }

    var usesMultipart: Bool {
        fileURL != nil
    }

    func jsonData() throws -> Data {
        let payload = [
            "content_text": contentText ?? "",
            "user_hint": userHint ?? "",
        ]
        return try JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys])
    }

    func multipartData(boundary: String) throws -> Data {
        let fileURL = try requireFileURL()
        var body = Data()

        appendField(named: "content_text", value: contentText ?? "", boundary: boundary, to: &body)
        appendField(named: "user_hint", value: userHint ?? "", boundary: boundary, to: &body)

        let filename = fileURL.lastPathComponent
        let fileData = try Data(contentsOf: fileURL)
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append(
            "Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n".data(using: .utf8)!
        )
        body.append("Content-Type: application/octet-stream\r\n\r\n".data(using: .utf8)!)
        body.append(fileData)
        body.append("\r\n".data(using: .utf8)!)
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)
        return body
    }

    private func requireFileURL() throws -> URL {
        guard let fileURL else {
            throw NativeCaptureClientError.filePayloadRequired
        }
        return fileURL
    }

    private func appendField(named name: String, value: String, boundary: String, to body: inout Data) {
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"\(name)\"\r\n\r\n".data(using: .utf8)!)
        body.append("\(value)\r\n".data(using: .utf8)!)
    }
}
