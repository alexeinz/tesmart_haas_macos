import Foundation
import SwiftUI
import AppKit
import TesmartKit

struct ConfigSnapshot: Codable {
    var pulledAt: Date
    var host: String
    var port: Int
    var size: Int
    var buzzer: Bool
    var macFilter: String
    var inputNames: [String: String]
    var outputNames: [String: String]
    var routes: [String: Int]      // output -> input, as read from the matrix
}

@MainActor
final class MatrixModel: ObservableObject {
    @AppStorage("host") var host = "192.168.1.10"
    @AppStorage("port") var port = Int(TesmartProtocol.defaultPort)
    @AppStorage("size") var size = 8          // inputs and outputs (8 or 16)
    @AppStorage("buzzer") var buzzer = true
    @AppStorage("macFilter") var macFilter = ""   // full MAC or vendor prefix, e.g. "AA:BB:CC"

    @Published var routes: [Int: Int] = [:]   // output -> input
    @Published var status = "Not connected"
    @Published var busy = false
    @Published var autoRefresh = true

    @Published var inputNames: [Int: String] = MatrixModel.load("inputNames") {
        didSet { MatrixModel.save(inputNames, "inputNames") }
    }
    @Published var outputNames: [Int: String] = MatrixModel.load("outputNames") {
        didSet { MatrixModel.save(outputNames, "outputNames") }
    }

    func inputLabel(_ i: Int) -> String {
        let n = inputNames[i]?.trimmingCharacters(in: .whitespaces) ?? ""
        return n.isEmpty ? "Input \(i)" : n
    }
    func outputLabel(_ o: Int) -> String {
        let n = outputNames[o]?.trimmingCharacters(in: .whitespaces) ?? ""
        return n.isEmpty ? "Out \(o)" : n
    }

    private static func load(_ key: String) -> [Int: String] {
        guard let d = UserDefaults.standard.data(forKey: key),
              let m = try? JSONDecoder().decode([Int: String].self, from: d) else { return [:] }
        return m
    }
    private static func save(_ m: [Int: String], _ key: String) {
        if let d = try? JSONEncoder().encode(m) { UserDefaults.standard.set(d, forKey: key) }
    }

    @Published var discovered: [DiscoveredDevice] = []
    @Published var scanning = false
    private var timer: Timer?
    private var scanTask: Task<Void, Never>?

    func discover() {
        guard !scanning else { scanTask?.cancel(); return }
        scanning = true
        discovered = []
        status = "Scanning local network…"
        let port = UInt16(clamping: self.port)
        scanTask = Task {
            let list = await TesmartDiscovery.scan(port: port, macFilter: macFilter) { d in
                Task { @MainActor in
                    if !self.discovered.contains(d) { self.discovered.append(d) }
                }
            }
            discovered = list
            scanning = false
            if let one = list.first, list.count == 1 { select(one) }
            status = list.isEmpty ? (macFilter.isEmpty ? "No matrix found on the local network" : "No matrix with MAC \(macFilter) found") : "Found \(list.count) matrix(es)"
        }
    }

    func select(_ d: DiscoveredDevice) {
        host = d.host
        size = d.outputs > 8 ? 16 : 8
        Task { await refresh() }
    }

    private var client: TesmartClient {
        TesmartClient(host: host, port: UInt16(clamping: port))
    }

    func startPolling() {
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: 10, repeats: true) { [weak self] _ in
            Task { @MainActor in
                guard let self, self.autoRefresh, !self.busy else { return }
                await self.refresh()
            }
        }
        Task { await refresh() }
    }

    /// Reads the live routing from the matrix and saves it with settings and names.
    func pullConfig() async {
        await refresh()
        guard !routes.isEmpty else { return }
        let snap = ConfigSnapshot(
            pulledAt: Date(), host: host, port: port, size: size, buzzer: buzzer, macFilter: macFilter,
            inputNames: Dictionary(uniqueKeysWithValues: inputNames.map { (String($0.key), $0.value) }),
            outputNames: Dictionary(uniqueKeysWithValues: outputNames.map { (String($0.key), $0.value) }),
            routes: Dictionary(uniqueKeysWithValues: routes.map { (String($0.key), $0.value) }))
        let panel = NSSavePanel()
        panel.nameFieldStringValue = "tesmart-config.json"
        panel.allowedContentTypes = [.json]
        guard panel.runModal() == .OK, let url = panel.url else { return }
        let enc = JSONEncoder()
        enc.outputFormatting = [.prettyPrinted, .sortedKeys]
        enc.dateEncodingStrategy = .iso8601
        do {
            try enc.encode(snap).write(to: url)
            status = "Config pulled → \(url.lastPathComponent)"
        } catch { status = "Save failed: \(error.localizedDescription)" }
    }

    /// Loads settings and names from a pulled config file (routes are not applied).
    func importConfig() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.json]
        guard panel.runModal() == .OK, let url = panel.url else { return }
        do {
            let dec = JSONDecoder(); dec.dateDecodingStrategy = .iso8601
            let c = try dec.decode(ConfigSnapshot.self, from: Data(contentsOf: url))
            host = c.host; port = c.port; size = c.size; buzzer = c.buzzer; macFilter = c.macFilter
            inputNames = Dictionary(uniqueKeysWithValues: c.inputNames.compactMap { k, v in Int(k).map { ($0, v) } })
            outputNames = Dictionary(uniqueKeysWithValues: c.outputNames.compactMap { k, v in Int(k).map { ($0, v) } })
            status = "Imported \(url.lastPathComponent)"
        } catch { status = "Import failed: \(error.localizedDescription)" }
    }

    func refresh() async {
        await run("Refreshed") { c in
            self.routes = try await c.routes(expectedOutputs: self.size)
        }
    }

    func route(input: Int, output: Int) async {
        await run("Output \(output) ← Input \(input)") { c in
            try await c.send(TesmartProtocol.routeCommand(input: input, output: output))
            self.routes = try await c.routes(expectedOutputs: self.size)
        }
    }

    func setAll(input: Int) async {
        await run("All outputs ← Input \(input)") { c in
            try await c.send(TesmartProtocol.allOutputsCommand(input: input))
            self.routes = try await c.routes(expectedOutputs: self.size)
        }
    }

    func mirror() async {
        await run("Mirrored outputs") { c in
            try await c.send(TesmartProtocol.mirrorCommand)
            self.routes = try await c.routes(expectedOutputs: self.size)
        }
    }

    func loadPreset(_ slot: Int) async {
        await run("Loaded preset \(slot)") { c in
            try await c.send(TesmartProtocol.loadPresetCommand(slot: slot))
            self.routes = try await c.routes(expectedOutputs: self.size)
        }
    }

    func savePreset(_ slot: Int) async {
        await run("Saved preset \(slot)") { c in
            try await c.send(TesmartProtocol.savePresetCommand(slot: slot))
        }
    }

    func setBuzzer(_ on: Bool) async {
        await run(on ? "Buzzer on" : "Buzzer muted") { c in
            try await c.send(TesmartProtocol.buzzerCommand(enabled: on))
            self.buzzer = on
        }
    }

    private func run(_ ok: String, _ work: (TesmartClient) async throws -> Void) async {
        busy = true
        defer { busy = false }
        do {
            try await work(client)
            status = ok
        } catch {
            status = error.localizedDescription
        }
    }
}
