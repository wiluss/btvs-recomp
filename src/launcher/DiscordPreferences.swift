import Foundation

struct DiscordPreferences: Codable, Equatable {
    var enabled = false
    var applicationID = ""
    enum CodingKeys: String, CodingKey { case enabled; case applicationID = "application_id" }

    var validID: Bool {
        (17...20).contains(applicationID.utf8.count)
            && applicationID.first != "0"
            && applicationID.utf8.allSatisfy { (48...57).contains($0) }
            && UInt64(applicationID) != nil
    }

    private static func read(_ url: URL) throws -> Data {
        let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
        guard attributes[.type] as? FileAttributeType == .typeRegular,
              (attributes[.size] as? NSNumber)?.intValue ?? 4097 <= 4096 else {
            throw CocoaError(.fileReadCorruptFile)
        }
        return try Data(contentsOf: url)
    }

    static func load(root: URL) throws -> DiscordPreferences {
        var result = DiscordPreferences()
        let common = root.appendingPathComponent("config/discord.json")
        if FileManager.default.fileExists(atPath: common.path) {
            let raw = try JSONSerialization.jsonObject(with: read(common)) as? [String: String]
            result.applicationID = raw?["application_id"] ?? ""
        }
        let local = root.appendingPathComponent("private/config/discord.json")
        if FileManager.default.fileExists(atPath: local.path) {
            let saved = try JSONDecoder().decode(DiscordPreferences.self, from: read(local))
            result.enabled = saved.enabled
            if !saved.applicationID.isEmpty { result.applicationID = saved.applicationID }
        }
        guard result.applicationID.isEmpty || result.validID else { throw CocoaError(.fileReadCorruptFile) }
        return result
    }

    func save(root: URL) throws {
        guard (applicationID.isEmpty && !enabled) || validID else { throw CocoaError(.fileWriteInvalidFileName) }
        let url = root.appendingPathComponent("private/config/discord.json")
        try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        try JSONEncoder().encode(self).write(to: url, options: .atomic)
    }
}
