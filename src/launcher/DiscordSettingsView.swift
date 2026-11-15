import SwiftUI

struct DiscordSettingsView: View {
    @ObservedObject var model: LauncherModel
    @State private var error: String?
    private func tr(_ key: String) -> String { model.tr(key) }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Toggle(tr("Présence Discord"), isOn: Binding(
                get: { model.discord.enabled },
                set: { value in
                    var settings = model.discord; settings.enabled = value
                    save(settings)
                }))
                .disabled(!model.discord.validID)
            Text(tr("Affiche le niveau actuel et le temps de session. Discord doit être ouvert."))
                .font(.system(size: 11)).foregroundStyle(.secondary)
            Text(tr(model.discord.validID ? "Modifications appliquées au prochain lancement." : "Présence Discord indisponible."))
                .font(.system(size: 11)).foregroundStyle(.secondary)
            if let error { Text(error).font(.system(size: 11)).foregroundStyle(.red) }
        }
    }

    private func save(_ settings: DiscordPreferences) {
        do {
            try model.saveDiscord(settings)
            error = nil
        } catch { self.error = tr("Impossible d’enregistrer les préférences Discord.") }
    }
}
