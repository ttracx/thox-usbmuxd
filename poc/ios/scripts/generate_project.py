#!/usr/bin/env python3
"""Generate a minimal deterministic Xcode project using only the standard library.

This does not sign/build the app or change any account configuration. XcodeGen's
project.yml is also supplied for teams that prefer their established tooling.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "ThoxUSBLab.xcodeproj"


def ident(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()[:24].upper()


def quote(value: str) -> str:
    return json.dumps(value)


def main() -> None:
    files = sorted((ROOT / "ThoxUSBLab").rglob("*.swift"))
    if not files:
        raise SystemExit("No app sources found")
    objects: list[str] = []

    def obj(label: str, body: str) -> str:
        value = ident(label)
        objects.append(f"\t\t{value} = {{ {body} }};")
        return value

    refs = []
    builds = []
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        ref = obj(f"file:{relative}", f"isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = {quote(relative)}; sourceTree = \"<group>\";")
        refs.append(ref)
        builds.append(obj(f"build:{relative}", f"isa = PBXBuildFile; fileRef = {ref};"))

    package = obj("package", 'isa = XCLocalSwiftPackageReference; relativePath = ".";')
    dependency = obj("package-product", f'isa = XCSwiftPackageProductDependency; package = {package}; productName = THOXWire;')
    package_build = obj("package-build", f"isa = PBXBuildFile; productRef = {dependency};")
    product = obj("product", 'isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = ThoxUSBLab.app; sourceTree = BUILT_PRODUCTS_DIR;')
    products = obj("products", f'isa = PBXGroup; children = ({product},); name = Products; sourceTree = "<group>";')
    sources = obj("source-group", f'isa = PBXGroup; children = ({",".join(refs)},); name = Sources; sourceTree = "<group>";')
    main_group = obj("main-group", f'isa = PBXGroup; children = ({sources}, {products},); sourceTree = "<group>";')
    sources_phase = obj("sources-phase", f'isa = PBXSourcesBuildPhase; buildActionMask = 2147483647; files = ({",".join(builds)},); runOnlyForDeploymentPostprocessing = 0;')
    framework_phase = obj("framework-phase", f'isa = PBXFrameworksBuildPhase; buildActionMask = 2147483647; files = ({package_build},); runOnlyForDeploymentPostprocessing = 0;')
    resources_phase = obj("resources-phase", 'isa = PBXResourcesBuildPhase; buildActionMask = 2147483647; files = (); runOnlyForDeploymentPostprocessing = 0;')

    project_configs = []
    target_configs = []
    for config in ["Debug", "Release"]:
        project_configs.append(obj(f"project-config:{config}", f'isa = XCBuildConfiguration; buildSettings = {{ CLANG_ENABLE_MODULES = YES; IPHONEOS_DEPLOYMENT_TARGET = 17.0; SDKROOT = iphoneos; SWIFT_VERSION = 5.0; }}; name = {config};'))
        settings = {
            "CODE_SIGN_STYLE": "Automatic", "DEVELOPMENT_TEAM": "DVJ6Z5343U",
            "CURRENT_PROJECT_VERSION": "1", "MARKETING_VERSION": "0.1.0",
            "PRODUCT_BUNDLE_IDENTIFIER": "ai.thox.thoxos.usblab", "PRODUCT_NAME": "$(TARGET_NAME)",
            "GENERATE_INFOPLIST_FILE": "YES", "INFOPLIST_KEY_CFBundleDisplayName": "ThoxOS USB Lab",
            "INFOPLIST_KEY_UILaunchScreen_Generation": "YES", "INFOPLIST_KEY_UIApplicationSceneManifest_Generation": "YES",
            "INFOPLIST_KEY_UIApplicationSupportsIndirectInputEvents": "YES",
            "INFOPLIST_KEY_NSLocalNetworkUsageDescription": "Connect to your paired THOX device for explicitly selected document tasks.",
            "TARGETED_DEVICE_FAMILY": "1,2", "SUPPORTED_PLATFORMS": "iphoneos iphonesimulator",
            "SWIFT_VERSION": "5.0", "SWIFT_OPTIMIZATION_LEVEL": "-Onone" if config == "Debug" else "-O",
            "IPHONEOS_DEPLOYMENT_TARGET": "17.0", "ENABLE_PREVIEWS": "YES",
        }
        if config == "Debug":
            settings["SWIFT_ACTIVE_COMPILATION_CONDITIONS"] = "DEBUG $(inherited)"
        assignments = " ".join(f"{key} = {quote(value)};" for key, value in settings.items())
        target_configs.append(obj(f"target-config:{config}", f"isa = XCBuildConfiguration; buildSettings = {{ {assignments} }}; name = {config};"))

    project_list = obj("project-config-list", f'isa = XCConfigurationList; buildConfigurations = ({",".join(project_configs)},); defaultConfigurationIsVisible = 0; defaultConfigurationName = Release;')
    target_list = obj("target-config-list", f'isa = XCConfigurationList; buildConfigurations = ({",".join(target_configs)},); defaultConfigurationIsVisible = 0; defaultConfigurationName = Release;')
    target = obj("target", f'isa = PBXNativeTarget; buildConfigurationList = {target_list}; buildPhases = ({sources_phase}, {framework_phase}, {resources_phase},); buildRules = (); dependencies = (); name = ThoxUSBLab; packageProductDependencies = ({dependency},); productName = ThoxUSBLab; productReference = {product}; productType = "com.apple.product-type.application";')
    project = obj("project", f'isa = PBXProject; attributes = {{ BuildIndependentTargetsInParallel = 1; LastUpgradeCheck = 1600; }}; buildConfigurationList = {project_list}; compatibilityVersion = "Xcode 14.0"; developmentRegion = en; hasScannedForEncodings = 0; knownRegions = (en, Base,); mainGroup = {main_group}; packageReferences = ({package},); productRefGroup = {products}; projectDirPath = ""; projectRoot = ""; targets = ({target},);')
    PROJECT.mkdir(parents=True, exist_ok=True)
    (PROJECT / "project.pbxproj").write_text("// !$*UTF8*$!\n{\n\tarchiveVersion = 1;\n\tclasses = {};\n\tobjectVersion = 56;\n\tobjects = {\n" + "\n".join(objects) + f"\n\t}};\n\trootObject = {project};\n}}\n")
    scheme_dir = PROJECT / "xcshareddata" / "xcschemes"
    scheme_dir.mkdir(parents=True, exist_ok=True)
    reference = f'<BuildableReference BuildableIdentifier="primary" BlueprintIdentifier="{target}" BuildableName="ThoxUSBLab.app" BlueprintName="ThoxUSBLab" ReferencedContainer="container:ThoxUSBLab.xcodeproj"/>'
    scheme = f'''<?xml version="1.0" encoding="UTF-8"?>
<Scheme LastUpgradeVersion="1600" version="1.3">
  <BuildAction parallelizeBuildables="YES" buildImplicitDependencies="YES"><BuildActionEntries><BuildActionEntry buildForTesting="YES" buildForRunning="YES" buildForProfiling="YES" buildForArchiving="YES" buildForAnalyzing="YES">{reference}</BuildActionEntry></BuildActionEntries></BuildAction>
  <TestAction buildConfiguration="Debug" selectedDebuggerIdentifier="Xcode.DebuggerFoundation.Debugger.LLDB" selectedLauncherIdentifier="Xcode.IDEFoundation.Launcher.LLDB" shouldUseLaunchSchemeArgsEnv="YES"><Testables/></TestAction>
  <LaunchAction buildConfiguration="Debug" selectedDebuggerIdentifier="Xcode.DebuggerFoundation.Debugger.LLDB" selectedLauncherIdentifier="Xcode.IDEFoundation.Launcher.LLDB" launchStyle="0" useCustomWorkingDirectory="NO" ignoresPersistentStateOnLaunch="NO" debugDocumentVersioning="YES" debugServiceExtension="internal" allowLocationSimulation="YES"><BuildableProductRunnable runnableDebuggingMode="0">{reference}</BuildableProductRunnable></LaunchAction>
  <ProfileAction buildConfiguration="Release" shouldUseLaunchSchemeArgsEnv="YES" savedToolIdentifier="" useCustomWorkingDirectory="NO" debugDocumentVersioning="YES"><BuildableProductRunnable runnableDebuggingMode="0">{reference}</BuildableProductRunnable></ProfileAction>
  <AnalyzeAction buildConfiguration="Debug"/>
  <ArchiveAction buildConfiguration="Release" revealArchiveInOrganizer="YES"/>
</Scheme>
'''
    (scheme_dir / "ThoxUSBLab.xcscheme").write_text(scheme)
    print(f"Generated {PROJECT.name} with {len(files)} app sources")


if __name__ == "__main__":
    main()
