import AppKit
import CoreText
import SwiftUI
import UniformTypeIdentifiers

struct LaunchSettings {
    var scale = 2
    var uhd = false
    var widescreen = false
    // UHD always uses widescreen gameplay; retain the scaled-mode preference.
    var effectiveWidescreen: Bool {
        get { uhd || widescreen }
        set { widescreen = newValue }
    }
    var edges = true
    var fps = true
    var fullscreen = false
    var vsync = true
    var linear = true
    var texturesHD = true
    var textHD = true
    var arenas = true
    var customPack: URL?
    let saveProfile: URL

    init(root: URL) {
        saveProfile = root.appendingPathComponent("private/profile")
        guard let raw = try? Data(contentsOf: root.appendingPathComponent("private/config/graphics.json")),
              let prefs = (try? JSONSerialization.jsonObject(with: raw)) as? [String: Any] else { return }
        if let savedScale = prefs["scale"] as? Int, (1...4).contains(savedScale) {
            scale = savedScale
        }
        uhd = prefs["resolution"] as? String == "4k"
        widescreen = prefs["aspect"] as? String == "16:9"
        edges = prefs["hud"] as? String != "safe"
        fps = prefs["fps"] as? Bool ?? fps
        fullscreen = prefs["fullscreen"] as? Bool ?? fullscreen
        vsync = prefs["vsync"] as? Bool ?? vsync
        linear = prefs["filter"] as? String != "nearest"
        if let textures = prefs["textures"] as? String { texturesHD = textures != "original" }
        if let text = prefs["text"] as? String { textHD = text == "hd" || (text == "auto" && texturesHD) }
        arenas = prefs["arenas"] as? Bool ?? arenas
    }

    func arguments() -> [String] {
        var args = ["menu", "--seconds", "0"]
        args += ["--aspect", effectiveWidescreen ? "16:9" : "4:3"]
        args += ["--hud", edges ? "edges" : "safe"]
        args += fps ? ["--fps"] : ["--no-fps"]
        args += fullscreen ? ["--fullscreen"] : ["--windowed"]
        args += vsync ? ["--vsync"] : ["--no-vsync"]
        args += ["--filter", linear ? "linear" : "nearest"]
        args += ["--text", textHD ? "hd" : "original"]
        args += uhd ? ["--resolution", "4k"] : ["--scale", String(scale)]
        if let pack = customPack { args += ["--texture-pack", pack.path] } else {
            args += ["--textures", texturesHD ? "campaign2x" : "original"]
        }
        args += arenas ? ["--unlock-arenas"] : ["--no-unlock-arenas"]
        args += ["--profile", saveProfile.path]
        return args
    }

}

@MainActor
final class LauncherModel: ObservableObject {
    let root: URL
    @Published private(set) var logo: NSImage?
    @Published private(set) var logoMoon: NSImage?
    @Published private(set) var mist: NSImage?
    @Published private(set) var veil: NSImage?
    @Published private(set) var decorativeFontAvailable = false
    @Published var showJournal = false
    @Published var showControls = false
    @Published var showSetup = false
    @Published var showUpdates = false
    @Published var showSupport = false
    @Published var supportReport = false
    @Published var supportRunning = false
    @Published var backupFailure = false
    @Published var backupFailureMessage = ""
    @Published var updateRunning = false
    @Published var setupISO: URL?
    @Published private(set) var setupRunning = false
    @Published private(set) var setupComplete = false
    @Published private(set) var setupFailed = false
    @Published private(set) var setupStage = "Vérification de l’ISO…"
    @Published private(set) var setupFraction: Double?
    @Published private(set) var hdRunning = false
    @Published private(set) var hdStatus = ""
    var busy: Bool { running || setupRunning || hdRunning || updateRunning || supportRunning }
    @Published var language: LauncherLanguage { didSet { if language != oldValue { saveLanguage() } } }
    @Published private(set) var controls = ControlProfile()
    @Published private(set) var controlsLoadFailed = false
    @Published var preferencesError: String? = nil
    @Published private(set) var exitCode: Int? = nil
    @Published var settings: LaunchSettings
    @Published private(set) var running = false
    @Published private(set) var statusKey = "Installation locale détectée"
    @Published private(set) var transcript = ""
    @Published private(set) var launchFailed = false

    private var process: Process?
    private var output: FileHandle?
    private var setupBuffer = ""

