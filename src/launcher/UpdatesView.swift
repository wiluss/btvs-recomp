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
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            task.waitUntilExit()
            let output = String(decoding: data, as: UTF8.self)
            await MainActor.run {
                var final: [String: Any]?
                for line in output.split(separator: "\n") {
                    if let row = try? JSONSerialization.jsonObject(with: Data(line.utf8)) as? [String: Any] { final = row }
                }
                self.working = false; self.process = nil
                if task.terminationStatus != 0 {
                    self.state = "error"; self.detail = final?["message"] as? String ?? output
                } else if let final {
                    self.state = final["status"] as? String ?? "error"
                    self.tag = final["tag"] as? String
                    self.notes = final["notes"] as? String ?? ""
                    self.detail = final["message"] as? String ?? ""
                } else { self.state = "error"; self.detail = output }
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
            Text(tr("Le lanceur est mis à jour sans reconstruire le jeu. Vos sauvegardes et packs sont conservés."))
                .font(.callout)
            if updater.working {
                ProgressView()
                Text(tr(updater.state == "installing" ? "Installation du lanceur… Gardez cette fenêtre ouverte." : "Recherche d’une mise à jour…"))
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
