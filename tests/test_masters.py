"""Source isolation and curve-export regression tests; no font installation."""
from pathlib import Path
import json,math,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools'),str(ROOT)]
from masters import Designer,MASTER_ROOT,WEIGHTS,Outline
from build import compile_font
from outline_qa import inspect

class MasterTests(unittest.TestCase):
    def test_complete_independent_weight_inventory(self):
        identities=set();reference_cmap=None
        for family in ('LihuiT','zayJu'):
            outlines=[]
            for weight in WEIGHTS:
                d=Designer(family,weight)
                self.assertEqual((len(d.glyphs),len(d.cmap)),(945,810))
                if reference_cmap is None:reference_cmap=d.cmap
                self.assertEqual(d.cmap,reference_cmap)
                identities.add(d.source_path)
                outlines.append(tuple(d.glyphs['n'].geometry.recording.value))
            self.assertEqual(len(set(outlines)),8)
        self.assertEqual(len(identities),16)

    def test_production_loader_never_imports_drawing_scaffolds(self):
        code=f"import sys;sys.path[:0]=[{str(ROOT/'src')!r},{str(ROOT)!r}];import build;build.Designer('LihuiT',100);assert not any(n in sys.modules for n in ('outlines','outline_engine','beziers','shapely'))"
        subprocess.run([sys.executable,'-c',code],check=True)

    def test_svg_roundtrip_preserves_selected_master_and_other_weight(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'LihuiT').mkdir()
            before={}
            for weight in (100,300):
                payload=(MASTER_ROOT/'LihuiT'/f'{weight}.json').read_bytes()
                (root/'LihuiT'/f'{weight}.json').write_bytes(payload);before[weight]=payload
            svg=root/'e.svg'
            args=['--family','LihuiT','--weight','100','--glyph','e','--svg',str(svg),'--source-root',str(root)]
            for operation in ('export','import'):
                subprocess.run([sys.executable,str(ROOT/'tools/master_svg.py'),operation,*args],check=True,capture_output=True,text=True)
            self.assertEqual((root/'LihuiT/100.json').read_bytes(),before[100])
            self.assertEqual((root/'LihuiT/300.json').read_bytes(),before[300])

    def test_missing_weight_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(FileNotFoundError):Designer('zayJu',100,source_root=Path(temp))

    def test_single_weight_edit_is_isolated(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);(base/'LihuiT').mkdir()
            for weight in (100,300):
                (base/'LihuiT'/f'{weight}.json').write_bytes((MASTER_ROOT/'LihuiT'/f'{weight}.json').read_bytes())
            before100=Designer('LihuiT',100,source_root=base)
            before300=Designer('LihuiT',300,source_root=base)
            path=base/'LihuiT/100.json';data=json.loads(path.read_text())
            glyph=next(g for g in data['glyphs'] if g['name']=='n')
            glyph['advance']+=7
            path.write_text(json.dumps(data))
            after100=Designer('LihuiT',100,source_root=base)
            after300=Designer('LihuiT',300,source_root=base)
            self.assertEqual(after100.glyphs['n'].advance,before100.glyphs['n'].advance+7)
            self.assertEqual(after300.glyphs['n'].advance,before300.glyphs['n'].advance)
            self.assertEqual(after300.glyphs['n'].geometry.recording.value,before300.glyphs['n'].geometry.recording.value)

    def test_oblique_transforms_its_own_master_control_points(self):
        upright=Designer('zayJu',100);oblique=Designer('zayJu',100,True)
        for name in ('e','n','R','uni00E9'):
            a=upright.glyphs[name];b=oblique.glyphs[name]
            self.assertEqual(a.advance,b.advance)
            self.assertEqual(len(a.geometry.recording.value),len(b.geometry.recording.value))
            for (op,points),(other,transformed) in zip(a.geometry.recording.value,b.geometry.recording.value):
                self.assertEqual(op,other)
                for p,q in zip(points,transformed):
                    self.assertAlmostEqual(q[0],p[0]+p[1]*math.tan(math.radians(10)),places=7)
                    self.assertAlmostEqual(q[1],p[1],places=7)

    def test_real_cubic_and_quadratic_export(self):
        d=Designer('LihuiT',100)
        for cff in (False,True):
            font,_,_=compile_font(d,cff)
            gs=font.getGlyphSet();r=inspect(gs['e'],gs)
            self.assertTrue(r['valid'])
            self.assertGreater(r['cubics'] if cff else r['quadratics'],0)
            self.assertEqual(r['counter_contours'],1)

    def test_invalid_master_identity_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);(base/'zayJu').mkdir()
            path=base/'zayJu/100.json'
            path.write_bytes((MASTER_ROOT/'LihuiT/100.json').read_bytes())
            with self.assertRaisesRegex(ValueError,'identity'):Designer('zayJu',100,source_root=base)

    def test_open_contour_is_not_accepted_by_geometry_gate(self):
        with self.assertRaisesRegex(ValueError,'Open font contour'):
            inspect(Outline('M0 0 L100 0 L100 100'))

