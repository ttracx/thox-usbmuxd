// SPDX-License-Identifier: GPL-3.0-or-later
import Foundation
import SwiftUI
import THOXWire

@MainActor
final class LabModel: ObservableObject {
    @Published var pairingInput = ""
    @Published var hasPairingKey = false
    @Published var listenerEnabled = false
    @Published var connected = false
    @Published var connectionLabel = "Stopped"
    @Published var connectionDetail = "Open the app and start the listener before connecting Mini."
    @Published var errorMessage: String?
    @Published var documentName = "No document selected"
    @Published var documentText = ""
    @Published var mode = "analyze"
    @Published var executor = "No device connected"
    @Published var supportsInference = false
    @Published var jobID: String
    @Published var jobStatus = "No job"
    @Published var resultText = ""
    @Published var pendingCount = 0

    private let transport = USBListener()
    private var isForeground = true
    private var requests: [String: (operation: String, timeout: Task<Void, Never>)] = [:]
    private static let savedJob = "THOXUSBLab.lastJobID"

    init() {
        jobID = UserDefaults.standard.string(forKey: Self.savedJob) ?? ""
        transport.onEvent = { [weak self] event in
            Task { @MainActor [weak self] in self?.receive(event) }
        }
        do { hasPairingKey = try PairingKeyStore.load() != nil }
        catch { errorMessage = error.localizedDescription }
    }

    var canSubmit: Bool { connected && !documentText.isEmpty && pendingCount == 0 }
    var canCancel: Bool { connected && !jobID.isEmpty && ["queued", "running"].contains(jobStatus) }

    func saveKey() {
        do {
            let key = try PairingKey.decode(pairingInput)
            stopListener()
            try PairingKeyStore.save(key)
            hasPairingKey = true
            pairingInput = ""
            errorMessage = nil
            connectionDetail = "Pairing key saved on this device. Start the listener when ready."
        } catch { errorMessage = error.localizedDescription }
    }

    func forgetKey() {
        stopListener()
        do { try PairingKeyStore.remove(); hasPairingKey = false; pairingInput = "" }
        catch { errorMessage = error.localizedDescription }
    }

    func startListener() {
        guard isForeground else { return }
        do {
            guard let key = try PairingKeyStore.load() else { throw WireError.invalidKey }
            errorMessage = nil
            listenerEnabled = true
            connectionLabel = "Starting"
            connectionDetail = "Opening the USB app listener on port 49321."
            transport.start(key: key)
        } catch { errorMessage = error.localizedDescription }
    }

    func stopListener() {
        listenerEnabled = false
        connected = false
        transport.stop()
        clearPending()
    }

    func sceneChanged(_ phase: ScenePhase) {
        if phase == .background {
            isForeground = false
            connected = false
            transport.stop()
            clearPending()
            connectionLabel = "Paused"
            connectionDetail = "Jobs remain on Mini. Return to the app to reconnect."
        } else if phase == .active {
            let returnedFromBackground = !isForeground
            isForeground = true
            if listenerEnabled && returnedFromBackground { startListener() }
        }
    }

    func importDocument(_ result: Result<[URL], Error>) {
        do {
            guard let url = try result.get().first else { return }
            let access = url.startAccessingSecurityScopedResource()
            defer { if access { url.stopAccessingSecurityScopedResource() } }
            let handle = try FileHandle(forReadingFrom: url)
            defer { try? handle.close() }
            let bytes = try handle.read(upToCount: 65_537) ?? Data()
            guard !bytes.isEmpty, bytes.count <= 65_536,
                  let text = String(data: bytes, encoding: .utf8) else {
                throw NSError(domain: "THOXDocument", code: 1, userInfo: [
                    NSLocalizedDescriptionKey: "Choose a nonempty UTF-8 text file no larger than 65,536 bytes."
                ])
            }
            documentText = text
            documentName = url.lastPathComponent
            errorMessage = nil
        } catch { errorMessage = error.localizedDescription }
    }

    func submit() {
        guard canSubmit else { return }
        guard mode == "analyze" || supportsInference else {
            errorMessage = "Inference must be configured by the Mini operator."
            return
        }
        request("job_submit", args: ["text": documentText, "mode": mode])
    }

    func refresh() {
        guard !jobID.isEmpty else { return }
        request("job_get", args: ["job_id": jobID])
    }

