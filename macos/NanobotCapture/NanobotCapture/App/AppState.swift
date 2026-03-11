import Foundation

final class AppState: ObservableObject {
    @Published var lastStatus: String = "Ready"
}
