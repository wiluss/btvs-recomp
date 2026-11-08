import AppKit
import SwiftUI

private enum LauncherPage { case home, settings, packs }
private enum HomeItem: Int, CaseIterable { case play, options, packs }
private enum Theme {
    static let violet = Color(red: 0.71, green: 0.47, blue: 0.97)
    static let muted = Color(red: 0.68, green: 0.61, blue: 0.79)
    static let ink = Color(red: 0.022, green: 0.008, blue: 0.060)
}

struct LauncherView: View {
    @ObservedObject var model: LauncherModel
    @State private var page = LauncherPage.home
    @State private var droppingPack = false
    @FocusState private var homeFocus: HomeItem?
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private func tr(_ key: String) -> String { model.tr(key) }

    private func gameFont(_ size: CGFloat) -> Font {
        model.decorativeFontAvailable ? .custom("BuffyDecorative-Regular", size: size)
            : .system(size: size, design: .serif)
    }

    var body: some View {
        ZStack {
            MistBackdrop(mist: model.mist, veil: model.veil, gameRunning: model.busy)
            VStack(spacing: 0) {
                topbar
                Group {
                    if page == .home { home }
                    else {
                        ScrollView {
                            VStack(spacing: 26) {
                                heading(page == .settings ? tr("Options") : tr("Packs & skins"))
                                if page == .settings { settings } else { packs }
                            }.padding(.horizontal, 70).padding(.top, 18).padding(.bottom, 35)
                        }
                    }
                }.id(page).transition(.opacity)
                footer
            }
        }
        .frame(minWidth: 900, minHeight: 690)
        .foregroundStyle(Color(red: 0.94, green: 0.86, blue: 1))
        .preferredColorScheme(.dark).tint(Theme.violet)
        .environment(\.locale, Locale(identifier: model.language.rawValue))
        .sheet(isPresented: $model.showJournal) { journal }
        .sheet(isPresented: $model.showControls) { ControlsView(model: model) }
        .sheet(isPresented: $model.showSetup) { SetupView(model: model) }
        .alert(tr("Erreur"), isPresented: Binding(get: { model.preferencesError != nil }, set: { if !$0 { model.preferencesError = nil } })) {
            Button("OK") { model.preferencesError = nil }
        } message: { Text(model.preferencesError ?? "") }
        .onExitCommand { if page != .home { navigate(.home) } }
    }

    private func navigate(_ destination: LauncherPage) {
        homeFocus = nil
        withAnimation(reduceMotion ? nil : .easeOut(duration: 0.18)) { page = destination }
    }

    private var topbar: some View {
        HStack {
            if page != .home {
                Button { navigate(.home) } label: {
                    Label(tr("Accueil"), systemImage: "chevron.left").font(.system(size: 12))
                }.buttonStyle(.plain).foregroundStyle(Theme.muted)
                    .keyboardShortcut(.cancelAction)
            }
            Spacer()
        }.frame(height: 28).padding(.horizontal, 30).padding(.top, 18)
    }

    private var home: some View {
        VStack(spacing: 0) {
            Spacer(minLength: 0)
            if let logo = model.logo {
                Image(nsImage: logo).resizable().interpolation(.high).scaledToFit().colorInvert()
                    .frame(maxWidth: 560).frame(height: 310)
                    .shadow(color: Theme.violet.opacity(0.2), radius: 25)
                    .accessibilityLabel("btvs-recomp")
            } else {
                VStack(spacing: 10) {
                    Text("btvs-recomp").font(.system(size: 60, design: .serif))
                    Text("Buffy · Xbox · 2002").font(gameFont(23))
                }.frame(height: 310).accessibilityElement(children: .combine)
            }
            Spacer(minLength: 10).frame(maxHeight: 28)
            menuButton(model.busy ? tr("Arrêter") : tr("Jouer"), item: .play, primary: true,
                       enabled: model.busy || model.localInstallationDetected) {
                model.busy ? model.stop() : model.launch()
            }
            menuButton(tr("Options"), item: .options) { navigate(.settings) }.padding(.top, 11)
            menuButton(tr("Packs & skins"), item: .packs) { navigate(.packs) }.padding(.top, 2)
            Spacer(minLength: 10).frame(maxHeight: 28)
            if model.controlsLoadFailed {
                Text(tr("Le profil de commandes est invalide. Restaure les valeurs d’origine ou corrige-le."))
                    .font(.system(size: 11)).foregroundStyle(.orange)
            } else if model.localInstallationDetected {
                Text(tr("Retrouve ta partie avec Load Game dans le menu du jeu."))
                    .font(.system(size: 11)).foregroundStyle(Theme.muted)
            } else {
                Text(tr("Prépare le jeu à partir de ton exemplaire pour commencer."))
                    .font(.system(size: 12)).foregroundStyle(Theme.muted)
                Button(tr("Préparer depuis une ISO…")) { model.showSetup = true }
                    .buttonStyle(.plain).foregroundStyle(Theme.violet).padding(.top, 10)
            }
            Spacer(minLength: 18)
        }.frame(maxWidth: .infinity)
            .onAppear { homeFocus = model.running || model.localInstallationDetected ? .play : .options }
            .onMoveCommand { direction in
                guard !model.showJournal, !model.showControls, !model.showSetup else { return }
                let current = homeFocus?.rawValue ?? 0
                switch direction {
                case .down: homeFocus = HomeItem(rawValue: (current + 1) % HomeItem.allCases.count)
                case .up: homeFocus = HomeItem(rawValue: (current + HomeItem.allCases.count - 1) % HomeItem.allCases.count)
                default: break
                }
            }
    }

