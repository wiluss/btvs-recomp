import AppKit
import SwiftUI

@MainActor
enum PlayerSupportService {
    static func run(root: URL, arguments: [String], completion: @escaping ([String: Any]?, String?) -> Void) {
        let task = Process(), pipe = Pipe()
        task.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        task.arguments = [root.appendingPathComponent("src/launcher/player_support.py").path] + arguments + ["--root", root.path]
        task.currentDirectoryURL = root; task.standardOutput = pipe; task.standardError = pipe
        do { try task.run() } catch { completion(nil,error.localizedDescription); return }
        Task.detached {
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            task.waitUntilExit()
            let output = String(decoding: data, as: UTF8.self)
            await MainActor.run {
                let row = output.split(separator: "\n").last.flatMap { try? JSONSerialization.jsonObject(with: Data($0.utf8)) as? [String: Any] }
                completion(row, task.terminationStatus == 0 ? nil : row?["message"] as? String ?? output)
            }
        }
    }
}

struct BackupChoice: Identifiable {
    let id: String
    let created: String
    let automatic: Bool
    let bytes: Int
}

struct PlayerSupportView: View {
    @ObservedObject var model: LauncherModel
    @State private var entries: [BackupChoice] = []
    @State private var selected = ""
    @State private var detail = ""
    @State private var report = ""
    @State private var reportURL: URL?
    @State private var confirmRestore = false
    private func tr(_ key: String) -> String { model.tr(key) }

    private func run(_ arguments: [String], completed: @escaping ([String: Any]) -> Void) {
        guard !model.supportRunning else { return }
        model.supportRunning = true; detail = ""
        PlayerSupportService.run(root: model.root, arguments: arguments) { row, error in
            model.supportRunning = false
            if let error { detail = error }
            else if let row { completed(row) }
            else { detail = tr("Erreur") }
        }
    }
    private func refresh() {
        run(["list"]) { row in
            entries = (row["backups"] as? [[String: Any]] ?? []).compactMap { item in
                guard let id = item["id"] as? String, let created = item["created"] as? String else { return nil }
                return BackupChoice(id: id, created: created, automatic: item["automatic"] as? Bool ?? false, bytes: item["bytes"] as? Int ?? 0)
            }
            if !entries.contains(where: { $0.id == selected }) { selected = entries.first?.id ?? "" }
        }
    }
    private func createReport() {
        run(["report"]) { row in
            report = row["text"] as? String ?? ""
            reportURL = (row["path"] as? String).map { URL(fileURLWithPath: $0) }
        }
    }
    private func backupLabel(_ item: BackupChoice) -> String {
        let parser = DateFormatter(); parser.locale = Locale(identifier: "en_US_POSIX"); parser.timeZone = TimeZone(secondsFromGMT: 0); parser.dateFormat = "yyyyMMdd'T'HHmmss'Z'"
        let display = DateFormatter(); display.locale = Locale(identifier: model.language.rawValue); display.dateStyle = .medium; display.timeStyle = .short
        let date = parser.date(from: item.created).map { display.string(from: $0) } ?? item.created
        return date + " · " + tr(item.automatic ? "Automatique" : "Manuelle") + " · " + ByteCountFormatter.string(fromByteCount: Int64(item.bytes), countStyle: .file)
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text(tr(model.supportReport ? "Rapport de problème" : "Sauvegardes de secours"))
                .font(.title2).foregroundStyle(Color(red: 0.71, green: 0.47, blue: 0.97))
            if model.supportReport {
                Text(tr("Vérifiez ce rapport avant de le partager. Aucun envoi automatique."))
                ScrollView { Text(report).font(.system(size: 11, design: .monospaced)).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading) }.frame(height: 280)
                HStack {
                    Button(tr("Copier")) { NSPasteboard.general.clearContents(); NSPasteboard.general.setString(report, forType: .string) }.disabled(report.isEmpty)
                    Button(tr("Afficher le fichier")) { if let reportURL { NSWorkspace.shared.activateFileViewerSelecting([reportURL]) } }.disabled(reportURL == nil)
                    Button(tr("Actualiser"), action: createReport).disabled(model.supportRunning)
                }
            } else {
                Text(tr("Trois copies automatiques du profil complet sont conservées avant les sessions. Fermez le jeu pour sauvegarder ou restaurer."))
                if entries.isEmpty { Text(tr("Aucune copie de secours pour le moment.")) }
                else {
                    Picker(tr("Copie à restaurer"), selection: $selected) {
                        ForEach(entries) { item in Text(backupLabel(item)).tag(item.id) }
                    }
                }
                HStack {
                    Button(tr("Créer une copie maintenant")) { run(["backup"]) { _ in refresh() } }
                    Button(tr("Restaurer cette copie")) { confirmRestore = true }.disabled(selected.isEmpty)
                    Button(tr("Ouvrir le dossier"), action: model.openSavedGames)
                }.disabled(model.supportRunning)
            }
            if model.supportRunning { ProgressView() }
            if !detail.isEmpty { Text(detail).font(.callout).foregroundStyle(.orange).textSelection(.enabled) }
            HStack { Spacer(); Button(tr("Fermer")) { model.showSupport = false }.disabled(model.supportRunning) }
        }.padding(28).frame(width: 680).preferredColorScheme(.dark).tint(.purple)
            .interactiveDismissDisabled(model.supportRunning)
            .onAppear { if model.supportReport { createReport() } else { refresh() } }
            .alert(tr("Restaurer cette copie ?"), isPresented: $confirmRestore) {
                Button(tr("Annuler"), role: .cancel) {}
                Button(tr("Restaurer cette copie")) {
                    run(["restore", "--id", selected]) { _ in detail = tr("Profil restauré. Le profil précédent a été conservé séparément.") }
                }
            } message: { Text(tr("La progression sera remplacée par cette copie. Le profil actuel sera conservé pour pouvoir revenir en arrière.")) }
    }
}
