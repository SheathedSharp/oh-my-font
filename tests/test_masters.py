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

if __name__=='__main__':unittest.main()