    private func menuButton(_ title: String, item: HomeItem, primary: Bool = false, enabled: Bool = true,
                            action: @escaping () -> Void) -> some View {
        Button(action: action) {
            ZStack {
                if primary {
                    Ellipse().fill(Theme.violet.opacity(0.24)).frame(width: 260, height: 39).blur(radius: 16)
                    OrnamentalLine().stroke(Theme.violet.opacity(0.6), lineWidth: 1)
                        .frame(width: 360, height: 6).offset(y: 31)
                }
                Text(title).font(gameFont(primary ? 39 : 25))
                    .shadow(color: Theme.violet.opacity(primary ? 0.95 : 0.4), radius: primary ? 9 : 3)
                    .foregroundStyle(primary ? Color.white : Color(red: 0.75, green: 0.60, blue: 0.92))
            }
            .frame(width: 390, height: primary ? 72 : 45).contentShape(Rectangle())
        }.buttonStyle(MenuStyle(keyboardFocus: homeFocus == item, primary: primary))
            .focused($homeFocus, equals: item)
            .keyboardShortcut((homeFocus == item || (homeFocus == nil && item == .play)) ? .defaultAction : nil)
            .disabled(!enabled).opacity(enabled ? 1 : 0.4)
    }

    private func heading(_ title: String) -> some View {
        HStack(spacing: 22) {
            OrnamentalLine().stroke(Theme.violet.opacity(0.65), lineWidth: 1).frame(height: 7)
            Text(title).font(gameFont(30)).fixedSize()
                .shadow(color: Theme.violet, radius: 9)
            OrnamentalLine().stroke(Theme.violet.opacity(0.65), lineWidth: 1)
                .rotationEffect(.degrees(180)).frame(height: 7)
        }.padding(.bottom, 8)
    }

    private var settings: some View {
        HStack(alignment: .top, spacing: 24) {
            section(tr("Image")) {
                Picker(tr("Résolution"), selection: $model.settings.uhd) {
                    Text(tr("Facteur de rendu")).tag(false); Text("4K UHD").tag(true)
                }.pickerStyle(.segmented)
                Picker(tr("Définition"), selection: $model.settings.scale) {
                    ForEach(1...4, id: \.self) { Text("\($0)×").tag($0) }
                }.pickerStyle(.segmented).disabled(model.settings.uhd)
                HStack {
                    Text(model.gameResolution).font(.system(size: 12, weight: .medium, design: .monospaced))
                    Spacer()
                    Text(model.settings.uhd || model.settings.widescreen ? "16:9" : "4:3")
                        .font(.system(size: 10, weight: .medium)).padding(.horizontal, 8).padding(.vertical, 4)
                        .background(Theme.violet.opacity(0.12), in: Capsule())
                }.foregroundStyle(Theme.muted)
                Toggle(tr("Format 16:9"), isOn: $model.settings.widescreen).disabled(model.settings.uhd)
                Toggle(tr("Plein écran"), isOn: $model.settings.fullscreen)
            }
            section(tr("Confort")) {
                Toggle(tr("Synchronisation verticale"), isOn: $model.settings.vsync)
                Toggle(tr("Compteur FPS"), isOn: $model.settings.fps)
                Divider().overlay(Theme.violet.opacity(0.15))
                Toggle(tr("Textures HD"), isOn: $model.settings.texturesHD)
                    .disabled(!model.campaignAvailable || model.settings.customPack != nil)
                Toggle(tr("Textes HD"), isOn: $model.settings.textHD)
                    .disabled(!model.textAvailable)
                if !model.campaignAvailable {
                    Text(tr("Le pack HD n’est pas installé sur ce Mac."))
                        .font(.system(size: 11)).foregroundStyle(Theme.muted)
                }
            }
        }.disabled(model.busy)
    }

