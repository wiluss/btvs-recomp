import Foundation

enum LauncherLanguage: String, Codable, CaseIterable, Identifiable {
    case fr, en, es, de, it
    var id: String { rawValue }
    var name: String {
        switch self {
        case .fr: return "Français"
        case .en: return "English"
        case .es: return "Español"
        case .de: return "Deutsch"
        case .it: return "Italiano"
        }
    }
    static var system: LauncherLanguage {
        for tag in Locale.preferredLanguages {
            if let value = LauncherLanguage(rawValue: String(tag.prefix(2)).lowercased()) { return value }
        }
        return .en
    }
}

enum LauncherText {
    static let catalog: [String: [String: String]] = {
        guard let url = Bundle.main.url(forResource: "Localizations", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let table = try? JSONDecoder().decode([String: [String: String]].self, from: data) else { return [:] }
        return table
    }()
    static func text(_ key: String, language: LauncherLanguage) -> String {
        catalog[language.rawValue]?[key] ?? catalog["fr"]?[key] ?? key
    }
}
