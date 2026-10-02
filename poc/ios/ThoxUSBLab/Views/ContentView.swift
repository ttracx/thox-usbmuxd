// SPDX-License-Identifier: GPL-3.0-or-later
import SwiftUI
import UniformTypeIdentifiers

extension Color {
    static let thoxEmerald = Color(red: 0.20, green: 0.83, blue: 0.60)
    static let thoxInk = Color(red: 0.04, green: 0.06, blue: 0.06)
}

struct ContentView: View {
    @ObservedObject var model: LabModel
    @State private var importing = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    header
                    connection
                    pairing
                    workspace
                    job
                    Text("Your AI. Your Data. Your Rules.™")
                        .font(.footnote).foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity)
                    Text("© 2026 THOX.ai LLC. All rights reserved, subject to applicable licenses.\nTHOX.ai™ and THOX product names and logos are trademarks of THOX.ai LLC.\nOther marks belong to their respective owners.")
                        .font(.caption2).foregroundStyle(.secondary)
                        .multilineTextAlignment(.center).frame(maxWidth: .infinity)
                }
                .padding(20)
                .frame(maxWidth: 720)
                .frame(maxWidth: .infinity)
            }
            .background(Color.thoxInk)
            .navigationTitle("ThoxOS USB Lab")
            .navigationBarTitleDisplayMode(.inline)
            .fileImporter(isPresented: $importing, allowedContentTypes: [.plainText], allowsMultipleSelection: false) {
                model.importDocument($0)
            }
            .alert("USB Lab", isPresented: Binding(
                get: { model.errorMessage != nil },
                set: { if !$0 { model.errorMessage = nil } }
            )) {
                Button("OK", role: .cancel) { model.errorMessage = nil }
            } message: {
                Text(model.errorMessage ?? "")
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 10) {
            Label("THOX  /  EXPERIMENTAL", systemImage: "cpu")
                .font(.system(.caption, design: .monospaced).weight(.semibold))
                .foregroundStyle(Color.thoxEmerald)
            Text("A private workspace.\nConnected to Mini.")
                .font(.system(.largeTitle, design: .rounded).weight(.semibold))
            Text("Select a document, send a task, and bring the result back into ThoxOS.")
                .foregroundStyle(.secondary)
        }
    }

    private var connection: some View {
        card {
            HStack {
                Image(systemName: model.connected ? "checkmark.shield.fill" : "cable.connector")
                    .font(.title2).foregroundStyle(Color.thoxEmerald)
                VStack(alignment: .leading, spacing: 4) {
                    Text(model.connectionLabel).font(.headline)
                    Text(model.connectionDetail).font(.caption).foregroundStyle(.secondary)
                }
                Spacer()
                if model.pendingCount > 0 { ProgressView().accessibilityLabel("Waiting for Mini") }
            }
            HStack {
                Button(model.listenerEnabled ? "Stop listener" : "Start USB listener") {
                    if model.listenerEnabled { model.stopListener() } else { model.startListener() }
                }
                .buttonStyle(.borderedProminent)
                .disabled(!model.hasPairingKey)
                Spacer()
                Text("USB · 49321").font(.system(.caption, design: .monospaced)).foregroundStyle(.secondary)
            }
            Text("Execution: \(model.executor)")
                .font(.caption).foregroundStyle(.secondary).textSelection(.enabled)
        }
    }

    private var pairing: some View {
        card {
            Label("Pair this iPhone", systemImage: "key.horizontal").font(.headline)
            Text(model.hasPairingKey ? "A pairing key is saved in this device’s Keychain." : "Import the 32-byte base64 pairing key generated on Mini.")
                .font(.subheadline).foregroundStyle(.secondary)
            SecureField("Base64 pairing key", text: $model.pairingInput)
                .textInputAutocapitalization(.never).autocorrectionDisabled()
                .textFieldStyle(.roundedBorder)
                .accessibilityIdentifier("pairingKey")
            HStack {
                Button("Save key", action: model.saveKey)
                    .buttonStyle(.bordered).disabled(model.pairingInput.isEmpty)
                if model.hasPairingKey {
                    Button("Forget key", role: .destructive, action: model.forgetKey).buttonStyle(.borderless)
                }
            }
            Text("Use a trusted path to transfer the key. Saving a new key ends the current session.")
                .font(.caption).foregroundStyle(.secondary)
        }
    }

    private var workspace: some View {
        card {
            Label("Selected document", systemImage: "doc.text").font(.headline)
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(model.documentName).lineLimit(2)
                    Text("\(model.documentText.utf8.count.formatted()) / 65,536 bytes · UTF-8 text")
                        .font(.caption).foregroundStyle(.secondary)
                }
                Spacer()
                Button("Choose file") { importing = true }.buttonStyle(.bordered)
            }
            Picker("Task", selection: $model.mode) {
                Text("Analyze text").tag("analyze")
                if model.supportsInference { Text("Model inference").tag("inference") }
            }
            .pickerStyle(.segmented)
            Text(model.mode == "analyze"
                 ? "Analyze returns deterministic text statistics and a SHA-256 digest. It does not run a language model."
                 : "Run the inference provider configured on Mini. Review the execution location above before sending.")
                .font(.caption).foregroundStyle(.secondary)
            Button(action: model.submit) {
                Label("Send selected text to Mini", systemImage: "arrow.up.right")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent).disabled(!model.canSubmit)
        }
    }

    private var job: some View {
        card {
            HStack {
                Label("Saved job", systemImage: "tray.and.arrow.down").font(.headline)
                Spacer()
                Text(model.jobStatus.capitalized).font(.caption).foregroundStyle(Color.thoxEmerald)
            }
            if model.jobID.isEmpty {
                Text("Results stay on Mini when the USB connection ends.")
                    .font(.subheadline).foregroundStyle(.secondary)
            } else {
                Text(model.jobID).font(.system(.caption2, design: .monospaced))
                    .foregroundStyle(.secondary).textSelection(.enabled)
                HStack {
                    Button("Refresh", action: model.refresh).buttonStyle(.bordered)
                        .disabled(!model.connected || model.pendingCount > 0)
                    Button("Cancel job", role: .destructive, action: model.cancel).buttonStyle(.bordered)
                        .disabled(!model.canCancel || model.pendingCount > 0)
                    Spacer()
                    if !model.resultText.isEmpty {
                        ShareLink(item: model.resultText) { Image(systemName: "square.and.arrow.up") }
                            .accessibilityLabel("Share job result")
                    }
                }
                if !model.resultText.isEmpty {
                    Text(model.resultText).font(.system(.caption, design: .monospaced))
                        .textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading)
                }
            }
            Text("Keep ThoxOS open for the USB connection. Return to reconnect and refresh an accepted job; submissions are never automatically retried.")
                .font(.caption).foregroundStyle(.secondary)
        }
    }

    private func card<Content: View>(@ViewBuilder _ content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 14, content: content)
            .padding(18).frame(maxWidth: .infinity, alignment: .leading)
            .background(Color.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 18))
            .overlay(RoundedRectangle(cornerRadius: 18).stroke(Color.white.opacity(0.09), lineWidth: 1))
    }
}
