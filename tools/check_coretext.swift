// Native macOS checks. Registers one local candidate at a time, process scope only.
// Does not install in Font Book, ~/Library/Fonts, or the system font directory.
import Foundation
import CoreText
import AppKit

let root = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
let out = root.appendingPathComponent(".release-work")
let samples = ["Build a brighter tomorrow.", "Ideas ship farther.", "Zayju  zayju.de", "a g r y z 1 0", "Il1 O0Q 5S 8B rn m", "ÀÁÂÃÄÅ Ç ÉÈÊË Ñ ÖÜ ß", "0123456789"]
var records: [[String: Any]] = []
func fail(_ message: String) -> Never { fputs(message + "\n", stderr); exit(1) }
for format in ["ttf", "otf"] {
    let base = root.appendingPathComponent("dist/" + format)
    guard let walker = FileManager.default.enumerator(at: base, includingPropertiesForKeys: nil) else { fail("Missing font directory") }
    let urls = walker.compactMap { $0 as? URL }.filter { $0.pathExtension == format }.sorted { $0.path < $1.path }
    guard urls.count == 32 else { fail("Expected 32 faces per desktop format") }
    for url in urls {
        var error: Unmanaged<CFError>?
        guard CTFontManagerRegisterFontsForURL(url as CFURL, .process, &error) else { fail("Registration failed: " + url.lastPathComponent + ": " + String(describing: error?.takeRetainedValue())) }
        let expected = url.deletingPathExtension().lastPathComponent
        let font = CTFontCreateWithName(expected as CFString, 36, nil)
        let actual = CTFontCopyPostScriptName(font) as String
        guard actual == expected else { fail("Font identity mismatch: " + actual + " != " + expected) }
        guard let fileURL = CTFontCopyAttribute(font, kCTFontURLAttribute) as? URL, fileURL.standardizedFileURL == url.standardizedFileURL else { fail("CoreText used a different file for " + expected) }
        var widths: [Double] = []
        guard let context = CGContext(data: nil, width: 1500, height: 620, bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { fail("Cannot allocate drawing context") }
        context.setFillColor(CGColor(gray: 1, alpha: 1)); context.fill(CGRect(x: 0, y: 0, width: 1500, height: 620))
        for (index, text) in samples.enumerated() {
            let attributes: [NSAttributedString.Key: Any] = [NSAttributedString.Key(kCTFontAttributeName as String): font, NSAttributedString.Key(kCTForegroundColorAttributeName as String): CGColor(gray: 0, alpha: 1)]
            let line = CTLineCreateWithAttributedString(NSAttributedString(string: text, attributes: attributes))
            let width = CTLineGetTypographicBounds(line, nil, nil, nil)
            guard width > 0 && width < 1460 else { fail("Invalid line bounds: " + expected) }
            for run in CTLineGetGlyphRuns(line) as! [CTRun] {
                let attrs = CTRunGetAttributes(run) as NSDictionary
                let runFont = attrs[kCTFontAttributeName] as! CTFont
                guard CTFontCopyPostScriptName(runFont) as String == expected else { fail("Unexpected fallback font: " + expected) }
            }
            widths.append(width)
            context.textPosition = CGPoint(x: 24, y: 550 - index * 73)
            CTLineDraw(line, context)
        }
        if expected.hasSuffix("-Bold") || expected.hasSuffix("-Regular") {
            guard let image = context.makeImage(), let png = NSBitmapImageRep(cgImage: image).representation(using: .png, properties: [:]) else { fail("PNG rendering failed") }
            try png.write(to: out.appendingPathComponent("coretext-" + expected + "-" + format + ".png"))
        }
        records.append(["file": format + "/" + url.deletingLastPathComponent().lastPathComponent + "/" + url.lastPathComponent, "postscript": actual, "sample_lines": samples.count, "widths": widths, "process_registration": true, "no_fallback": true])
        guard CTFontManagerUnregisterFontsForURL(url as CFURL, .process, &error) else { fail("Unregister failed: " + expected) }
    }
}
let report: [String: Any] = ["platform": ProcessInfo.processInfo.operatingSystemVersionString, "scope": "CoreText process registration only; no persistent installation or manual app acceptance", "records": records]
let data = try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys])
try data.write(to: out.appendingPathComponent("coretext-checks.json"))
print("PASS: \(records.count) desktop candidates, \(records.count * samples.count) CoreText lines, exact file identity, no fallback, process-only registration.")
