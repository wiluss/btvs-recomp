import AppKit
import SwiftUI

@MainActor
final class UpdateModel: ObservableObject {
    @Published var working = false
    @Published var state = "idle"
    @Published var notes = ""
    @Published var detail = ""
    @Published var tag: String?
    let root: URL
    private var process: Process?

    init(root: URL) { self.root = root }

    func run(install: Bool) {
        guard !working else { return }
        let task = Process(), pipe = Pipe()
        task.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        task.arguments = [root.appendingPathComponent("tools/update_launcher.py").path, "--target", root.path]
        if install, let tag { task.arguments! += ["--tag", tag] }
        else { task.arguments! += ["--check"] }
        task.currentDirectoryURL = root
        task.standardOutput = pipe
        task.standardError = pipe
        working = true; detail = ""; state = install ? "installing" : "checking"
        process = task
        do { try task.run() }
        catch { detail = error.localizedDescription; state = "error"; working = false; process = nil; return }
        Task.detached {
            var pending = Data(), transcript = ""
            while true {
                let chunk = pipe.fileHandleForReading.availableData
                if chunk.isEmpty { break }
                pending.append(chunk)
                while let newline = pending.firstIndex(of: 10) {
                    let line = Data(pending[..<newline])
                    pending.removeSubrange(...newline)
                    transcript = String((transcript + String(decoding: line, as: UTF8.self) + "\n").suffix(65536))
                    if let row = try? JSONSerialization.jsonObject(with: line) as? [String: Any] {
                        await MainActor.run {
                            if let status = row["status"] as? String { self.state = status }
                            if let message = row["message"] as? String { self.detail = message }
                            if let tag = row["tag"] as? String { self.tag = tag }
                            if let notes = row["notes"] as? String { self.notes = notes }
                        }
                    }
                }
            }
            task.waitUntilExit()
            let output = transcript
            await MainActor.run {
                self.working = false; self.process = nil
                if task.terminationStatus != 0 {
                    self.state = "error"
                    if self.detail.isEmpty { self.detail = output }
                } else if !["available", "current", "complete"].contains(self.state) {
                    self.state = "error"; self.detail = output
                }
            }
        }
    }
}

struct UpdatesView: View {
    @ObservedObject var model: LauncherModel
    @StateObject private var updater: UpdateModel
    init(model: LauncherModel) {
        self.model = model
        _updater = StateObject(wrappedValue: UpdateModel(root: model.root))
    }
    private func tr(_ key: String) -> String { model.tr(key) }
    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            Label(tr("Mises à jour"), systemImage: "arrow.triangle.2.circlepath")
                .font(.title2).foregroundStyle(.purple)
            Text(tr("Le jeu est reconstruit automatiquement si nécessaire. Vos sauvegardes et packs sont conservés."))
                .font(.callout)
            if updater.working {
                ProgressView()
                Text(tr(updater.detail.isEmpty ? "Recherche d’une mise à jour…" : updater.detail))
                    .fixedSize(horizontal: false, vertical: true)
            } else if updater.state == "current" {
                Text(tr("Votre version est à jour."))
            } else if updater.state == "complete" {
                Text(tr("Mise à jour installée. Quittez puis rouvrez le lanceur."))
            } else if updater.state == "available" {
                Text(updater.tag ?? "").font(.headline)
                ScrollView { Text(updater.notes).font(.callout).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading) }.frame(height: 240)
            } else if updater.state == "error" {
                ScrollView { Text(updater.detail).foregroundStyle(.orange).textSelection(.enabled) }.frame(maxHeight: 180)
            }
            HStack {
                Button(tr("Fermer")) { model.showUpdates = false }.disabled(updater.working)
                Spacer()
                if updater.state == "available" {
                    Button(tr("Installer la mise à jour")) { updater.run(install: true) }.disabled(updater.working)
                } else if updater.state != "complete" {
                    Button(tr("Rechercher une mise à jour")) { updater.run(install: false) }.disabled(updater.working)
                }
            }
        }.padding(28).frame(width: 600).preferredColorScheme(.dark).tint(.purple)
            .interactiveDismissDisabled(updater.working)
            .onChange(of: updater.working) { model.updateRunning = $0 }
            .onAppear { updater.run(install: false) }
    }
}