    init() {
        root = Bundle.main.bundleURL.deletingLastPathComponent().deletingLastPathComponent()
        let languageURL = root.appendingPathComponent("private/config/launcher.json")
        let prefs = (try? Data(contentsOf: languageURL)).flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: String] }
        language = prefs?["language"].flatMap(LauncherLanguage.init(rawValue:)) ?? .system
        settings = LaunchSettings(root: root)
        let controlsURL = root.appendingPathComponent("private/config/controls.json")
        if FileManager.default.fileExists(atPath: controlsURL.path) {
            do { controls = try ControlProfile.load(controlsURL) }
            catch { controlsLoadFailed = true }
        }
        if !FileManager.default.fileExists(atPath: campaignPack.path) {
            settings.texturesHD = false
        }
        if !textAvailable { settings.textHD = false }
        if !localInstallationDetected { statusKey = "Installation locale à préparer" }
        reloadArtwork()
    }

    func tr(_ key: String) -> String { LauncherText.text(key, language: language) }

    var status: String {
        let text = tr(statusKey)
        return exitCode.map { text + " · \($0)" } ?? text
    }

    private func saveLanguage() {
        do {
            let path = root.appendingPathComponent("private/config/launcher.json")
            try FileManager.default.createDirectory(at: path.deletingLastPathComponent(), withIntermediateDirectories: true)
            let data = try JSONEncoder().encode(["language": language.rawValue])
            try data.write(to: path, options: .atomic)
        } catch { preferencesError = error.localizedDescription }
    }

    func saveControls(_ profile: ControlProfile) throws {
        guard profile.valid else { throw CocoaError(.fileWriteInvalidFileName) }
        let path = root.appendingPathComponent("private/config/controls.json")
        try FileManager.default.createDirectory(at: path.deletingLastPathComponent(), withIntermediateDirectories: true)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        try encoder.encode(profile).write(to: path, options: .atomic)
        controls = profile
        controlsLoadFailed = false
    }

    var campaignPack: URL {
        assetURL("textures/campaign-ui-hd.xrtp")
    }

    var campaignAvailable: Bool {
        FileManager.default.fileExists(atPath: campaignPack.path)
    }

    var textAvailable: Bool {
        FileManager.default.isReadableFile(atPath: assetURL("textures/original-text-hd.xrtp").path)
    }

    private func assetURL(_ name: String) -> URL {
        let legacy = root.appendingPathComponent("private/" + name)
        return FileManager.default.fileExists(atPath: legacy.path)
            ? legacy : root.appendingPathComponent("private/hd/1/" + name)
    }

    private func reloadArtwork() {
        logoMoon = Bundle.main.url(forResource: "LogoMoon", withExtension: "png").flatMap(NSImage.init(contentsOf:))
        logo = Bundle.main.url(forResource: "Logo", withExtension: "png").flatMap(NSImage.init(contentsOf:))
            ?? NSImage(contentsOf: assetURL("launcher/logo.png"))
        mist = NSImage(contentsOf: assetURL("launcher/mist-1.png"))
        veil = NSImage(contentsOf: assetURL("launcher/mist-2.png"))
        let font = assetURL("fonts/buffy-decorative/BuffyDecorative.ttf")
        if FileManager.default.isReadableFile(atPath: font.path) {
            CTFontManagerRegisterFontsForURL(font as CFURL, .process, nil)
        }
        decorativeFontAvailable = NSFont(name: "BuffyDecorative-Regular", size: 20) != nil
    }

    func openHDDownload() {
        NSWorkspace.shared.open(URL(string: "https://github.com/wiluss/btvs-recomp/releases")!)
    }

    func chooseHDArchive() {
        guard !busy, localInstallationDetected else { return }
        let panel = NSOpenPanel()
        panel.message = tr("Choisir le pack HD ZIP…")
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = false
        panel.allowedContentTypes = [.zip]
        if panel.runModal() == .OK, let archive = panel.url { installHDArchive(archive) }
    }

    private func installHDArchive(_ archive: URL) {
        guard process == nil else { return }
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        task.currentDirectoryURL = root
        task.arguments = [root.appendingPathComponent("tools/hd_pack.py").path, "install", archive.path]
        task.standardInput = FileHandle.nullDevice
        let pipe = Pipe(); task.standardOutput = pipe; task.standardError = pipe
        let reader = pipe.fileHandleForReading
        transcript = ""; hdStatus = "Installation du pack HD…"
        reader.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty else { handle.readabilityHandler = nil; return }
            let text = String(decoding: data, as: UTF8.self)
            Task { @MainActor in
                guard let self, self.process === task || self.process == nil else { return }
                self.transcript = String((self.transcript + text).suffix(18_000))
            }
        }
        task.terminationHandler = { [weak self] finished in
            Task { @MainActor in
                guard let self, self.process === finished else { return }
                self.hdRunning = false
                self.hdStatus = finished.terminationStatus == 0 ? "Pack HD installé" : "Installation HD interrompue. Consulte le journal."
                if finished.terminationStatus == 0 {
                    self.settings.texturesHD = self.campaignAvailable
                    self.settings.textHD = self.textAvailable
                    self.reloadArtwork()
                }
                self.process = nil; self.output = nil
            }
        }
        process = task; output = reader
        do { try task.run(); hdRunning = true }
        catch {
            reader.readabilityHandler = nil; process = nil; output = nil
            transcript = error.localizedDescription
            hdStatus = "Installation HD interrompue. Consulte le journal."
        }
    }

    func chooseISO() {
        guard !busy else { return }
        let panel = NSOpenPanel()
        panel.message = tr("Choisir une ISO…")
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = false
        panel.allowedContentTypes = [UTType(filenameExtension: "iso"), UTType(filenameExtension: "xiso")].compactMap { $0 }
        if panel.runModal() == .OK {
            setupISO = panel.url; setupComplete = false; setupFailed = false
        }
    }

    func prepareGame() {
        guard process == nil, let iso = setupISO else { return }
        setupComplete = false; setupFailed = false; setupFraction = nil
        setupStage = "Vérification de l’ISO…"
        setupBuffer = ""
        transcript = ""
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        task.currentDirectoryURL = root
        task.arguments = [root.appendingPathComponent("tools/setup_game.py").path, iso.path, "--build"]
        let pipe = Pipe(); task.standardOutput = pipe; task.standardError = pipe
        let reader = pipe.fileHandleForReading
        reader.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty else { handle.readabilityHandler = nil; return }
            let text = String(decoding: data, as: UTF8.self)
            Task { @MainActor in
                guard let self, self.process === task || self.process == nil else { return }
                self.transcript = String((self.transcript + text).suffix(18_000))
                guard self.process === task else { return }
                self.setupBuffer += text
                while let newline = self.setupBuffer.firstIndex(of: "\n") {
                    let line = String(self.setupBuffer[..<newline]); self.setupBuffer.removeSubrange(...newline)
                    guard let object = try? JSONSerialization.jsonObject(with: Data(line.utf8)) as? [String: Any],
                          let stage = object["stage"] as? String else { continue }
                    let labels = ["inspect":"Vérification de l’ISO…", "extract":"Extraction du jeu…",
                                  "tools":"Préparation des outils…", "patches":"Préparation des outils…",
                                  "generate":"Préparation des fichiers du jeu…", "compile":"Construction du jeu…"]
                    if let label = labels[stage] { self.setupStage = label }
                    self.setupFraction = nil
                    if stage == "extract", let done = object["done"] as? Double, let total = object["total"] as? Double, total > 0 {
                        self.setupFraction = min(1, done / total)
                    }
                    if stage == "ready" { self.setupComplete = true }
                }
            }
        }
        task.terminationHandler = { [weak self] finished in
            Task { @MainActor in
                guard let self, self.process === finished else { return }
                self.setupRunning = false
                // Exit status is authoritative even if the last pipe event
                // reaches the main actor after the termination callback.
                self.setupComplete = finished.terminationStatus == 0
                self.setupFailed = !self.setupComplete
                if self.setupComplete { self.statusKey = "Installation locale détectée" }
                self.process = nil; self.output = nil
            }
        }
        process = task; output = reader
        do { try task.run(); setupRunning = true }
        catch {
            reader.readabilityHandler = nil; process = nil; output = nil
            transcript = error.localizedDescription; setupFailed = true
        }
    }

    // Presence only: play.py still verifies the XBE, packs and profile.
    var localInstallationDetected: Bool {
        let files = FileManager.default
        return files.isExecutableFile(atPath: root.appendingPathComponent("build/game/buffy-macos").path)
            && files.isReadableFile(atPath: root.appendingPathComponent("private/game/Default.xbe").path)
            && files.isReadableFile(atPath: root.appendingPathComponent("tools/play.py").path)
    }

    var gameResolution: String {
        if settings.uhd { return "3840 × 2160" }
        return "\((settings.widescreen ? 854 : 640) * settings.scale) × \(480 * settings.scale)"
    }

    func openPreparationGuide() {
        NSWorkspace.shared.open(root.appendingPathComponent("docs/ALPHA.md"))
    }

    func choosePack() {
        let panel = NSOpenPanel()
        panel.message = tr("Choisis un pack XRTP local")
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = false
        if let xrtp = UTType(filenameExtension: "xrtp") {
            panel.allowedContentTypes = [xrtp]
        }
        if panel.runModal() == .OK, let url = panel.url {
            _ = selectPack([url])
        }
    }

    // Selection only. The existing launch path verifies the pack's contents.
    @discardableResult
    func selectPack(_ urls: [URL]) -> Bool {
        guard !busy, urls.count == 1, let url = urls.first, url.isFileURL,
              url.pathExtension.lowercased() == "xrtp",
              (try? url.resourceValues(forKeys: [.isRegularFileKey]))?.isRegularFile == true,
              FileManager.default.isReadableFile(atPath: url.path) else { return false }
        settings.customPack = url
        return true
    }

    func copyJournal() {
        guard !transcript.isEmpty else { return }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(transcript, forType: .string)
    }

    func openSavedGames() {
        let folder = settings.saveProfile
        NSWorkspace.shared.open(FileManager.default.fileExists(atPath: folder.path)
                                ? folder : folder.deletingLastPathComponent())
    }

    func launch() {
        guard !busy, process == nil, !showControls, !showJournal, !showSetup, !showUpdates, !showSupport else { return }
        supportRunning = true
        statusKey = "Copie de secours du profil…"
        PlayerSupportService.run(root: root, arguments: ["backup", "--auto"]) { _, error in
            self.supportRunning = false
            if let error {
                self.backupFailureMessage = error
                self.backupFailure = true
            } else { self.launchPrepared() }
        }
    }

    func launchPrepared() {
        guard !busy, process == nil, !showControls, !showJournal, !showSetup, !showUpdates, !showSupport else { return }
        if FileManager.default.fileExists(atPath: root.appendingPathComponent("private/profile-restore.json").path) {
            preferencesError = tr("Une restauration interrompue doit être récupérée avant de jouer.")
            return
        }
        launchFailed = false
        exitCode = nil
        let script = root.appendingPathComponent("tools/play.py")
        guard FileManager.default.isReadableFile(atPath: script.path) else {
            statusKey = "Dossier btvs-recomp introuvable"
            launchFailed = true
            return
        }
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        task.currentDirectoryURL = root
        task.arguments = [script.path] + settings.arguments()
        let journal = Pipe()
        task.standardOutput = journal
        task.standardError = journal
        task.standardInput = FileHandle.nullDevice
        transcript = ""
        statusKey = "Vérification du jeu et des packs…"
        let reader = journal.fileHandleForReading
        reader.readabilityHandler = { [weak self, weak task] handle in
            let data = handle.availableData
            if data.isEmpty { handle.readabilityHandler = nil; return }
            let text = String(decoding: data, as: UTF8.self)
            Task { @MainActor in
                guard let self, let task, self.process === task || self.process == nil else { return }
                self.transcript = String((self.transcript + text).suffix(18_000))
                guard self.process === task else { return }
                if self.transcript.contains("HDD de test") && self.statusKey != "Arrêt en cours…" {
                    self.statusKey = "Lancement en cours"
                }
            }
        }
        task.terminationHandler = { [weak self] finished in
            let code = finished.terminationStatus
            Task { @MainActor in
                guard let self, self.process === finished else { return }
                self.statusKey = code == 0 ? "Session terminée" : "Lancement interrompu"
                self.exitCode = code == 0 ? nil : Int(code)
                self.launchFailed = code != 0
                self.running = false
                self.process = nil
                self.output = nil
            }
        }
        process = task
        output = reader
        do {
            try task.run()
            running = true
        } catch {
            reader.readabilityHandler = nil
            process = nil
            output = nil
            statusKey = error.localizedDescription
            launchFailed = true
        }
    }

    func stop() {
        guard let process, process.isRunning else { return }
        statusKey = "Arrêt en cours…"
        process.interrupt()
    }
}

