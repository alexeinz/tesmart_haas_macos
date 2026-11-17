import Foundation
import Darwin

public struct DiscoveredDevice: Identifiable, Hashable, Sendable {
    public let host: String
    public let outputs: Int
    public let mac: String?
    public var id: String { host }
}

/// Finds matrices by probing every address of the local /24 networks with the
/// status command and keeping hosts that answer with a valid LINK reply.
public enum TesmartDiscovery {
    /// IPv4 addresses (as host strings) to probe, from all up non-loopback interfaces.
    public static func candidateHosts() -> [String] {
        var result: [String] = []
        var ifap: UnsafeMutablePointer<ifaddrs>?
        guard getifaddrs(&ifap) == 0, let first = ifap else { return [] }
        defer { freeifaddrs(ifap) }
        var seenBases = Set<UInt32>()
        for p in sequence(first: first, next: { $0.pointee.ifa_next }) {
            let f = Int32(p.pointee.ifa_flags)
            guard f & IFF_UP != 0, f & IFF_LOOPBACK == 0,
                  let a = p.pointee.ifa_addr, a.pointee.sa_family == UInt8(AF_INET) else { continue }
            let ip = a.withMemoryRebound(to: sockaddr_in.self, capacity: 1) { UInt32(bigEndian: $0.pointee.sin_addr.s_addr) }
            let base = ip & 0xFFFF_FF00
            guard seenBases.insert(base).inserted else { continue }
            for last in 1...254 {
                let h = base | UInt32(last)
                if h == ip { continue }
                result.append("\(h >> 24).\((h >> 16) & 255).\((h >> 8) & 255).\(h & 255)")
            }
        }
        return result
    }

    public static func scan(port: UInt16 = TesmartProtocol.defaultPort,
                            concurrency: Int = 48,
                            macFilter: String = "",
                            onFound: @escaping @Sendable (DiscoveredDevice) -> Void) async -> [DiscoveredDevice] {
        let hosts = candidateHosts()
        var found: [DiscoveredDevice] = []
        await withTaskGroup(of: DiscoveredDevice?.self) { group in
            var it = hosts.makeIterator()
            func add() -> Bool {
                guard let h = it.next() else { return false }
                group.addTask { await probe(host: h, port: port, macFilter: macFilter) }
                return true
            }
            for _ in 0..<concurrency { if !add() { break } }
            for await r in group {
                if let r { found.append(r); onFound(r) }
                _ = add()
                if Task.isCancelled { group.cancelAll() }
            }
        }
        return found.sorted { $0.host.localizedStandardCompare($1.host) == .orderedAscending }
    }

    /// Lowercase hex digits only, e.g. "AA:bb-1" -> "aabb1".
    static func normalizeMAC(_ s: String) -> String {
        s.lowercased().filter { $0.isHexDigit }
    }

    /// MAC of a host from the ARP cache (populated by the probe's connection attempt).
    public static func arpMAC(host: String) -> String? {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/usr/sbin/arp")
        p.arguments = ["-n", host]
        let out = Pipe()
        p.standardOutput = out; p.standardError = Pipe()
        guard (try? p.run()) != nil else { return nil }
        let data = out.fileHandleForReading.readDataToEndOfFile()
        p.waitUntilExit()
        let text = String(decoding: data, as: UTF8.self)
        guard let r = text.range(of: " at ") else { return nil }
        let token = text[r.upperBound...].split(separator: " ").first.map(String.init) ?? ""
        let parts = token.split(separator: ":")
        guard parts.count == 6 else { return nil }
        return parts.map { $0.count == 1 ? "0\($0)" : String($0) }.joined(separator: ":").uppercased()
    }

    static func probe(host: String, port: UInt16, macFilter: String) async -> DiscoveredDevice? {
        let client = TesmartClient(host: host, port: port, timeout: 1.2)
        guard let reply = try? await client.statusReply(), reply.contains("LINK") else { return nil }
        let routes = TesmartProtocol.parseRoutes(reply)
        guard !routes.isEmpty else { return nil }
        let mac = arpMAC(host: host)
        let want = normalizeMAC(macFilter)
        if !want.isEmpty, !(mac.map(normalizeMAC)?.hasPrefix(want) ?? false) { return nil }
        return DiscoveredDevice(host: host, outputs: routes.count, mac: mac)
    }
}
