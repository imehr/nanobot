import SwiftUI
import UniformTypeIdentifiers

struct FileDropZone: View {
    let files: [URL]
    let onDropFiles: ([URL]) -> Void

    @State private var isTargeted = false

    var body: some View {
        RoundedRectangle(cornerRadius: 18, style: .continuous)
            .strokeBorder(style: StrokeStyle(lineWidth: 2, dash: [10, 8]))
            .foregroundStyle(isTargeted ? Color.accentColor : Color.secondary.opacity(0.4))
            .background(
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .fill(isTargeted ? Color.accentColor.opacity(0.08) : Color.secondary.opacity(0.08))
            )
            .frame(minHeight: 140)
            .overlay {
                VStack(spacing: 10) {
                    Image(systemName: "square.and.arrow.down")
                        .font(.system(size: 28, weight: .semibold))
                    Text(files.isEmpty ? "Drop files here" : "Drop more files here")
                        .font(.headline)
                    Text("Receipts, screenshots, PDFs, and images are copied into the inbox before any routing happens.")
                        .multilineTextAlignment(.center)
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: 360)
                }
                .padding(20)
            }
            .onDrop(of: [UTType.fileURL.identifier], isTargeted: $isTargeted) { providers in
                loadProviders(providers)
            }
    }

    private func loadProviders(_ providers: [NSItemProvider]) -> Bool {
        guard !providers.isEmpty else {
            return false
        }

        for provider in providers where provider.hasItemConformingToTypeIdentifier(UTType.fileURL.identifier) {
            provider.loadDataRepresentation(forTypeIdentifier: UTType.fileURL.identifier) { data, _ in
                guard
                    let data,
                    let url = NSURL(
                        absoluteURLWithDataRepresentation: data,
                        relativeTo: nil
                    ) as URL?
                else {
                    return
                }

                DispatchQueue.main.async {
                    onDropFiles([url])
                }
            }
        }

        return true
    }
}
