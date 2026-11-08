import AppKit
import Carbon.HIToolbox
import SwiftUI

struct ControlsView: View {
    @ObservedObject var model: LauncherModel
    @Environment(\.dismiss) private var dismiss
    @State private var draft: ControlProfile
    @State private var device = 0
    @State private var capture: Int?
    @State private var unsupportedKey = false
    @State private var error: String?

    init(model: LauncherModel) {
        self.model = model
        _draft = State(initialValue: model.controls)
    }
    private func tr(_ key: String) -> String { model.tr(key) }
    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack {
                Text(tr("Modifier les commandes")).font(.title2)
                Spacer()
                Picker("", selection: $device) {
                    Text(tr("Clavier")).tag(0); Text(tr("Manette")).tag(1)
                }.pickerStyle(.segmented).frame(width: 230)
            }
            Text(tr("Les modifications s’appliquent au prochain lancement.")).font(.caption).foregroundStyle(.secondary)
            if device == 0 {
                HStack {
                    Button("AZERTY") { draft.keyboard = ControlProfile.azerty }
                    Button("QWERTY") { draft.useQwerty() }
                    Spacer()
                }
            } else {
                Text(tr("Les boutons sont indiqués par leur position sur la manette.")).font(.caption).foregroundStyle(.secondary)
            }
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    bindingsGroup("Boutons Xbox", range: 0..<12)
                    bindingsGroup("Croix directionnelle", range: 12..<16)
                    if device == 0 {
                        bindingsGroup("Touches de déplacement", range: 16..<20)
                        bindingsGroup("Touches de caméra", range: 20..<24)
                    } else {
                        ForEach(0..<2, id: \.self) { stick in
                            HStack {
                                Text(tr(stick == 0 ? "Stick gauche" : "Stick droit"))
                                Spacer()
                                Picker(tr("Source physique"), selection: Binding(get: { draft.sticks[stick] }, set: { draft.assignStick($0, to: stick) })) {
                                    Text(tr("Stick gauche")).tag(0)
                                    Text(tr("Stick droit")).tag(1)
                                    Text(tr("Non attribué")).tag(2)
                                }.labelsHidden().frame(width: 225)
                            }
                        }
                        Text(tr("Toutes les manettes utilisent ce profil.")).font(.caption).foregroundStyle(.secondary)
                        Text(tr("Le remappage ne change pas les indications de boutons dans le jeu."))
                            .font(.caption).foregroundStyle(.secondary)
                    }
                }.padding(.trailing, 10)
            }
            Text(tr("Attribuer une entrée déjà utilisée échange les deux commandes.")).font(.caption).foregroundStyle(.secondary)
            if let error { Text(error).font(.caption).foregroundStyle(.red) }
            if !draft.valid || model.controlsLoadFailed {
                Text(tr("Le profil de commandes est invalide. Restaure les valeurs d’origine ou corrige-le."))
                    .font(.caption).foregroundStyle(.orange)
            }
            HStack {
                Button(tr("Restaurer les valeurs d’origine")) { draft = ControlProfile(); error = nil }
                Spacer()
                Button(tr("Annuler")) { dismiss() }.keyboardShortcut(.cancelAction)
                Button(tr("Enregistrer")) {
                    do { try model.saveControls(draft); dismiss() }
                    catch { self.error = tr("Impossible d’enregistrer les commandes.") }
                }.buttonStyle(.borderedProminent).disabled(!draft.valid || model.busy)
            }
        }
        .padding(28).frame(width: 720, height: 650)
        .background(Color(red: 0.035, green: 0.015, blue: 0.075))
        .tint(Color(red: 0.71, green: 0.47, blue: 0.97))
        .preferredColorScheme(.dark)
        .sheet(isPresented: Binding(get: { capture != nil }, set: { if !$0 { capture = nil } })) {
            VStack(spacing: 18) {
                Text(tr("Appuie sur une touche")).font(.title2)
                if let capture { Text(tr(ControlProfile.names[capture])).foregroundStyle(.secondary) }
                Text(tr("Échap annule la saisie.")).foregroundStyle(.secondary)
                if unsupportedKey { Text(tr("Cette touche n’est pas prise en charge.")).font(.caption).foregroundStyle(.orange) }
                KeyCapture(completed: { key in
                    guard let control = capture else { return }
                    if let key { draft.assignKey(key, to: control) }
                    capture = nil
                }, rejected: { unsupportedKey = true })
                .frame(width: 280, height: 44)
                Button(tr("Annuler")) { capture = nil }.keyboardShortcut(.cancelAction)
            }.padding(32)
        }
    }
    private func bindingsGroup(_ name: String, range: Range<Int>) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(tr(name)).font(.headline).foregroundStyle(Color(red: 0.71, green: 0.47, blue: 0.97))
            ForEach(range, id: \.self) { row in
                HStack {
                    Text(tr(ControlProfile.names[row])).font(.system(size: 12))
                    Spacer()
                    if device == 0 {
                        Button(ControlProfile.keyName(draft.keyboard[row], tr: tr)) { unsupportedKey = false; capture = row }
                            .frame(width: 120)
                            .accessibilityLabel(tr(ControlProfile.names[row]) + ": " + ControlProfile.keyName(draft.keyboard[row], tr: tr))
                        Menu {
                            ForEach(ControlProfile.supportedKeys, id: \.self) { key in
                                Button(ControlProfile.keyName(key, tr: tr)) { draft.assignKey(key, to: row) }
                            }
                        } label: { Image(systemName: "chevron.down").accessibilityHidden(true) }
                        .menuStyle(.borderlessButton).menuIndicator(.hidden).frame(width: 23)
                        .accessibilityLabel(tr("Choisir une touche…")).help(tr("Choisir une touche…"))
                    } else {
                        Picker(tr("Source physique"), selection: Binding(get: { draft.pad[row] }, set: { draft.assignPad($0, to: row) })) {
                            ForEach(-1..<16, id: \.self) { source in
                                Text(ControlProfile.sourceName(source, tr: tr)).tag(source)
                            }
                        }.labelsHidden().frame(width: 225)
                    }
                }.padding(.vertical, 2)
            }
            Divider().padding(.top, 5)
        }
    }
}

