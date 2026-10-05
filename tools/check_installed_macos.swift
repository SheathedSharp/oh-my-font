// Validate fonts installed in the release-specific USER font folder.
// Does not register substitute/process-only fonts; RTF round-trips through AppKit.
import Foundation
import CoreText
import AppKit
let root = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
let version = try String(contentsOf:root.appendingPathComponent("VERSION"),encoding:.utf8).trimmingCharacters(in:.whitespacesAndNewlines)
let folder = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Fonts/oh-my-font-v"+version)
let out = root.appendingPathComponent(".release-work")
func fail(_ s:String)->Never { fputs(s+"\n",stderr);exit(1) }
let files = try FileManager.default.contentsOfDirectory(at:folder,includingPropertiesForKeys:nil).filter{$0.pathExtension=="ttf"}.sorted{$0.path<$1.path}
guard files.count==32 else { fail("Expected 32 installed TTF files") }
let specimen=NSMutableAttributedString(string:"")
var records:[[String:Any]]=[]
for url in files {
    let name=url.deletingPathExtension().lastPathComponent
    guard let font=NSFont(name:name,size:27) else {fail("Installed NSFont unavailable: "+name)}
    let ct=CTFontCreateWithName(name as CFString,27,nil)
    guard let resolved=CTFontCopyAttribute(ct,kCTFontURLAttribute) as? URL, resolved.standardizedFileURL==url.standardizedFileURL else {fail("Installed file identity mismatch: "+name)}
    let family=CTFontCopyFamilyName(ct) as String
    guard family=="LihuiT" || family=="zayJu" else {fail("Unexpected family: "+family)}
    records.append(["postscript":name,"family":family,"file":url.lastPathComponent,"installed_file_match":true])
    specimen.append(NSAttributedString(string:name+"\n",attributes:[.font:NSFont.systemFont(ofSize:10)]))
    specimen.append(NSAttributedString(string:"Build a brighter tomorrow.\nIdeas ship farther. Zayju zayju.de\nÀÁÂÃÄÅ Ç ÉÈÊË Ñ ÖÜ ß  Il1 O0Q 5S 8B rn m\n\n",attributes:[.font:font]))
}
var styleLinks:[[String:Any]]=[]
for family in ["LihuiT","zayJu"] {
    let regular=NSFont(name:family+"-Regular",size:27)!
    let bold=NSFontManager.shared.convert(regular,toHaveTrait:.boldFontMask)
    let italic=NSFontManager.shared.convert(regular,toHaveTrait:.italicFontMask)
    guard bold.fontName==family+"-Bold", italic.fontName==family+"-Oblique" else { fail("Style link mismatch: \(family), \(bold.fontName), \(italic.fontName)") }
    styleLinks.append(["family":family,"bold":bold.fontName,"italic":italic.fontName])
}
let data=try specimen.data(from:NSRange(location:0,length:specimen.length),documentAttributes:[.documentType:NSAttributedString.DocumentType.rtf])
let rtf=out.appendingPathComponent("Installed-Fonts-Specimen.rtf")
try data.write(to:rtf)
let reread=try NSAttributedString(url:rtf,options:[.documentType:NSAttributedString.DocumentType.rtf],documentAttributes:nil)
var names=Set<String>()
reread.enumerateAttribute(.font,in:NSRange(location:0,length:reread.length)){value,_,_ in if let f=value as? NSFont, f.fontName.hasPrefix("LihuiT-") || f.fontName.hasPrefix("zayJu-"){names.insert(f.fontName)}}
guard names.count==32 else {fail("RTF round-trip lost faces: \(names.count)")}
let report:[String:Any]=["os":ProcessInfo.processInfo.operatingSystemVersionString,"scope":"32 TTFs in release-specific user font folder; independent AppKit lookup and RTF round-trip; not manual design approval","records":records,"style_links":styleLinks,"rtf_preserved_faces":names.count]
try JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys]).write(to:out.appendingPathComponent("installed-macos-checks.json"))
print("PASS: 32 installed TTFs, exact path/family, native bold/Oblique linking, 32-face RTF export/import.")