    private var packs: some View {
        VStack(spacing: 24) {
            section(tr("Pack HD")) {
                Text(tr("Textures, HUD et textes HD, avec les retouches manuelles."))
                    .font(.system(size: 12)).foregroundStyle(Theme.muted)
                HStack {
                    Button(tr("Télécharger le pack HD…"), action: model.openHDDownload)
                    Button(tr("Installer le pack HD…"), action: model.chooseHDArchive)
                        .disabled(!model.localInstallationDetected)
                    if model.hdRunning { ProgressView().controlSize(.small) }
                }
                if !model.hdStatus.isEmpty {
                    Text(tr(model.hdStatus)).font(.system(size: 11)).foregroundStyle(Theme.muted)
                } else {
                    Text(model.campaignAvailable ? tr("Pack HD disponible") : tr("Installe le jeu, puis sélectionne le ZIP HD téléchargé."))
                        .font(.system(size: 11)).foregroundStyle(Theme.muted)
                }
            }
            section(tr("Pack personnel")) {
                HStack(spacing: 20) {
                    Image(systemName: "square.stack.3d.up").font(.system(size: 26)).foregroundStyle(Theme.violet)
                    VStack(alignment: .leading, spacing: 8) {
                        Text(model.settings.customPack?.lastPathComponent ?? tr("Aucun pack sélectionné"))
                            .font(.system(size: 13, weight: .medium)).lineLimit(1).truncationMode(.middle)
                        Text(model.settings.customPack == nil ? tr("Glisse un pack .xrtp ici, ou choisis un fichier.")
                             : tr("Sélectionné pour le prochain lancement."))
                            .font(.system(size: 12)).foregroundStyle(Theme.muted)
                    }
                    Spacer()
                    Button(tr("Choisir…"), action: model.choosePack)
                    if model.settings.customPack != nil { Button(tr("Retirer")) { model.settings.customPack = nil } }
                }
            }
            .overlay(RoundedRectangle(cornerRadius: 9).strokeBorder(Theme.violet.opacity(droppingPack ? 0.85 : 0), lineWidth: 2))
            .dropDestination(for: URL.self) { urls, _ in model.selectPack(urls) }
                isTargeted: { droppingPack = $0 && !model.running }
            section(tr("Extras")) {
                Toggle(tr("Rendre les quatre arènes accessibles"), isOn: $model.settings.arenas)
                Text(tr("Disponibles dans Extras depuis le menu du jeu."))
                    .font(.system(size: 11)).foregroundStyle(Theme.muted)
            }
        }.disabled(model.busy)
    }

    private var footer: some View {
        HStack(spacing: 20) {
            Button { model.showControls = true } label: {
                Label(tr("Commandes"), systemImage: "gamecontroller")
            }.buttonStyle(.plain).disabled(model.busy)
            Button(action: model.openSavedGames) {
                Label(tr("Sauvegardes"), systemImage: "folder")
            }.buttonStyle(.plain)
            Menu {
                Picker(tr("Langue"), selection: $model.language) {
                    ForEach(LauncherLanguage.allCases) { language in Text(language.name).tag(language) }
                }
            } label: {
                Label(model.language.rawValue.uppercased(), systemImage: "globe")
            }.menuStyle(.borderlessButton).frame(width: 66).help(tr("Langue"))
            Spacer()
            if model.running || model.launchFailed || !model.transcript.isEmpty {
                Button { model.showJournal = true } label: {
                    Text(model.status).lineLimit(1)
                }.buttonStyle(.plain).help(tr("Afficher le journal de session"))
            }
            if page != .home {
                Button(model.running ? tr("Arrêter") : tr("Jouer"), action: model.running ? model.stop : model.launch)
                    .buttonStyle(.bordered).disabled(!model.running && !model.localInstallationDetected)
            }
        }
        .font(.system(size: 11)).foregroundStyle(Theme.muted)
        .padding(.horizontal, 30).padding(.vertical, 20)
    }

