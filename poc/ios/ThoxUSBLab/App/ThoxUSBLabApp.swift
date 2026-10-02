// SPDX-License-Identifier: GPL-3.0-or-later
import SwiftUI

@main
struct ThoxUSBLabApp: App {
    @StateObject private var model = LabModel()
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            ContentView(model: model)
                .preferredColorScheme(.dark)
                .tint(.thoxEmerald)
                .onChange(of: scenePhase) { _, phase in model.sceneChanged(phase) }
        }
    }
}
