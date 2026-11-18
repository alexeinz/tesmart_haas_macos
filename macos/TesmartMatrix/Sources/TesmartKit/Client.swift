import Foundation
import Network

public enum TesmartError: Error, LocalizedError {
    case connectionFailed(String)
    case timeout
    case incomplete(got: Int, expected: Int)

    public var errorDescription: String? {
        switch self {
        case .connectionFailed(let m): return "Connection failed: \(m)"
        case .timeout: return "Timed out talking to the matrix"
        case .incomplete(let g, let e): return "Incomplete route data (\(g) of \(e) outputs)"
        }
    }
}

/// One-shot TCP transactions; an actor serializes access because the device
/// handles a single connection at a time.
public actor TesmartClient {
    public let host: String
    public let port: UInt16
    public let timeout: TimeInterval

    public init(host: String, port: UInt16 = TesmartProtocol.defaultPort, timeout: TimeInterval = 3) {
        self.host = host
        self.port = port
        self.timeout = timeout
    }

    public func routes(expectedOutputs: Int) async throws -> [Int: Int] {
        var last: [Int: Int] = [:]
        for _ in 0..<3 {
            let reply = try await transact(TesmartProtocol.statusCommand, expectReply: true)
            last = TesmartProtocol.parseRoutes(reply)
            if !last.isEmpty && last.count >= expectedOutputs { return last }
            try await Task.sleep(nanoseconds: 200_000_000)
        }
        throw TesmartError.incomplete(got: last.count, expected: expectedOutputs)
    }

    /// Raw status reply; used to identify a matrix during discovery.
    public func statusReply() async throws -> String {
        try await transact(TesmartProtocol.statusCommand, expectReply: true)
    }

    public func send(_ command: String) async throws {
        _ = try await transact(command, expectReply: false)
    }

    private func transact(_ command: String, expectReply: Bool) async throws -> String {
        guard let nwPort = NWEndpoint.Port(rawValue: port) else {
            throw TesmartError.connectionFailed("invalid port")
        }
        let conn = NWConnection(host: NWEndpoint.Host(host), port: nwPort, using: .tcp)
        let timeout = self.timeout
        return try await withTaskCancellationHandler {
            try await withCheckedThrowingContinuation { (cont: CheckedContinuation<String, Error>) in
                let state = Once(cont)
                let queue = DispatchQueue(label: "tesmart.client")
                queue.asyncAfter(deadline: .now() + timeout) {
                    state.finish(.failure(TesmartError.timeout)); conn.cancel()
                }
                conn.stateUpdateHandler = { st in
                    switch st {
                    case .ready:
                        conn.send(content: Data((command + "\r\n").utf8), completion: .contentProcessed { err in
                            if let err { state.finish(.failure(TesmartError.connectionFailed(err.localizedDescription))); conn.cancel(); return }
                            if expectReply {
                                Self.receive(conn, buffer: Data(), state: state)
                            } else {
                                state.finish(.success("")); conn.cancel()
                            }
                        })
                    case .failed(let e), .waiting(let e):
                        state.finish(.failure(TesmartError.connectionFailed(e.localizedDescription))); conn.cancel()
                    default: break
                    }
                }
                conn.start(queue: queue)
            }
        } onCancel: { conn.cancel() }
    }

    private static func receive(_ conn: NWConnection, buffer: Data, state: Once) {
        conn.receive(minimumIncompleteLength: 1, maximumLength: 4096) { data, _, isComplete, error in
            var buf = buffer
            if let data { buf.append(data) }
            let text = String(decoding: buf, as: UTF8.self)
            if text.contains("END") || isComplete || error != nil {
                state.finish(.success(text)); conn.cancel()
            } else {
                receive(conn, buffer: buf, state: state)
            }
        }
    }
}

/// Resumes a continuation exactly once.
private final class Once: @unchecked Sendable {
    private let lock = NSLock()
    private var cont: CheckedContinuation<String, Error>?
    init(_ c: CheckedContinuation<String, Error>) { cont = c }
    func finish(_ result: Result<String, Error>) {
        lock.lock(); let c = cont; cont = nil; lock.unlock()
        c?.resume(with: result)
    }
}
