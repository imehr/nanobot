import SwiftUI

struct ShareView: View {
    let title: String

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title)
                .font(.title2.bold())
            Text("Share extension scaffold for native Nanobot capture.")
                .foregroundStyle(.secondary)
        }
        .padding(20)
        .frame(minWidth: 320, minHeight: 180, alignment: .topLeading)
    }
}
