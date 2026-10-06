"""Negative and regression tests for full reference-cut sources and exports."""
import io,sys,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'design/full-01/tools'),str(ROOT/'design/core-01/tools')]
from build import load,FULL,FAMILIES,verify_approved_core,validate_source,compile_font
from geometry import inspect,component_count
from fontTools.ttLib import TTFont
from ufoLib2.objects import Component,Anchor

class SourceTests(unittest.TestCase):
    def test_complete_legacy_contract_and_locked_core(self):
        target=json.loads((FULL/'repertoire.json').read_text())
        for family in FAMILIES:
            u=load(family);self.assertEqual(len(u),986)
            self.assertEqual(set(validate_source(u)),set(map(int,target['cmap'])))
            self.assertTrue(set(target['glyph_order'])<=set(u.keys()))
            verify_approved_core(u,family)

    def test_core_width_change_is_rejected(self):
        u=load('LihuiT');u['a'].width+=1
        with self.assertRaisesRegex(ValueError,'Approved'):verify_approved_core(u,'LihuiT')

    def test_core_curve_change_is_rejected(self):
        u=load('zayJu');u['M'].contours[0].points[0].x+=1
        with self.assertRaisesRegex(ValueError,'Approved'):verify_approved_core(u,'zayJu')

    def test_core_encoding_change_is_rejected(self):
        u=load('LihuiT');u['B'].unicodes=[]
        with self.assertRaisesRegex(ValueError,'Approved'):verify_approved_core(u,'LihuiT')

    def test_duplicate_codepoint_rejected(self):
        u=load('LihuiT');u['C'].unicodes.append(ord('D'))
        with self.assertRaisesRegex(ValueError,'Duplicate codepoint'):validate_source(u)

    def test_missing_component_rejected(self):
        u=load('LihuiT');u['C'].components.append(Component('nonexistent-source'))
        with self.assertRaisesRegex(ValueError,'Unknown component'):validate_source(u)

    def test_component_cycle_rejected(self):
        u=load('zayJu');u['C'].components.append(Component('C'))
        with self.assertRaisesRegex(ValueError,'Cyclic'):validate_source(u)

    def test_nonfinite_point_rejected(self):
        u=load('LihuiT');u['C'].contours[0].points[0].x=float('nan')
        with self.assertRaisesRegex(ValueError,'Non-finite'):validate_source(u)

    def test_duplicate_anchor_rejected(self):
        u=load('LihuiT');u['C'].anchors.append(Anchor(name='top',x=0,y=0))
        with self.assertRaisesRegex(ValueError,'Duplicate glyph anchor'):validate_source(u)

    def test_top_accents_do_not_reintroduce_tittles_under_ss03(self):
        from build import signature
        for family in FAMILIES:
            u=load(family)
            for base in ('uni00ED','uni00EC','uni00EE','uni00EF','uni01F0'):
                self.assertEqual(signature(u,base),signature(u,base+'.ss03'))

    def test_clarity_feature_includes_accented_forms(self):
        for family in FAMILIES:
            u=load(family);mapping=u.lib['de.zayju.alternateMappings']['ss05']
            self.assertEqual(len(mapping),25)
            for name in ('uni00CC','uni00CD','uni012E','uni013A','uni013E'):
                target=mapping[name];self.assertIn(target,u)
                self.assertEqual(u[target].width,u['I.clarity' if name in ('uni00CC','uni00CD','uni012E') else 'l.clarity'].width)

    def test_unknown_family_fails_closed(self):
        with self.assertRaisesRegex(ValueError,'Unknown'):load('other')

    def test_command_sign_has_only_intended_counters(self):
        for family in FAMILIES:
            u=load(family);r=inspect(u['uni2318'],u)
            self.assertTrue(r['valid']);self.assertEqual(r['counter_contours'],5)
            self.assertEqual(component_count(r['geometry']),1)

    def test_ogonek_joins_without_changing_base(self):
        for family in FAMILIES:
            u=load(family)
            for name in ('uni0104','uni0105','uni0118','uni0119','uni012E','uni0172','uni0173','uni01EA','uni01EB'):
                self.assertEqual(component_count(inspect(u[name],u)['geometry']),1,(family,name))
            self.assertIn('_ogonek',[a.name for a in u['uni0328'].anchors]);verify_approved_core(u,family)

    def test_soft_hyphen_is_default_invisible(self):
        for family in FAMILIES:
            u=load(family);self.assertEqual(u['uni00AD'].width,0)
            self.assertTrue(inspect(u['uni00AD'],u)['geometry'].is_empty)

class SerializedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fonts={}
        for cff in (False,True):
            f=compile_font(load('LihuiT'),cff);buf=io.BytesIO();f.save(buf);buf.seek(0)
            cls.fonts[cff]=TTFont(buf)
    @classmethod
    def tearDownClass(cls):
        for f in cls.fonts.values():f.close()

    def test_no_nested_true_type_components(self):
        f=self.fonts[False]
        for name in f.getGlyphOrder():
            g=f['glyf'][name]
            if g.isComposite():self.assertTrue(all(not f['glyf'][c.glyphName].isComposite() for c in g.components),name)

    def test_cubic_and_quadratic_curves_survive(self):
        for cff,f in self.fonts.items():
            gs=f.getGlyphSet();r=inspect(gs['e'],gs)
            self.assertGreater(r['cubics'] if cff else r['quadratics'],0)

    def test_oe_export_distance_is_bounded(self):
        geometries=[]
        for f in self.fonts.values():
            gs=f.getGlyphSet();r=inspect(gs['uni0152'],gs);self.assertTrue(r['valid']);geometries.append(r['geometry'])
        self.assertLessEqual(geometries[0].boundary.segmentize(1).hausdorff_distance(geometries[1].boundary.segmentize(1)),1.6)

    def test_smart_dropout_is_not_misrepresented_as_hinting(self):
        f=self.fonts[False]
        self.assertEqual(bytes(f['prep'].program.getBytecode()),bytes.fromhex('b801ff85b0048d'))
        self.assertNotIn('fpgm',f)

if __name__=='__main__':unittest.main()
