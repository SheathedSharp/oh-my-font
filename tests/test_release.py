"""Release identity, scope and packaging regressions. No font installation/publication."""
import importlib.util,io,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import release_support as contract
from fontTools.ttLib import TTFont
from package_release import archive
from verify_release import sums
spec=importlib.util.spec_from_file_location('official_release_build',ROOT/'build.py');production=importlib.util.module_from_spec(spec);spec.loader.exec_module(production)

class ContractTests(unittest.TestCase):
    def test_entire_accepted_source_snapshot_is_unchanged(self):
        spec=contract.validate_approval()
        self.assertEqual(spec['approved_commit'],'4640e2b38bc20b72e4f5584113208fa819b5adc9')
        self.assertEqual((spec['glyphs'],spec['codepoints']),(986,810))

    def test_only_two_regular_faces_six_files(self):
        expected=contract.expected_files();self.assertEqual(len(expected),6)
        self.assertTrue(all('-Regular.' in n for n in expected))
        self.assertEqual({n.split('/')[1] for n in expected},{'LihuiT','zayJu'})

    def test_modified_approval_input_is_blocking(self):
        with patch.object(contract,'sha',return_value='0'*64):
            with self.assertRaisesRegex(ValueError,'Approved reference input changed'):contract.validate_approval()

    def test_unknown_weights_cannot_be_synthesized(self):
        result=subprocess.run([sys.executable,str(ROOT/'build.py'),'--weights','100'],cwd=ROOT,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0);self.assertIn('unrecognized arguments',result.stderr)

    def test_stale_output_is_not_silently_mixed_or_deleted(self):
        with tempfile.TemporaryDirectory() as temp:
            old=Path(temp)/'ttf/zayJu/zayJu-Bold.ttf';old.parent.mkdir(parents=True);old.write_bytes(b'preserve old candidate')
            r=subprocess.run([sys.executable,str(ROOT/'build.py'),'--output',temp],cwd=ROOT,capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0);self.assertEqual(old.read_bytes(),b'preserve old candidate')

    def test_site_advertises_only_approved_regular_styles(self):
        import re
        html=(ROOT/'site/index.html').read_text()
        weight=re.search(r'<select id="weight">(.*?)</select>',html).group(1)
        self.assertEqual(weight.count('<option'),1);self.assertIn('value="400"',weight)
        self.assertNotIn('16 STYLES',html);self.assertNotIn('/ Bold /',html);self.assertIn('v'+contract.version(),html)
        self.assertEqual(set(re.findall(r'data-weight="(\d+)"',html)),{'400'})

    def test_no_legacy_drawing_import(self):
        self.assertNotIn('outlines',sys.modules);self.assertNotIn('outline_engine',sys.modules)

class MetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fonts={}
        for family in contract.FAMILIES:
            for cff in (False,True):
                u=contract.reference.load(family);font=production.promote(contract.reference.compile_font(u,cff),family)
                buf=io.BytesIO();font.save(buf);buf.seek(0);cls.fonts[(family,cff)]=TTFont(buf)
    @classmethod
    def tearDownClass(cls):
        for f in cls.fonts.values():f.close()

    def test_official_names_not_draft_names(self):
        for (family,_),f in self.fonts.items():
            self.assertEqual(f['name'].getDebugName(1),family)
            self.assertEqual(f['name'].getDebugName(2),'Regular')
            self.assertEqual(f['name'].getDebugName(6),family+'-Regular')
            self.assertEqual(f['name'].getDebugName(5),'Version '+contract.version())
            self.assertFalse(any('Full Draft' in n.toUnicode() or 'Core Study' in n.toUnicode() for n in f['name'].names))

    def test_no_legacy_mac_name_records_added(self):
        for f in self.fonts.values():
            self.assertFalse(any(n.platformID==1 for n in f['name'].names))

    def test_license_and_source_not_removed(self):
        for f in self.fonts.values():
            self.assertEqual(f['name'].getDebugName(13),(ROOT/'OFL.txt').read_text().strip())
            self.assertEqual(f['name'].getDebugName(11),'https://github.com/SheathedSharp/oh-my-font')
            self.assertEqual(f['name'].getDebugName(9),'zayju');self.assertEqual(f['OS/2'].fsType,0)

    def test_complete_scope_and_no_variable_or_italic(self):
        for f in self.fonts.values():
            self.assertEqual(len(f.getBestCmap()),810);self.assertEqual(len(f.getGlyphOrder()),986)
            self.assertEqual(f['OS/2'].usWeightClass,400);self.assertEqual(f['post'].italicAngle,0);self.assertNotIn('fvar',f)

    def test_cff_internal_identity(self):
        for family in contract.FAMILIES:
            f=self.fonts[family,True];self.assertEqual(f['CFF '].cff.fontNames,[family+'-Regular'])
            self.assertEqual(f['CFF '].cff.topDictIndex[0].version,contract.version())

class ArchiveTests(unittest.TestCase):
    def test_safe_archive_has_complete_internal_hashes(self):
        import zipfile,hashlib
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'test.zip';archive(p,'test',{'README.txt':b'hello'})
            with zipfile.ZipFile(p) as z:
                records=sums(z.read('test/SHA256SUMS.txt'))
                self.assertEqual(records,{'README.txt':hashlib.sha256(b'hello').hexdigest()})

    def test_archive_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError,'Unsafe'):archive(Path(temp)/'bad.zip','test',{'../bad':b'x'})

    def test_checksum_rejects_duplicate_names(self):
        line='0'*64+'  x\n'
        with self.assertRaisesRegex(ValueError,'duplicate'):sums((line+line).encode())

    def test_checksum_rejects_parent_paths(self):
        with self.assertRaisesRegex(ValueError,'Unsafe'):sums(('0'*64+'  ../x\n').encode())

if __name__=='__main__':unittest.main()
