import AppKit
import SwiftUI

final class ShareViewController: NSViewController {
    private let model = ShareExtensionModel()

    override func loadView() {
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