    private var journal: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack {
                Text(tr("Journal de session")).font(.title2)
                Spacer()
                Button(tr("Copier"), action: model.copyJournal).disabled(model.transcript.isEmpty)
                Button(tr("Fermer")) { model.showJournal = false }.keyboardShortcut(.cancelAction)
            }
            ScrollView {
                Text(model.transcript.isEmpty ? tr("Aucune session lancée depuis l’ouverture du lanceur.") : model.transcript)
                    .font(.system(size: 11, design: .monospaced)).textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }.padding(28).frame(width: 700, height: 420).background(Theme.ink)
    }

    private func section<Content: View>(_ title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 20) {
            Text(title).font(gameFont(23)).foregroundStyle(Theme.violet)
            Divider().overlay(Theme.violet.opacity(0.2))
            content()
        }.padding(24).frame(maxWidth: .infinity, alignment: .leading)
            .background(Theme.ink.opacity(0.76), in: RoundedRectangle(cornerRadius: 9))
            .overlay(RoundedRectangle(cornerRadius: 9).strokeBorder(Theme.violet.opacity(0.16)))
            .toggleStyle(.switch)
    }
}

private struct MenuStyle: ButtonStyle {
    var keyboardFocus: Bool
    var primary: Bool
    func makeBody(configuration: Configuration) -> some View {
        MenuSurface(label: configuration.label, keyboardFocus: keyboardFocus,
                    primary: primary, pressed: configuration.isPressed)
    }
}

private struct MenuSurface<Label: View>: View {
    let label: Label
    let keyboardFocus: Bool
    let primary: Bool
    let pressed: Bool
    @State private var hovering = false
    @Environment(\.isEnabled) private var enabled
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    private var lit: Bool { enabled && (hovering || keyboardFocus) }

    var body: some View {
        label
            .background {
                Ellipse().fill(Theme.violet.opacity(lit ? 0.19 : 0))
                    .frame(width: primary ? 300 : 240, height: 26).blur(radius: 16)
            }
            .overlay(alignment: .leading) {
                Image(systemName: "diamond.fill").font(.system(size: 6))
                    .foregroundStyle(Theme.violet).padding(.leading, 27).opacity(lit ? 1 : 0)
                    .accessibilityHidden(true)
            }
            .shadow(color: Theme.violet.opacity(lit ? 0.6 : 0), radius: 8)
            .opacity(pressed ? 0.65 : 1)
            .scaleEffect(reduceMotion ? 1 : pressed ? 0.98 : lit ? 1.025 : 1)
            .animation(reduceMotion ? nil : .easeOut(duration: 0.16), value: lit)
            .animation(reduceMotion ? nil : .easeOut(duration: 0.1), value: pressed)
            .onHover { hovering = $0 }
    }
}

/// Low-frequency texture drift, paused while playing or when the app is inactive.
private struct MistBackdrop: View {
    let mist: NSImage?
    let veil: NSImage?
    let gameRunning: Bool
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        TimelineView(.animation(minimumInterval: 0.1, paused: gameRunning || scenePhase != .active || reduceMotion)) { context in
            let phase = reduceMotion ? 0 : context.date.timeIntervalSinceReferenceDate / 28
            GeometryReader { geometry in
                ZStack {
                    Theme.ink
                    if let mist {
                        Image(nsImage: mist).resizable().interpolation(.high).scaledToFill()
                            .frame(width: geometry.size.width + 80, height: geometry.size.height + 80)
                            .offset(x: sin(phase) * 14, y: cos(phase) * 10).opacity(0.46)
                    }
                    if let veil {
                        Image(nsImage: veil).resizable().interpolation(.high).scaledToFill()
                            .frame(width: geometry.size.width + 80, height: geometry.size.height + 80)
                            .offset(x: cos(phase * 0.7) * 22, y: sin(phase * 0.7) * 12).opacity(0.07)
                    }
                    RadialGradient(colors: [.clear, Theme.ink.opacity(0.9)], center: .center,
                                   startRadius: 70, endRadius: geometry.size.width * 0.67)
                    LinearGradient(colors: [Theme.ink.opacity(0.7), .clear, Theme.ink.opacity(0.8)],
                                   startPoint: .top, endPoint: .bottom)
                }.frame(width: geometry.size.width, height: geometry.size.height).clipped()
            }
        }.ignoresSafeArea().accessibilityHidden(true).allowsHitTesting(false)
    }
}

/// Spear-shaped divider echoing the game's menu layout, drawn without assets.
private struct OrnamentalLine: Shape {
    func path(in rect: CGRect) -> Path {
        var p = Path()
        p.move(to: CGPoint(x: 0, y: rect.midY))
        p.addLine(to: CGPoint(x: rect.maxX, y: rect.midY))
        p.move(to: CGPoint(x: rect.width * 0.06, y: rect.midY))
        p.addLine(to: CGPoint(x: rect.width * 0.12, y: 0))
        p.addLine(to: CGPoint(x: rect.width * 0.66, y: rect.midY))
        p.addLine(to: CGPoint(x: rect.width * 0.12, y: rect.maxY))
        p.closeSubpath()
        return p
    }
}
