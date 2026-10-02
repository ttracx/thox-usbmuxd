// swift-tools-version: 5.9
// SPDX-License-Identifier: GPL-3.0-or-later
import PackageDescription

let package = Package(
    name: "THOXWire",
    platforms: [.iOS(.v17), .macOS(.v13)],
    products: [.library(name: "THOXWire", targets: ["THOXWire"])],
    targets: [
        .target(name: "THOXWire"),
        .testTarget(name: "THOXWireTests", dependencies: ["THOXWire"], resources: [.process("Fixtures")])
    ]
)
