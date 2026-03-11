import AppKit
import SwiftUI

final class ShareViewController: NSViewController {
    override func loadView() {
        self.view = NSHostingView(rootView: ShareView(title: "Nanobot Share Extension"))
    }
}
