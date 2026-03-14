import SwiftUI

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
                    .foregroundStyle(model.resultState == .failure ? .red : .secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            HStack {
                if model.resultState == .success {
                    Button("Done") {
                        onDone()
                    }
                    .buttonStyle(.borderedProminent)
                } else {
                    Button("Cancel") {
                        onCancel()
                    }
                    Spacer()
                    Button(model.isSubmitting ? "Sending..." : "Send to Nanobot") {
                        Task {
                            _ = await model.submit()
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(!model.canSubmit)
                }
            }
        }
        .padding(20)
        .frame(minWidth: 360, minHeight: 220, alignment: .topLeading)
    }
}
