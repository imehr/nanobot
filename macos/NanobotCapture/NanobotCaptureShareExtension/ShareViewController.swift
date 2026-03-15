import AppKit
import SwiftUI

final class ShareViewController: NSViewController {
    private let model = ShareExtensionModel()

    override func loadView() {
        preferredContentSize = NSSize(width: 540, height: 380)

        self.view = NSHostingView(
            rootView: ShareView(
                model: model,
                onCancel: { [weak self] in
                    self?.extensionContext?.cancelRequest(withError: NSError(domain: "NanobotShare", code: 1))
                },
                onDone: { [weak self] in
                    self?.extensionContext?.completeRequest(returningItems: nil)
                }
            )
        )
        view.frame = NSRect(origin: .zero, size: preferredContentSize)
    }

    override func viewDidLoad() {
        super.viewDidLoad()
        Task { @MainActor [weak self] in
            guard let self else {
                return
            }
            let items = (self.extensionContext?.inputItems as? [NSExtensionItem]) ?? []
            await model.load(items: items)
        }
    }
}
