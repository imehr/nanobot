import XCTest
@testable import NanobotCapture

@MainActor
final class MenuBarCaptureTests: XCTestCase {
    func testPasteTextFlowStoresNote() {
        let model = MenuBarCaptureViewModel()

        model.note = "Book the regular bike service"
        model.hint = "bike"

        XCTAssertEqual(model.note, "Book the regular bike service")
        XCTAssertEqual(model.hint, "bike")
    }

    func testClipboardActionLoadsIncomingText() {
        let model = MenuBarCaptureViewModel()

        let loaded = model.loadClipboardText("Front tire pressure is 35 psi")

        XCTAssertTrue(loaded)
        XCTAssertEqual(model.note, "Front tire pressure is 35 psi")
    }

    func testQueuedAndCompletedResultRenderingUsesQueueStatus() {
        let model = MenuBarCaptureViewModel()

        model.applyQueued(
            CaptureResponse(
                captureId: "cap-123",
                status: "queued",
                inboxItemPath: "/tmp/inbox/item.md",
                entities: [],
                actions: ["saved original", "queued"],
                followUp: nil
            )
        )

        XCTAssertEqual(model.resultMessage, "Queued cap-123")

        model.applyStatus(
            CaptureStatusResponse(
                captureId: "cap-123",
                status: "completed",
                sourceChannel: "telegram",
                captureType: "text",
                inboxItemPath: "/tmp/inbox/item.md",
                primaryPath: "/Mehr/Projects/nanobot/timeline.md",
                canonicalPaths: ["/Mehr/Work/projects/nanobot/index.md"],
                archivePaths: [],
                projectMemoryPaths: ["/Mehr/Projects/nanobot/timeline.md"],
                followUp: nil,
                error: nil,
                queuedAt: "2026-03-14T10:00:00"
            )
        )

        XCTAssertEqual(model.resultMessage, "Saved to Project Memory: /Mehr/Projects/nanobot/timeline.md")
    }

    func testEmbeddedShareExtensionBundleDeclaresShareServiceManifest() throws {
        let pluginsURL = try XCTUnwrap(Bundle.main.builtInPlugInsURL)
        let extensionURL = pluginsURL.appendingPathComponent("NanobotCaptureShareExtension.appex")
        let extensionBundle = try XCTUnwrap(Bundle(url: extensionURL))
        let extensionManifest = try XCTUnwrap(extensionBundle.infoDictionary?["NSExtension"] as? [String: Any])

        XCTAssertEqual(extensionManifest["NSExtensionPointIdentifier"] as? String, "com.apple.share-services")
        XCTAssertEqual(
            extensionManifest["NSExtensionPrincipalClass"] as? String,
            "NanobotCaptureShareExtension.ShareViewController"
        )

        XCTAssertEqual(extensionBundle.object(forInfoDictionaryKey: "CFBundleDisplayName") as? String, "Nanobot Capture")
        XCTAssertEqual(extensionBundle.object(forInfoDictionaryKey: "CFBundleIconName") as? String, "AppIcon")

        let attributes = try XCTUnwrap(extensionManifest["NSExtensionAttributes"] as? [String: Any])
        XCTAssertEqual(attributes["NSExtensionActivationDictionaryVersion"] as? Int, 2)
        XCTAssertEqual(attributes["NSExtensionPointName"] as? String, "com.apple.share-services")
        XCTAssertEqual(attributes["NSExtensionPointVersion"] as? String, "1.0")
        XCTAssertEqual(attributes["NSExtensionServiceAllowsToolbarItem"] as? Bool, true)
        let rule = try XCTUnwrap(attributes["NSExtensionActivationRule"] as? String)
        XCTAssertTrue(rule.contains("public.text"))
        XCTAssertTrue(rule.contains("public.url"))
        XCTAssertTrue(rule.contains("public.file-url"))
        XCTAssertTrue(rule.contains("public.image"))
        XCTAssertTrue(rule.contains("com.apple.webarchive"))
        XCTAssertTrue(rule.contains("com.apple.rtfd"))
        XCTAssertTrue(rule.contains("com.apple.flat-rtfd"))
    }

    func testEmbeddedAppBundleDeclaresCaptureAppIcon() {
        XCTAssertEqual(Bundle.main.object(forInfoDictionaryKey: "CFBundleIconName") as? String, "AppIcon")
    }

    func testEmbeddedAppAndShareExtensionContainSandboxEntitlements() throws {
        let appEntitlements = try entitlementsXML(for: Bundle.main.bundleURL)
        XCTAssertTrue(appEntitlements.contains("com.apple.security.app-sandbox"))
        XCTAssertTrue(appEntitlements.contains("com.apple.security.network.client"))
        XCTAssertTrue(appEntitlements.contains("com.apple.security.files.user-selected.read-write"))

        let pluginsURL = try XCTUnwrap(Bundle.main.builtInPlugInsURL)
        let extensionURL = pluginsURL.appendingPathComponent("NanobotCaptureShareExtension.appex")
        let extensionEntitlements = try entitlementsXML(for: extensionURL)
        XCTAssertTrue(extensionEntitlements.contains("com.apple.security.app-sandbox"))
        XCTAssertTrue(extensionEntitlements.contains("com.apple.security.network.client"))
        XCTAssertTrue(extensionEntitlements.contains("com.apple.security.files.user-selected.read-write"))
    }

    private func entitlementsXML(for bundleURL: URL) throws -> String {
        let process = Process()
        let output = Pipe()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/codesign")
        process.arguments = ["-d", "--entitlements", ":-", bundleURL.path]
        process.standardOutput = output
        process.standardError = output
        try process.run()
        process.waitUntilExit()

        let data = output.fileHandleForReading.readDataToEndOfFile()
        let text = String(decoding: data, as: UTF8.self)
        XCTAssertEqual(process.terminationStatus, 0, "codesign failed for \(bundleURL.path): \(text)")
        return text
    }
}
