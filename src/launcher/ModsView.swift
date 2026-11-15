import AppKit
import SwiftUI
import ImageIO
import UniformTypeIdentifiers

struct InstalledMod: Identifiable {
    let id: String
    let name: String
    let author: String
    let detail: String
    let preview: URL?
    let entries: Int
    let bytes: Int64
}

@MainActor
enum ModService {
    static func run(root: URL, arguments: [String], completion: @escaping ([String: Any]?, String?) -> Void) {
        let task = Process(), pipe = Pipe()
        task.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        task.arguments = [root.appendingPathComponent("src/launcher/mod_library.py").path] + arguments + ["--root", root.path]
        task.currentDirectoryURL = root; task.standardOutput = pipe; task.standardError = pipe
        do { try task.run() } catch { completion(nil,error.localizedDescription); return }
        Task.detached {
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            task.waitUntilExit()
            let output = String(decoding: data, as: UTF8.self)
            await MainActor.run {
                let row = output.split(separator: "\n").last.flatMap { try? JSONSerialization.jsonObject(with: Data($0.utf8)) as? [String: Any] }
                guard task.terminationStatus == 0, let row else {
                    completion(nil, row?["error"] as? String ?? (output.isEmpty ? "Invalid mod helper response" : output)); return
                }
                completion(row, nil)
            }
        }
    }
}

extension LauncherModel {
    func modAction(_ arguments: [String]) {
        guard !busy else { return }
        modsRunning = true; modError = nil
        ModService.run(root: root, arguments: arguments) { row, error in
            self.modsRunning = false
            if let error { self.modError = error; return }
            self.activeMod = row?["active"] as? String
            self.installedMods = (row?["mods"] as? [[String: Any]] ?? []).compactMap { item in
                guard let id = item["id"] as? String, let name = item["name"] as? String,
                      let count = item["entries"] as? Int, let size = item["bytes"] as? Int64 else { return nil }
                return InstalledMod(id: id, name: name, author: item["author"] as? String ?? "",
                                    detail: item["description"] as? String ?? "",
                                    preview: (item["preview"] as? String).map { URL(fileURLWithPath: $0) }, entries: count, bytes: size)
            }
        }
    }

    func prepareModsAndLaunch() {
        guard !busy else { return }
        modsRunning = true
        ModService.run(root: root, arguments: ["wardrobe", "--textures", settings.texturesHD ? "campaign2x" : "original", "--text", settings.textHD ? "hd" : "original"]) { row, error in
            self.modsRunning = false
            if let error { self.modError = error; self.preferencesError = error; return }
            let pack = (row?["pack"] as? String).map { URL(fileURLWithPath: $0) }
            self.startGame(modPack: pack, wardrobe: row?["catalog"] as? String, wardrobePrefs: row?["preferences"] as? String)
        }
    }
}

struct SkinThumbnail: View {
    let url: URL?
    let placeholder: String
    @State private var image: NSImage?
    var body: some View {
        ZStack {
            Color.black.opacity(0.25)
            if let image { Image(nsImage: image).resizable().scaledToFit() }
            else {
                VStack(spacing: 10) {
                    Image(systemName: "tshirt").font(.system(size: 32))
                    Text(placeholder).font(.caption)
                }.foregroundStyle(.secondary)
            }
        }.task(id: url) {
            image = nil
            guard let url, let values = try? url.resourceValues(forKeys: [.fileSizeKey]),
                  let size = values.fileSize, size <= 8 * 1024 * 1024,
                  let source = CGImageSourceCreateWithURL(url as CFURL, nil),
                  let thumb = CGImageSourceCreateThumbnailAtIndex(source, 0, [
                    kCGImageSourceCreateThumbnailFromImageAlways: true,
                    kCGImageSourceThumbnailMaxPixelSize: 720,
                    kCGImageSourceCreateThumbnailWithTransform: true
                  ] as CFDictionary) else { return }
            image = NSImage(cgImage: thumb, size: .zero)
        }
    }
}

struct ModsView: View {
    @ObservedObject var model: LauncherModel
    private func tr(_ key: String) -> String { model.tr(key) }
    private func choosePreview(_ mod: InstalledMod) {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.png]; panel.allowsMultipleSelection = false
        panel.message = tr("Choisir une capture de cette tenue")
        if panel.runModal() == .OK, let url = panel.url {
            model.modAction(["preview", "--id", mod.id, "--file", url.path])
        }
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(tr("Importe un skin .xrtp avec son .json. Ajoute une capture PNG pour reconnaître chaque tenue."))
                .font(.system(size: 12)).foregroundStyle(.secondary)
            HStack {
                Button(tr("Importer un skin…"), action: model.choosePack)
                Button(tr("Guide des skins")) { NSWorkspace.shared.open(model.root.appendingPathComponent("docs/MODS.md")) }
                if model.modsRunning { ProgressView().controlSize(.small) }
            }
            Button { model.modAction(["disable"]) } label: {
                HStack {
                    Image(systemName: model.activeMod == nil ? "checkmark.circle.fill" : "circle")
                    VStack(alignment: .leading) {
                        Text(tr("Tenue d’origine"))
                        Text(tr("Le jeu choisit la tenue prévue pour le niveau.")).font(.caption).foregroundStyle(.secondary)
                    }
                    Spacer()
                }.padding(12).background(Color.purple.opacity(0.10), in: RoundedRectangle(cornerRadius: 8))
            }.buttonStyle(.plain)
            if model.installedMods.isEmpty { Text(tr("Aucun skin importé")).foregroundStyle(.secondary) }
            LazyVGrid(columns: [GridItem(.adaptive(minimum: 230, maximum: 360))], alignment: .leading, spacing: 16) {
                ForEach(model.installedMods) { mod in
                    VStack(alignment: .leading, spacing: 10) {
                        SkinThumbnail(url: mod.preview, placeholder: tr("Capture à ajouter"))
                            .frame(height: 165).clipShape(RoundedRectangle(cornerRadius: 7))
                            .accessibilityLabel(tr("Aperçu de la tenue") + " · " + mod.name)
                        HStack {
                            Text(mod.name).font(.system(size: 14, weight: .semibold)).lineLimit(2)
                            Spacer()
                            if model.activeMod == mod.id { Label(tr("Sélectionnée"), systemImage: "checkmark.circle.fill").font(.caption).foregroundStyle(.purple) }
                        }
                        if !mod.author.isEmpty { Text(mod.author).font(.caption).foregroundStyle(.secondary) }
                        if !mod.detail.isEmpty { Text(mod.detail).font(.caption).foregroundStyle(.secondary).lineLimit(3) }
                        HStack {
                            Button(tr(model.activeMod == mod.id ? "Désactiver" : "Porter cette tenue")) {
                                model.modAction(model.activeMod == mod.id ? ["disable"] : ["activate", "--id", mod.id])
                            }
                            Spacer()
                            Button { choosePreview(mod) } label: { Image(systemName: "photo.badge.plus") }
                                .help(tr("Ajouter ou remplacer la capture"))
                                .accessibilityLabel(tr("Ajouter ou remplacer la capture") + " · " + mod.name)
                        }
                    }.padding(12).background(Color.purple.opacity(model.activeMod == mod.id ? 0.20 : 0.08), in: RoundedRectangle(cornerRadius: 10))
                }
            }
            if let error = model.modError { Text(error).foregroundStyle(.orange).font(.callout).textSelection(.enabled) }
            Text(tr("En jeu : F8 ouvre la garde-robe. Mets d’abord le jeu en pause."))
                .font(.system(size: 11)).foregroundStyle(.secondary)
        }.onAppear { model.modAction(["list"]) }
    }
}
