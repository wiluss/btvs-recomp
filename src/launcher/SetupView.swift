import SwiftUI

struct SetupView: View {
    @ObservedObject var model: LauncherModel
    private func tr(_ key: String) -> String { model.tr(key) }

    var body: some View {
        VStack(alignment: .leading, spacing: 22) {
            Text(tr("Préparer Buffy")).font(.title)
            Text(tr("Choisis l’ISO de ton exemplaire. Le jeu sera préparé sur ce Mac."))
                .foregroundStyle(.secondary)
            HStack {
                Image(systemName: "opticaldisc").font(.system(size: 28)).foregroundStyle(.purple)
                Text(model.setupISO?.lastPathComponent ?? tr("Aucune ISO sélectionnée"))
                    .lineLimit(2).frame(maxWidth: .infinity, alignment: .leading)
                Button(tr("Choisir une ISO…")) { model.chooseISO() }.disabled(model.setupRunning)
            }.padding(18).background(.white.opacity(0.045), in: RoundedRectangle(cornerRadius: 12))
            Text(tr("Les fichiers du jeu restent locaux. Ton ISO et tes sauvegardes sont conservées."))
                .font(.caption).foregroundStyle(.secondary)
            if model.setupRunning {
                if let value = model.setupFraction { ProgressView(value: value) }
                else { ProgressView().progressViewStyle(.linear) }
                Text(model.tr(model.setupStage)).font(.callout)
            } else if model.setupComplete {
                Label(tr("Jeu préparé. Tu peux maintenant le lancer."), systemImage: "checkmark.circle")
                    .foregroundStyle(.green)
            } else if model.setupFailed {
                Text(tr("La préparation a échoué. Consulte le journal pour les détails."))
                    .foregroundStyle(.orange)
            } else {
                Text(tr("La première préparation peut prendre plusieurs minutes. Les outils nécessaires doivent être installés."))
                    .font(.caption).foregroundStyle(.secondary)
            }
            Spacer(minLength: 0)
            HStack {
                Button(tr("Guide d’installation")) { model.openPreparationGuide() }
                if model.setupFailed {
                    Button(tr("Journal de session")) { model.showSetup = false; model.showJournal = true }
                }
                Spacer()
                if model.setupRunning {
                    Button(tr("Annuler")) { model.stop() }
                } else {
                    Button(tr("Fermer")) { model.showSetup = false }.keyboardShortcut(.cancelAction)
                    if !model.setupComplete {
                        Button(tr("Préparer le jeu")) { model.prepareGame() }
                            .buttonStyle(.borderedProminent).disabled(model.setupISO == nil)
                    }
                }
            }
        }.padding(30).frame(width: 660, height: 400)
            .background(Color(red: 0.035, green: 0.015, blue: 0.075))
            .tint(Color(red: 0.71, green: 0.47, blue: 0.97)).preferredColorScheme(.dark)
            .interactiveDismissDisabled(model.setupRunning)
    }
}