@main
struct BuffyLauncher: App {
    @StateObject private var model = LauncherModel()

    var body: some Scene {
        Window("btvs-recomp", id: "launcher") {
            LauncherView(model: model)
                .onDisappear { model.stop() }
                .onReceive(NotificationCenter.default.publisher(for: NSApplication.willTerminateNotification)) { _ in
                    model.stop()
                }
        }
        .windowStyle(.hiddenTitleBar)
        .defaultSize(width: 1000, height: 740)
        .commands {
            CommandGroup(after: .help) {
                Button(model.tr("Rapport de problème")) { model.supportReport = true; model.showSupport = true }
                    .disabled(model.busy || model.showControls || model.showSetup || model.showUpdates)
                Button(model.tr("Journal de session")) { model.showJournal = true }.disabled(model.showControls || model.showSetup)
                    .keyboardShortcut("j", modifiers: [.command, .option])
                Button(model.tr("Rechercher une mise à jour")) { model.showUpdates = true }
                    .disabled(model.busy || model.showControls || model.showSetup || model.showJournal)
                Button(model.tr("Guide d’installation")) { model.openPreparationGuide() }
                Button(model.tr("Préparer depuis une ISO…")) { model.showSetup = true }
                    .disabled(model.busy || model.showControls || model.showJournal)
            }
        }
    }
}
