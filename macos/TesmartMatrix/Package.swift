// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "TesmartMatrix",
    platforms: [.macOS(.v13)],
    products: [
        .library(name: "TesmartKit", targets: ["TesmartKit"]),
        .executable(name: "TesmartMatrix", targets: ["TesmartMatrix"]),
    ],
    targets: [
        .target(name: "TesmartKit"),
        .executableTarget(name: "TesmartMatrix", dependencies: ["TesmartKit"]),
        .testTarget(name: "TesmartKitTests", dependencies: ["TesmartKit"]),
    ]
)