private struct KeyCapture: NSViewRepresentable {
    var completed: (Int?) -> Void
    var rejected: () -> Void
    func makeNSView(context: Context) -> CaptureField {
        let field = CaptureField(); field.completed = completed; field.rejected = rejected; return field
    }
    func updateNSView(_ view: CaptureField, context: Context) { view.completed = completed; view.rejected = rejected }
}

private final class CaptureField: NSView {
    var completed: ((Int?) -> Void)?
    var rejected: (() -> Void)?
    private var modifier: Int?
    override var acceptsFirstResponder: Bool { true }
    override func viewDidMoveToWindow() {
        super.viewDidMoveToWindow()
        DispatchQueue.main.async { [weak self] in if let self { self.window?.makeFirstResponder(self) } }
    }
    override func keyDown(with event: NSEvent) {
        modifier = nil
        if event.keyCode == UInt16(kVK_Escape) { completed?(nil); return }
        guard !event.modifierFlags.contains(.command) else { rejected?(); return }
        let specials: [Int: Int] = [kVK_Return:13,kVK_ANSI_KeypadEnter:13,kVK_Tab:9,kVK_Space:32,
            kVK_Delete:8,kVK_ForwardDelete:46,kVK_LeftArrow:37,kVK_RightArrow:39,kVK_UpArrow:38,kVK_DownArrow:40,
            kVK_Home:36,kVK_End:35,kVK_PageUp:33,kVK_PageDown:34,
            kVK_F1:112,kVK_F2:113,kVK_F3:114,kVK_F4:115,kVK_F5:116,kVK_F6:117,
            kVK_F7:118,kVK_F8:119,kVK_F9:120,kVK_F10:121,kVK_F12:123,
            kVK_ANSI_Keypad0:96,kVK_ANSI_Keypad1:97,kVK_ANSI_Keypad2:98,kVK_ANSI_Keypad3:99,
            kVK_ANSI_Keypad4:100,kVK_ANSI_Keypad5:101,kVK_ANSI_Keypad6:102,kVK_ANSI_Keypad7:103,
            kVK_ANSI_Keypad8:104,kVK_ANSI_Keypad9:105,kVK_ANSI_KeypadMultiply:106,kVK_ANSI_KeypadPlus:107,
            kVK_ANSI_KeypadMinus:109,kVK_ANSI_KeypadDecimal:110,kVK_ANSI_KeypadDivide:111]
        if let key = specials[Int(event.keyCode)] { completed?(key); return }
        if let text = event.charactersIgnoringModifiers?.uppercased(), text.utf8.count == 1,
           let byte = text.utf8.first, (65...90).contains(byte) || (48...57).contains(byte) {
            completed?(Int(byte)); return
        }
        rejected?()
    }
    override func flagsChanged(with event: NSEvent) {
        if event.modifierFlags.contains(.shift) { modifier = 16 }
        else if event.modifierFlags.contains(.control) { modifier = 17 }
        else if event.modifierFlags.contains(.option) { modifier = 18 }
        else if let modifier { self.modifier = nil; completed?(modifier) }
    }
}
