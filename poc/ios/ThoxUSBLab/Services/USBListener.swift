// SPDX-License-Identifier: GPL-3.0-or-later
import Foundation
import Network
import THOXWire

/// All socket and cryptographic state is confined to one serial queue.
final class USBListener {
    enum Event {
        case listening
        case authenticating
        case connected
        case disconnected(String)
        case stopped
        case message([String: Any])
    }

    var onEvent: ((Event) -> Void)?
    private let queue = DispatchQueue(label: "ai.thox.usblab.transport")
    private var listener: NWListener?
    private var connection: NWConnection?
    private var framing = FrameCodec()
    private var handshake: ServerHandshake?
    private var handshakeDeadline: DispatchWorkItem?
    private var key: Data?
    private var generation = UUID()

    func start(key: Data) {
        queue.async { [weak self] in self?.startOnQueue(key: key) }
    }

    func stop() {
        queue.async { [weak self] in
            guard let self else { return }
            self.shutdown()
            self.emit(.stopped)
        }
    }

    func send(_ message: [String: Any]) {
        queue.async { [weak self] in
            guard let self else { return }
            guard let connection = self.connection, let channel = self.handshake?.channel else {
                self.emit(.disconnected("No authenticated connection. The request was not sent."))
                return
            }
            do { try self.write(channel.encrypt(message), to: connection) }
            catch { self.dropConnection(error.localizedDescription) }
        }
    }

    private func startOnQueue(key: Data) {
        shutdown()
        self.key = key
        let current = generation
        do {
            let parameters = NWParameters.tcp
            parameters.requiredLocalEndpoint = .hostPort(host: "127.0.0.1", port: 49321)
            let server = try NWListener(using: parameters)
            listener = server
            server.stateUpdateHandler = { [weak self] state in
                guard let self, self.generation == current else { return }
                switch state {
                case .ready: self.emit(.listening)
                case .failed(let error):
                    self.shutdown()
                    self.emit(.disconnected("Listener failed: \(error.localizedDescription)"))
                default: break
                }
            }
            server.newConnectionHandler = { [weak self] candidate in
                guard let self, self.generation == current, self.connection == nil else {
                    candidate.cancel()
                    return
                }
                self.accept(candidate)
            }
            server.start(queue: queue)
        } catch {
            shutdown()
            emit(.disconnected(error.localizedDescription))
        }
    }

    private func accept(_ candidate: NWConnection) {
        guard let key else { candidate.cancel(); return }
        do { handshake = try ServerHandshake(key: key) }
        catch { candidate.cancel(); emit(.disconnected(error.localizedDescription)); return }
        connection = candidate
        framing = FrameCodec()
        emit(.authenticating)
        let timeout = DispatchWorkItem { [weak self, weak candidate] in
            guard let self, let candidate, self.connection === candidate,
                  self.handshake?.isAuthenticated != true else { return }
            self.dropConnection("Pairing handshake timed out. Waiting for a new connection.")
        }
        handshakeDeadline = timeout
        queue.asyncAfter(deadline: .now() + 10, execute: timeout)
        candidate.stateUpdateHandler = { [weak self, weak candidate] state in
            guard let self, let candidate, self.connection === candidate else { return }
            switch state {
            case .ready: self.receive(from: candidate)
            case .failed(let error): self.dropConnection(error.localizedDescription)
            case .cancelled: self.dropConnection("Connection closed. Waiting for Mini.")
            default: break
            }
        }
        candidate.start(queue: queue)
    }

    private func receive(from candidate: NWConnection) {
        candidate.receive(minimumIncompleteLength: 1, maximumLength: 65_536) { [weak self, weak candidate] data, _, complete, error in
            guard let self, let candidate, self.connection === candidate else { return }
            do {
                if let data, !data.isEmpty {
                    for frame in try self.framing.append(data) {
                        guard let handshake = self.handshake else { throw WireError.invalidHandshake }
                        if let channel = handshake.channel {
                            self.emit(.message(try channel.decrypt(frame)))
                        } else {
                            let reply = try handshake.accept(frame)
                            try self.write(reply, to: candidate)
                            if handshake.isAuthenticated {
                                self.handshakeDeadline?.cancel()
                                self.handshakeDeadline = nil
                                self.emit(.connected)
                            }
                        }
                    }
                }
                if let error { self.dropConnection(error.localizedDescription) }
                else if complete { self.dropConnection("Mini disconnected. Reopen its connection to resume.") }
                else { self.receive(from: candidate) }
            } catch { self.dropConnection(error.localizedDescription) }
        }
    }

    private func write(_ message: [String: Any], to candidate: NWConnection) throws {
        let data = try FrameCodec.encode(message)
        candidate.send(content: data, completion: .contentProcessed { [weak self, weak candidate] error in
            guard let self, let candidate, self.connection === candidate, let error else { return }
            self.dropConnection(error.localizedDescription)
        })
    }

    private func dropConnection(_ reason: String) {
        let old = connection
        connection = nil
        old?.stateUpdateHandler = nil
        old?.cancel()
        handshakeDeadline?.cancel()
        handshakeDeadline = nil
        handshake = nil
        framing = FrameCodec()
        emit(.disconnected(reason))
    }

    private func shutdown() {
        generation = UUID()
        listener?.stateUpdateHandler = nil
        listener?.newConnectionHandler = nil
        listener?.cancel()
        listener = nil
        let old = connection
        connection = nil
        old?.stateUpdateHandler = nil
        old?.cancel()
        handshakeDeadline?.cancel()
        handshakeDeadline = nil
        handshake = nil
        key = nil
        framing = FrameCodec()
    }

    private func emit(_ event: Event) {
        // The observable UI owns dispatch onto the main actor.
        onEvent?(event)
    }
}
