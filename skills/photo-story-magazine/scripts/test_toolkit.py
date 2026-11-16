"""Behavioral checks for the shipped renderer; run with --fonts <prepared manifest>."""
import argparse
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from pypdf import PdfReader
from PIL import Image
from reportlab.lib.units import mm
from magazine_layout import LayoutError, contrast, crop_geometry, render_plan

ROOT = Path(__file__).resolve().parent.parent
FONT_MANIFEST = None


class ToolkitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fieldkit-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def plan(self, elements, leaves=1):
        data = {"schema_version": 1, "title": "排版测试", "page_mm": [190,254],
                "pages": [{"id":"test","name":"中文书签","leaves":leaves,
                           "background":"#ffffff","elements":elements}]}
        path = self.root/"plan.json"
        path.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
        return path

    def textbox(self, **kw):
        return dict(type="text",text="正文测试与数字 2026",x=10,y=10,w=100,h=30,
                    role="body",color="#102a20",background="#ffffff",**kw)

    def test_focal_crop_and_aspect(self):
        box = [0,0,100,100]
        left,top,w,h = crop_geometry(300,100,box,[1,.5])
        self.assertEqual((left,top,w,h),(-200,0,300,100))
        self.assertAlmostEqual(w/h,3)
        self.assertEqual(crop_geometry(300,100,box,[0,.5]),(0,0,300,100))
        for actual, expected in zip(crop_geometry(300,100,box,fit="contain"),(0,100/3,100,100/3)):
            self.assertAlmostEqual(actual,expected)
        with self.assertRaises(LayoutError):
            crop_geometry(300,100,box,[1.5,.5])

    def test_selectable_chinese_embedded_fonts_and_split(self):
        path = self.plan([self.textbox(),
                          dict(type="text",text="右页终点",role="title",x=205,y=20,w=130,h=40)],2)
        out = render_plan(path,FONT_MANIFEST,self.root/"ok")
        spread, single = PdfReader(out/"magazine-spreads.pdf"), PdfReader(out/"magazine.pdf")
        self.assertEqual(len(spread.pages),1)
        self.assertEqual(len(single.pages),2)
        self.assertAlmostEqual(float(single.pages[0].mediabox.width),190*mm,places=3)
        self.assertAlmostEqual(float(spread.pages[0].mediabox.width),380*mm,places=3)
        self.assertIn("正文测试",spread.pages[0].extract_text())
        self.assertIn("右页终点",spread.pages[0].extract_text())
        embedded = 0
        for ref in spread.pages[0]["/Resources"]["/Font"].values():
            font = ref.get_object()
            if "/FontDescriptor" in font:
                self.assertIn("/FontFile2",font["/FontDescriptor"])
                embedded += 1
        self.assertGreaterEqual(embedded,2)
        self.assertTrue(single.outline)

    def test_overflow_rejects_pdf(self):
        e=self.textbox(); e.update(h=1,text="这是不能被静默裁掉的正文。"*10)
        with self.assertRaisesRegex(LayoutError,"overflow"):
            render_plan(self.plan([e]),FONT_MANIFEST,self.root/"overflow")
        self.assertFalse((self.root/"overflow/magazine.pdf").exists())

    def test_component_demo_cannot_silently_become_production(self):
        path=self.plan([self.textbox()])
        data=json.loads(path.read_text(encoding="utf-8")); data["kind"]="component-demo"
        path.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
        with self.assertRaisesRegex(LayoutError,"Component teaching plan"):
            render_plan(path,FONT_MANIFEST,self.root/"demo-blocked")
        self.assertFalse((self.root/"demo-blocked/magazine.pdf").exists())
        out=render_plan(path,FONT_MANIFEST,self.root/"demo-explicit",allow_demo=True)
        report=json.loads((out/"layout-report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["purpose"],"technical-demo")

    def test_missing_glyph_rejects_pdf(self):
        e=self.textbox(); e["text"]="缺字"+chr(0x10FFFF)
        with self.assertRaisesRegex(LayoutError,"Missing glyphs"):
            render_plan(self.plan([e]),FONT_MANIFEST,self.root/"missing")
        self.assertFalse((self.root/"missing/magazine.pdf").exists())

    def test_low_contrast_and_bounds(self):
        e=self.textbox(); e["color"]="#aaaaaa"
        with self.assertRaisesRegex(LayoutError,"contrast"):
            render_plan(self.plan([e]),FONT_MANIFEST,self.root/"contrast")
        e=self.textbox(); e["x"]=180
        with self.assertRaisesRegex(LayoutError,"outside page"):
            render_plan(self.plan([e]),FONT_MANIFEST,self.root/"bounds")
        self.assertGreater(contrast("#000000","#ffffff"),20)

    def test_foreground_layer_image_and_source_preservation(self):
        source=ROOT/"assets/specimens/landscape.png"
        before=hashlib.sha256(source.read_bytes()).hexdigest()
        elements=[dict(type="image",src=str(source),x=0,y=0,w=190,h=254,focal=[.8,.4],
                       clip=[[0,0],[1,0],[.85,1],[0,1]]),
                  self.textbox(),
                  dict(type="polygon",points=[[10,35],[30,32],[50,36]],fill="#1d3e35")]
        out=render_plan(self.plan(elements),FONT_MANIFEST,self.root/"layers")
        report=json.loads((out/"layout-report.json").read_text(encoding="utf-8"))
        self.assertEqual(len(report["images"]),1)
        self.assertEqual(before,hashlib.sha256(source.read_bytes()).hexdigest())
        with self.assertRaisesRegex(LayoutError,"not overwritten"):
            render_plan(self.root/"plan.json",FONT_MANIFEST,out)

    def test_exif_rotation_and_alpha_layer(self):
        source=self.root/"rotated.jpg"
        image=Image.new("RGB",(90,40),"red")
        exif=image.getexif(); exif[274]=6
        image.save(source,exif=exif)
        alpha=self.root/"foreground.png"
        Image.new("RGBA",(10,10),(10,90,50,128)).save(alpha)
        elements=[dict(type="image",src=str(source),x=10,y=10,w=60,h=120),
                  dict(type="image",src=str(alpha),x=10,y=10,w=60,h=120,fit="contain")]
        out=render_plan(self.plan(elements),FONT_MANIFEST,self.root/"exif")
        report=json.loads((out/"layout-report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["images"][0]["oriented_pixels"],[40,90])
        images=PdfReader(out/"magazine-spreads.pdf").pages[0]["/Resources"]["/XObject"]
        self.assertTrue(any("/SMask" in ref.get_object() for ref in images.values()))


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fonts",type=Path,required=True)
    args,remaining=parser.parse_known_args()
    FONT_MANIFEST=args.fonts.resolve()
    unittest.main(argv=[__file__]+remaining)