class NumericRegressionTests(unittest.TestCase):
    def test_legacy_light_foot_and_e_defects_are_reproducible(self):
        import importlib
        from shapely.geometry import LineString
        legacy_path=str(ROOT/'tools/drawing/legacy')
        sys.path.insert(0,legacy_path)
        try:old=importlib.import_module('outlines').Designer('LihuiT',100)
        finally:sys.path.remove(legacy_path)
        n,_=old.lower('n');e,_=old.lower('e')
        cut=n.intersection(LineString([(-100,1),(2000,1)]))
        widths=[g.length for g in cut.geoms]
        self.assertTrue(any(width>old.t+1 for width in widths))
        self.assertEqual(e.geom_type,'MultiPolygon')
        self.assertEqual(len(e.geoms),2)

    def test_serialized_cff_has_no_fractional_closure_drift(self):
        import io
        from fontTools.ttLib import TTFont
        font,_,_=compile_font(Designer('LihuiT',100),True)
        out=io.BytesIO();font.save(out);out.seek(0)
        with TTFont(out) as saved:
            gs=saved.getGlyphSet()
            for name in ('A','n','P','e','g.double'):
                self.assertTrue(inspect(gs[name],gs)['valid'],name)

    def test_serialized_ttf_fraction_has_no_quantized_spike(self):
        import io
        from fontTools.ttLib import TTFont
        font,_,_=compile_font(Designer('LihuiT',100),False)
        out=io.BytesIO();font.save(out);out.seek(0)
        with TTFont(out) as saved:
            gs=saved.getGlyphSet()
            self.assertTrue(inspect(gs['uni2153'],gs)['valid'])

    def test_zero_width_backtrack_cleanup_does_not_hide_real_crossings(self):
        from drawing.finish import finish_svg
        fixed,count=finish_svg('M0 0 L0 10 L10 10 L10 0 L20 0 L0 0 Z')
        self.assertEqual(count,1)
        r=inspect(Outline(fixed));self.assertTrue(r['valid'])
        self.assertAlmostEqual(r['geometry'].area,100)
        with self.assertRaises(ValueError):finish_svg('M0 0 L10 10 L0 10 L10 0 Z')

    def test_black_doubleacute_stays_separate_after_integer_export(self):
        import io
        from fontTools.ttLib import TTFont
        from outline_qa import component_count
        for oblique in (False,True):
            for cff in (False,True):
                with self.subTest(oblique=oblique,cff=cff):
                    font,_,_=compile_font(Designer('zayJu',900,oblique),cff)
                    out=io.BytesIO();font.save(out);out.seek(0)
                    with TTFont(out) as saved:
                        gs=saved.getGlyphSet()
                        for name,expected in [('uni030B',2),('uni02DD',2),('uni0170',3)]:
                            r=inspect(gs[name],gs)
                            self.assertTrue(r['valid'],name)
                            self.assertEqual(component_count(r['geometry']),expected,name)

    def test_indexed_distance_matches_dense_reference(self):
        from check_conversion import indexed_boundary_distance
        from shapely.geometry import Polygon
        from shapely.affinity import translate
        a=Polygon([(0,0),(120,0),(120,100),(0,100)],holes=[[(20,20),(60,20),(60,60),(20,60)]])
        b=translate(a,.37,-.63)
        expected=a.boundary.segmentize(2).hausdorff_distance(b.boundary.segmentize(2))
        self.assertAlmostEqual(indexed_boundary_distance(a,b),expected,places=10)

if __name__=='__main__':unittest.main()
