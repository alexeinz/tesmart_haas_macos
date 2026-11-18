import Foundation

/// Pure helpers for the TESmart matrix ASCII protocol (TCP port 5000).
public enum TesmartProtocol {
    public static let defaultPort: UInt16 = 5000
    public static let presetSlots = 1...8

    public static func routeCommand(input: Int, output: Int) -> String {
        String(format: "MT00SW%02d%02dNT", input, output)
    }
    public static func allOutputsCommand(input: Int) -> String {
        String(format: "MT00SW%02d00NT", input)
    }
    public static let mirrorCommand = "MT00SW0000NT"
    public static let statusCommand = "MT00RD0000NT"

    public static func loadPresetCommand(slot: Int) -> String {
        String(format: "MT00RD01%02dNT", slot)
    }
    public static func savePresetCommand(slot: Int) -> String {
        String(format: "MT00SV00%02dNT", slot)
    }
    /// `enabled == true` means the buzzer sounds.
    public static func buzzerCommand(enabled: Bool) -> String {
        enabled ? "MT00BZEN00NT" : "MT00BZEN01NT"
    }

    /// Decode a port token: 1-9 then A-G for 10-16.
    public static func decodePort(_ token: String) -> Int? {
        if let n = Int(token), (1...16).contains(n) { return n }
        guard token.count == 1, let u = token.uppercased().unicodeScalars.first,
              (65...71).contains(u.value) else { return nil }
        return Int(u.value) - 65 + 10
    }

    /// Parse `LINK:O1I1;O2I3;...;END` into an output -> input map.
    public static func parseRoutes(_ raw: String) -> [Int: Int] {
        let pattern = #"O(1[0-6]|[1-9A-G])I(1[0-6]|[1-9A-G])"#
        guard let re = try? NSRegularExpression(pattern: pattern) else { return [:] }
        let ns = raw as NSString
        var routes: [Int: Int] = [:]
        for m in re.matches(in: raw, range: NSRange(location: 0, length: ns.length)) {
            let o = ns.substring(with: m.range(at: 1))
            let i = ns.substring(with: m.range(at: 2))
            if let out = decodePort(o), let inp = decodePort(i) { routes[out] = inp }
        }
        return routes
    }
}
