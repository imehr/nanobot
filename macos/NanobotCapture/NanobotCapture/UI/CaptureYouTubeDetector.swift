import Foundation
import SwiftUI

/// Research harness topic hints. Must match the topic ids in
/// smaug/config/topic-research.json so the downstream agent routes correctly.
enum VideoResearchTopic: String, CaseIterable, Identifiable {
    case agents
    case llm
    case coding
    case robotics
    case vision
    case threeD = "three_d"
    case audio
    case image
    case video

    var id: String { rawValue }

    var label: String {
        switch self {
        case .agents: return "Agents & Automation"
        case .llm: return "LLMs & Reasoning"
        case .coding: return "AI Coding"
        case .robotics: return "Robotics"
        case .vision: return "Computer Vision"
        case .threeD: return "3D & Gaussian Splatting"
        case .audio: return "Audio, TTS, Voice"
        case .image: return "Image Models"
        case .video: return "Video Models"
        }
    }
}

/// Detects YouTube URLs in free-form capture text. Covers watch, shorts, live,
/// embed, and youtu.be short links. Case-insensitive.
enum YouTubeURLDetector {
    static let pattern: NSRegularExpression = {
        // swiftlint:disable:next force_try
        try! NSRegularExpression(
            pattern: #"https?://(?:www\.)?(?:m\.)?(?:youtube\.com/(?:watch\?v=|shorts/|live/|embed/)[A-Za-z0-9_-]{11}(?:[?&#][^\s]*)?|youtu\.be/[A-Za-z0-9_-]{11}(?:[?&#][^\s]*)?)"#,
            options: [.caseInsensitive]
        )
    }()

    static func firstURL(in text: String) -> String? {
        let range = NSRange(text.startIndex..<text.endIndex, in: text)
        guard
            let match = pattern.firstMatch(in: text, options: [], range: range),
            let swiftRange = Range(match.range, in: text)
        else { return nil }
        return String(text[swiftRange])
    }

    static func containsYouTubeURL(_ text: String) -> Bool {
        firstURL(in: text) != nil
    }
}

/// Inline banner + topic picker shown in the capture window when the editor
/// contains a YouTube URL. Binds directly to the hint field — when the user
/// picks a topic, the hint becomes the topic raw value (e.g. "agents") so
/// server-side downstream dispatch (smaug/config/topic-research.json) picks
/// the right blueprint slot.
struct CaptureYouTubeTopicBanner: View {
    let detectedURL: String
    @Binding var hint: String

    private var selectedTopic: VideoResearchTopic? {
        VideoResearchTopic(rawValue: hint)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Image(systemName: "play.rectangle.fill")
                    .foregroundStyle(.red)
                    .font(.title3)
                Text("YouTube URL detected")
                    .font(.headline)
                Spacer()
                Text("→ video research pipeline")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Text(detectedURL)
                .font(.system(.caption, design: .monospaced))
                .lineLimit(1)
                .truncationMode(.middle)
                .foregroundStyle(.secondary)

            HStack {
                Text("Topic hint:")
                    .font(.subheadline)
                Picker("Topic hint", selection: Binding<VideoResearchTopic?>(
                    get: { selectedTopic },
                    set: { newValue in hint = newValue?.rawValue ?? "" }
                )) {
                    Text("— pick one —").tag(Optional<VideoResearchTopic>.none)
                    ForEach(VideoResearchTopic.allCases) { topic in
                        Text(topic.label).tag(Optional<VideoResearchTopic>.some(topic))
                    }
                }
                .labelsHidden()
                .pickerStyle(.menu)
                .frame(maxWidth: 260)
                Spacer()
            }
        }
        .padding(14)
        .background(Color.accentColor.opacity(0.08), in: RoundedRectangle(cornerRadius: 14, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .stroke(Color.accentColor.opacity(0.35), lineWidth: 1)
        )
    }
}
