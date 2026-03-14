import SwiftUI

struct CaptureAttachmentPanel: View {
    let attachments: [CaptureAttachment]
    let onDropFiles: ([URL]) -> Void
    let onChooseFiles: () -> Void
    let onPasteClipboard: () -> Void
    let onClear: () -> Void
    let onRemoveAttachment: (UUID) -> Void

    private let columns = [
        GridItem(.adaptive(minimum: 220, maximum: 280), spacing: 16, alignment: .top),
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Attachments")
                        .font(.title3.bold())
                    Text("Paste screenshots, drag files, or attach receipts and PDFs. Images stay inline as attachment cards.")
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Text("\(attachments.count) item\(attachments.count == 1 ? "" : "s")")
                    .foregroundStyle(.secondary)
            }

            FileDropZone(files: attachments.map(\.fileURL), onDropFiles: onDropFiles)

            HStack {
                Button("Choose Files", action: onChooseFiles)
                Button("Paste Clipboard", action: onPasteClipboard)
                Button("Clear", action: onClear)
                    .disabled(attachments.isEmpty)
                Spacer()
            }

            if attachments.isEmpty {
                Text("No attachments yet. A pasted screenshot should appear here immediately as a thumbnail card.")
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.top, 6)
            } else {
                LazyVGrid(columns: columns, alignment: .leading, spacing: 16) {
                    ForEach(attachments) { attachment in
                        CaptureAttachmentCard(attachment: attachment) {
                            onRemoveAttachment(attachment.id)
                        }
                    }
                }
            }
        }
    }
}
