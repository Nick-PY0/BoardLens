import SwiftUI
import WebKit

@main
struct BoardLensCompanionApp: App {
    var body: some Scene { WindowGroup { CompanionView().preferredColorScheme(.dark) } }
}

struct CompanionView: View {
    @AppStorage("computerAddress") private var address = ""
    @State private var code = ""
    @State private var page: URL?
    @State private var error = ""
    private let background = Color(red: 0.063, green: 0.110, blue: 0.090)
    private let accent = Color(red: 0.57, green: 0.87, blue: 0.71)
    var body: some View {
        Group {
            if let url = page {
                VStack(spacing: 0) {
                    HStack { Button("Computer") { page = nil }; Spacer(); Text("BoardLens Companion").font(.headline) }.padding()
                    CompanionWebView(url: url) { message in error = message; page = nil }
                }
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: 18) {
                        Text("BoardLens").font(.largeTitle.bold()).foregroundStyle(accent)
                        Text("Your chess helper, on your phone or iPad").font(.title2.bold())
                        Text("On your computer, open BoardLens → Phone and enable the companion. Use the same Wi-Fi on both devices.")
                        if !error.isEmpty { Text(error).foregroundStyle(.orange) }
                        Text("Computer address").font(.headline)
                        TextField("192.168.1.50:8789", text: $address).textInputAutocapitalization(.never).autocorrectionDisabled().keyboardType(.URL).textFieldStyle(.roundedBorder)
                        Text("Pairing code").font(.headline)
                        TextField("Six-digit code", text: $code).keyboardType(.numberPad).textContentType(.oneTimeCode).textFieldStyle(.roundedBorder)
                        Button(action: connect) { Text("Connect to computer").font(.headline).frame(maxWidth: .infinity).padding(8) }.buttonStyle(.borderedProminent).tint(accent).foregroundStyle(background)
                        Text("The computer keeps reading the boards and running the engine. This app shows the moves, evaluations, settings and controls.").foregroundStyle(.secondary)
                    }.padding(24).frame(maxWidth: 560)
                }.frame(maxWidth: .infinity)
            }
        }.background(background).tint(accent)
    }
    private func connect() {
        var raw = address.trimmingCharacters(in: .whitespacesAndNewlines)
        if !raw.contains("://") { raw = "http://" + raw }
        guard var components = URLComponents(string: raw), let host = components.host, !host.isEmpty,
              components.user == nil, ["http", "https"].contains(components.scheme ?? "") else { error = "Enter the computer address shown in BoardLens."; return }
        if components.port == nil { components.port = 8789 }
        components.path = "/"; components.query = nil; components.fragment = nil
        address = components.string ?? raw
        let pairing = code.trimmingCharacters(in: .whitespacesAndNewlines)
        if !pairing.isEmpty {
            guard pairing.count == 6, pairing.allSatisfy(\.isNumber) else { error = "Enter the six-digit code shown on your computer."; return }
            components.fragment = "pair=" + pairing
        }
        error = ""; page = components.url
    }
}

struct CompanionWebView: UIViewRepresentable {
    let url: URL
    let onFailure: (String) -> Void
    func makeCoordinator() -> Coordinator { Coordinator(onFailure: onFailure) }
    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .default()
        let view = WKWebView(frame: .zero, configuration: configuration)
        view.navigationDelegate = context.coordinator
        view.isOpaque = false
        view.backgroundColor = UIColor(red: 0.063, green: 0.110, blue: 0.090, alpha: 1)
        return view
    }
    func updateUIView(_ view: WKWebView, context: Context) {
        // Updating SwiftUI state must not reload a connected live dashboard.
        if context.coordinator.loadedURL != url {
            context.coordinator.loadedURL = url
            view.load(URLRequest(url: url))
        }
    }
    final class Coordinator: NSObject, WKNavigationDelegate {
        var loadedURL: URL?
        let onFailure: (String) -> Void
        init(onFailure: @escaping (String) -> Void) { self.onFailure = onFailure }
        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
            onFailure("Could not reach the computer. Keep its companion enabled, check Wi-Fi and the address, and allow local network access when iOS asks.")
        }
    }
}