    func cancel() {
        guard canCancel else { return }
        request("job_cancel", args: ["job_id": jobID])
    }

    private func request(_ operation: String, args: [String: Any] = [:]) {
        guard connected else { errorMessage = "Connect Mini first."; return }
        guard requests.count < 8 else { errorMessage = "Wait for the outstanding request to finish."; return }
        let id = UUID().uuidString.lowercased()
        let timeout = Task { [weak self] in
            do { try await Task.sleep(nanoseconds: 15_000_000_000) } catch { return }
            guard let self, self.requests.removeValue(forKey: id) != nil else { return }
            self.pendingCount = self.requests.count
            self.errorMessage = operation == "job_submit"
                ? "Submission response was lost. Reconnect and refresh the saved job before submitting again."
                : "Request timed out. Reconnect or refresh the saved job."
        }
        requests[id] = (operation, timeout)
        pendingCount = requests.count
        if operation == "job_submit" {
            // The protocol makes the request UUID the durable job ID. Persist it
            // before sending so an accepted job can be recovered after ACK loss.
            jobID = id
            jobStatus = "Awaiting acknowledgement"
            resultText = ""
            UserDefaults.standard.set(id, forKey: Self.savedJob)
        }
        transport.send(["type": "request", "id": id, "op": operation, "args": args])
    }

    private func receive(_ event: USBListener.Event) {
        switch event {
        case .listening:
            connectionLabel = "Waiting for Mini"
            connectionDetail = "USB listener ready on 127.0.0.1:49321. Keep this app open."
        case .authenticating:
            connectionLabel = "Verifying device"
            connectionDetail = "Checking the shared pairing key."
        case .connected:
            connected = true
            connectionLabel = "Connected securely"
            connectionDetail = "Paired USB session • foreground only"
            request("status")
            if !jobID.isEmpty { refresh() }
        case .disconnected(let reason):
            connected = false
            connectionLabel = listenerEnabled ? "Waiting to reconnect" : "Stopped"
            connectionDetail = reason
            clearPending()
        case .stopped:
            connected = false
            connectionLabel = listenerEnabled ? "Paused" : "Stopped"
            if !listenerEnabled { connectionDetail = "Listener stopped. Jobs already accepted remain on Mini." }
        case .message(let message):
            processResponse(message)
        }
    }

    private func processResponse(_ message: [String: Any]) {
        guard message["type"] as? String == "response", let id = message["id"] as? String,
              let pending = requests.removeValue(forKey: id), let ok = message["ok"] as? Bool else {
            errorMessage = "Unexpected response received. Connection closed."
            stopListener()
            return
        }
        pending.timeout.cancel()
        pendingCount = requests.count
        guard ok else {
            let error = message["error"] as? [String: Any]
            errorMessage = error?["message"] as? String ?? "Mini rejected the request."
            return
        }
        guard let result = message["result"] as? [String: Any] else {
            errorMessage = "Mini returned an invalid result."
            stopListener()
            return
        }
        if pending.operation == "status" {
            executor = pretty(result["executor"] ?? result["device"] ?? "Mini")
            let capabilities = result["capabilities"] as? [String] ?? []
            supportsInference = capabilities.contains("inference")
            if !supportsInference { mode = "analyze" }
        } else if ["job_submit", "job_get", "job_cancel"].contains(pending.operation) {
            guard let id = result["id"] as? String, UUID(uuidString: id) != nil,
                  let status = result["status"] as? String,
                  ["queued", "running", "completed", "failed", "cancelled"].contains(status) else {
                errorMessage = "Mini returned an invalid job."
                stopListener()
                return
            }
            jobID = id
            jobStatus = status
            UserDefaults.standard.set(id, forKey: Self.savedJob)
            resultText = pretty(result)
        }
    }

    private func clearPending() {
        if requests.values.contains(where: { $0.operation == "job_submit" }) {
            errorMessage = "Submission confirmation was lost. Reconnect and refresh the saved job before submitting again."
        }
        requests.values.forEach { $0.timeout.cancel() }
        requests.removeAll()
        pendingCount = 0
    }

    private func pretty(_ value: Any) -> String {
        if let string = value as? String { return string }
        if JSONSerialization.isValidJSONObject(value),
           let data = try? JSONSerialization.data(withJSONObject: value, options: [.prettyPrinted, .sortedKeys]),
           let text = String(data: data, encoding: .utf8) { return text }
        return String(describing: value)
    }
}
