// Native verification only. Registers these draft fonts within this process,
// checks exact file identities, and unregisters them; never installs fonts.
import Foundation
import CoreText
import AppKit
import CryptoKit
let root=URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
let out=root.appendingPathComponent(".release-work")
let inventory=try JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("design/full-01/repertoire.json"))) as! [String:Any]
let cmap=inventory["cmap"] as! [String:String]
let spaces:Set<Int>=[0,13,32,160,173,0x2000,0x2001,0x2002,0x2003,0x2004,0x2005,0x2006,0x2007,0x2008,0x2009,0x200a,0x200b,0x202f,0x2060,0xfeff]
let samples=["ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz 0123456789", "Build a brighter tomorrow. Quality & Rhythm.", "Café, déjà vu, naïve — Straße & Æther", "Ďábel Ľudovít Ťažký Őrült Łódź Œuvre", "Tiếng Việt: Nguyễn, Trường, cộng hòa", "Ąą Ęę Įį Ųų Ǫǫ Ǭǭ", "€ £ $ ¥ ₹ ₩ ₽ ₺ ₴ ₿ ¢ ¤ © ® ™", "← ↑ → ↓ ↔ ↕ ⇐ ⇒ ⌘ ⌥ ⎋ ✓", "¼ ½ ¾ ⅐ ⅓ ⅒ ⅞ ⅔", "x\u{0301}\u{0301} x\u{0323}\u{0323} O\u{031B}\u{0301}", "office affinity fluffy AVATAR To Wa"]
func fail(_ s:String)->Never{fputs(s+"\n",stderr);exit(1)}
var rows:[[String:Any]]=[]
for family in ["LihuiT","zayJu"] {
 for format in ["ttf","otf"] {
    let post=family+"-Regular";let file=root.appendingPathComponent("dist/"+format+"/"+family+"/"+post+"."+format)
    var error:Unmanaged<CFError>?
    guard CTFontManagerRegisterFontsForURL(file as CFURL,.process,&error) else{fail("Release registration failed: "+post)}
    let font=CTFontCreateWithName(post as CFString,38,nil)
    guard CTFontCopyPostScriptName(font) as String==post else{fail("Wrong font identity")}
    guard let actual=CTFontCopyAttribute(font,kCTFontURLAttribute) as? URL,actual.standardizedFileURL==file.standardizedFileURL else{fail("Font resolved to a different file")}
    var mapped=0
    for cp in cmap.keys.compactMap({Int($0)}).sorted() where !spaces.contains(cp) {
        guard let scalar=UnicodeScalar(cp) else{fail("Invalid repertoire scalar")}
        var chars=Array(String(scalar).utf16);var glyphs=[CGGlyph](repeating:0,count:chars.count)
        guard CTFontGetGlyphsForCharacters(font,&chars,&glyphs,chars.count),glyphs.contains(where:{$0 != 0}) else{fail("Missing encoded character: "+String(cp,radix:16))}
        mapped+=1
    }
    guard let context=CGContext(data:nil,width:1800,height:1260,bitsPerComponent:8,bytesPerRow:0,space:CGColorSpaceCreateDeviceRGB(),bitmapInfo:CGImageAlphaInfo.premultipliedLast.rawValue) else{fail("No context")}
    context.setFillColor(CGColor(gray:1,alpha:1));context.fill(CGRect(x:0,y:0,width:1800,height:1260))
    for (index,text) in samples.enumerated() {
        let attrs:[NSAttributedString.Key:Any]=[NSAttributedString.Key(kCTFontAttributeName as String):font,NSAttributedString.Key(kCTForegroundColorAttributeName as String):CGColor(gray:0,alpha:1)]
        let line=CTLineCreateWithAttributedString(NSAttributedString(string:text,attributes:attrs))
        let width=CTLineGetTypographicBounds(line,nil,nil,nil)
        guard width>0 && width<1720 else{fail("Sample width exceeds proof bounds")}
        for run in CTLineGetGlyphRuns(line) as! [CTRun] {
            let attrs=CTRunGetAttributes(run) as NSDictionary;let runFont=attrs[kCTFontAttributeName] as! CTFont
            guard CTFontCopyPostScriptName(runFont) as String==post else{fail("Fallback in multilingual sample")}
            var glyphs=[CGGlyph](repeating:0,count:CTRunGetGlyphCount(run));CTRunGetGlyphs(run,CFRange(location:0,length:0),&glyphs)
            guard glyphs.allSatisfy({$0 != 0}) else{fail("Notdef in multilingual sample")}
        }
        context.textPosition=CGPoint(x:40,y:1170-index*97);CTLineDraw(line,context)
    }
    guard let image=context.makeImage(),let png=NSBitmapImageRep(cgImage:image).representation(using:.png,properties:[:]) else{fail("Native render failed")}
    try png.write(to:out.appendingPathComponent("native-"+family+"-"+format+".png"))
    let hash=SHA256.hash(data:try Data(contentsOf:file)).map{String(format:"%02x",$0)}.joined()
    rows.append(["file":format+"/"+family+"/"+post+"."+format,"sha256":hash,"sample_lines":samples.count,"encoded_characters_mapped":mapped,"no_fallback":true,"exact_file":true])
    guard CTFontManagerUnregisterFontsForURL(file as CFURL,.process,&error) else{fail("Unregister failed")}
 }
}
let result:[String:Any]=["scope":"Official Regular release macOS checks: exact files, mapping and sample rendering; process-only registration, not installation or final optical approval","records":rows,"passed":true]
try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:out.appendingPathComponent("coretext-checks.json"))
print("PASS: 4 actual desktop files, 48 CoreText sample lines and 3160 encoded mappings; no fallback, no persistent installation.")
