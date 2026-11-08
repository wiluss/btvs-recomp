import Foundation

struct ControlProfile: Codable, Equatable {
    var version = 1
    var keyboard = Self.azerty
    var pad = Array(0..<16)
    var sticks = [0, 1]
    static let azerty = [87,88,67,86,65,69,49,51,13,8,16,17,38,40,37,39,90,83,81,68,73,75,74,76]
    static let supportedKeys: [Int] = ([0,8,9,13,16,17,18,27,45,46] + Array(32...40) + Array(48...57)
        + Array(65...90) + Array(96...107) + Array(109...123)).filter { $0 != 122 }.sorted()
    static let names = ["A","B","X","Y","Blanc","Noir","Gâchette gauche","Gâchette droite",
                        "Start","Back","Clic du stick gauche","Clic du stick droit","↑","↓","←","→",
                        "Haut","Bas","Gauche","Droite","Haut","Bas","Gauche","Droite"]

    var valid: Bool {
        guard version == 1, keyboard.count == 24, pad.count == 16, sticks.count == 2,
              keyboard.allSatisfy({ Self.supportedKeys.contains($0) }),
              pad.allSatisfy({ (-1...15).contains($0) }), sticks.allSatisfy({ (0...2).contains($0) }) else { return false }
        let keys = keyboard.filter { $0 != 0 }, sources = pad.filter { $0 >= 0 }
        return Set(keys).count == keys.count && Set(sources).count == sources.count
            && [0,1,8].allSatisfy { keyboard[$0] != 0 || pad[$0] >= 0 }
    }
    static func load(_ url: URL) throws -> ControlProfile {
        let data = try Data(contentsOf: url)
        guard let text = String(data: data, encoding: .utf8),
              ["version", "keyboard", "pad", "sticks"].allSatisfy({ name in
                  text.components(separatedBy: "\"" + name + "\"").count == 2
              }) else { throw CocoaError(.fileReadCorruptFile) }
        guard data.count <= 8192,
              let fields = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              Set(fields.keys) == Set(["version","keyboard","pad","sticks"]) else { throw CocoaError(.fileReadCorruptFile) }
        let profile = try JSONDecoder().decode(ControlProfile.self, from: data)
        guard profile.valid else { throw CocoaError(.fileReadCorruptFile) }
        return profile
    }
    mutating func assignKey(_ key: Int, to control: Int) {
        guard keyboard.indices.contains(control), Self.supportedKeys.contains(key) else { return }
        let old = keyboard[control]
        if key != 0, let other = keyboard.firstIndex(of: key), other != control { keyboard[other] = old }
        keyboard[control] = key
    }
    mutating func assignPad(_ source: Int, to control: Int) {
        guard pad.indices.contains(control), (-1...15).contains(source) else { return }
        let old = pad[control]
        if source >= 0, let other = pad.firstIndex(of: source), other != control { pad[other] = old }
        pad[control] = source
    }
    mutating func assignStick(_ source: Int, to control: Int) {
        guard sticks.indices.contains(control), (0...2).contains(source) else { return }
        let other = 1 - control, old = sticks[control]
        if source != 2 && sticks[other] == source { sticks[other] = old }
        sticks[control] = source
    }
    mutating func useQwerty() {
        keyboard = Self.azerty
        keyboard[0] = 90; keyboard[4] = 81; keyboard[16] = 87; keyboard[18] = 65
    }
    static func keyName(_ key: Int, tr: (String) -> String) -> String {
        if key == 0 { return tr("Non attribué") }
        if (48...57).contains(key) || (65...90).contains(key) { return String(UnicodeScalar(key)!) }
        if (96...105).contains(key) { return "KP \(key - 96)" }
        if (112...123).contains(key) { return "F\(key - 111)" }
        let names = [8:"⌫",9:"Tab",13:"↩",16:"Maj",17:"Ctrl",18:"Alt",27:"Échap",32:"Espace",
                     33:"⇞",34:"⇟",35:"↘",36:"↖",37:"←",38:"↑",39:"→",40:"↓",45:"Insert",
                     46:"Suppr",106:"KP ×",107:"KP +",109:"KP −",110:"KP .",111:"KP /"]
        return tr(names[key] ?? "Non attribué")
    }
    static func sourceName(_ source: Int, tr: (String) -> String) -> String {
        switch source {
        case -1: return tr("Non attribué")
        case 0: return tr("Bas") + " · A / ×"
        case 1: return tr("Droite") + " · B / ○"
        case 2: return tr("Gauche") + " · X / □"
        case 3: return tr("Haut") + " · Y / △"
        default:
            let names = ["LB / L1","RB / R1","LT / L2","RT / R2","Menu / Start","View / Select","L3","R3","↑","↓","←","→"]
            return (4...15).contains(source) ? names[source-4] : tr("Non attribué")
        }
    }
}
