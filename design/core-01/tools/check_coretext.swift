// Process-only native rendering of the core study. Never installs fonts.
import Foundation
import CoreText
import AppKit
import CryptoKit
let root = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
let out = root.appendingPathComponent(".release-work/core-01")
let samples = ["BMR", "age", "23689", "Rage", "Mega"]
var records: [[String: Any]] = []
func fail(_ message: String) -> Never { fputs(message + "\n", stderr); exit(1) }
for family in ["LihuiT", "zayJu"] {
    for format in ["ttf", "otf"] {
        let post = family + "CoreStudy01-Reference"
        let file = out.appendingPathComponent("fonts/" + post + "." + format)
        var error: Unmanaged<CFError>?
        guard CTFontManagerRegisterFontsForURL(file as CFURL, .process, &error) else { fail("Core study registration failed") }
        let font = CTFontCreateWithName(post as CFString, 76, nil)
        guard CTFontCopyPostScriptName(font) as String == post else { fail("Study font identity mismatch") }
        guard let actual = CTFontCopyAttribute(font, kCTFontURLAttribute) as? URL, actual.standardizedFileURL == file.standardizedFileURL else { fail("Unexpected file/fallback") }
        guard let context = CGContext(data: nil, width: 1400, height: 760, bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { fail("Drawing context unavailable") }
        context.setFillColor(CGColor(gray: 1, alpha: 1)); context.fill(CGRect(x: 0,y: 0,width: 1400,height: 760))
        for (i,sample) in samples.enumerated() {
            let attributes: [NSAttributedString.Key: Any] = [NSAttributedString.Key(kCTFontAttributeName as String): font,NSAttributedString.Key(kCTForegroundColorAttributeName as String): CGColor(gray: 0, alpha: 1)]
            let line=CTLineCreateWithAttributedString(NSAttributedString(string: sample,attributes: attributes))
            guard CTLineGetTypographicBounds(line,nil,nil,nil)>0 else { fail("Empty core sample") }
            for run in CTLineGetGlyphRuns(line) as! [CTRun] {
                let attrs=CTRunGetAttributes(run) as NSDictionary
                let runFont=attrs[kCTFontAttributeName] as! CTFont
                guard CTFontCopyPostScriptName(runFont) as String == post else { fail("Fallback in core sample") }
                var glyphs=[CGGlyph](repeating: 0,count: CTRunGetGlyphCount(run))
                CTRunGetGlyphs(run,CFRange(location: 0,length: 0),&glyphs)
                guard glyphs.allSatisfy({$0 != 0}) else { fail("Missing core glyph") }
            }
            context.textPosition=CGPoint(x: 45,y: 660-i*137);CTLineDraw(line,context)
        }
        guard let image=context.makeImage(),let png=NSBitmapImageRep(cgImage: image).representation(using: .png,properties: [:]) else { fail("Native proof failed") }
        try png.write(to: out.appendingPathComponent("native-"+family+"-"+format+".png"))
        let hash=SHA256.hash(data: try Data(contentsOf: file)).map { String(format:"%02x",$0) }.joined()
        records.append(["file":"fonts/"+post+"."+format,"sha256":hash,"sample_lines":samples.count,"exact_file":true,"no_fallback":true])
        guard CTFontManagerUnregisterFontsForURL(file as CFURL,.process,&error) else { fail("Process unregister failed") }
    }
}
let report:[String:Any] = ["scope":"core-only macOS rendering; process registration, not installation or visual approval","files":records,"passed":true]
try JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys]).write(to:out.appendingPathComponent("coretext.json"))
print("PASS: 4 actual core-font files, 20 CoreText sample lines; no fallback, no installation.")
