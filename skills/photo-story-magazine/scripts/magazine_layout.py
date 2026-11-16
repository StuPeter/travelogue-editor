"""JSON-driven editorial PDF components. Geometry: mm, top-left; typography: pt."""
import argparse
import copy
import hashlib
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape
from PIL import Image, ImageOps
from fontTools.ttLib import TTFont as FontFile
from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph


class LayoutError(ValueError):
    pass


def contrast(fg, bg):
    def luminance(color):
        rgb = HexColor(color).rgb()
        values = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in rgb]
        return sum(c * w for c, w in zip(values, (.2126, .7152, .0722)))
    a, b = sorted([luminance(fg), luminance(bg)])
    return (b + .05) / (a + .05)


def crop_geometry(iw, ih, box, focal=(.5, .5), fit="cover"):
    """Focal = normalized point in oriented source, placed near box center and clamped."""
    x, y, w, h = box
    if min(iw, ih, w, h) <= 0 or fit not in ("cover", "contain"):
        raise LayoutError("Invalid image dimensions or fit mode")
    if len(focal) != 2 or not all(0 <= v <= 1 for v in focal):
        raise LayoutError("focal must contain two values in [0, 1]")
    scale = (max if fit == "cover" else min)(w / iw, h / ih)
    dw, dh = iw * scale, ih * scale
    if fit == "cover":
        left = x + min(0, max(w - dw, w / 2 - dw * focal[0]))
        top = y + min(0, max(h - dh, h / 2 - dh * focal[1]))
    else:
        left, top = x + (w - dw) / 2, y + (h - dh) / 2
    return left, top, dw, dh


class Renderer:
    def __init__(self, font_manifest, asset_root):
        path = Path(font_manifest).resolve()
        self.fonts = json.loads(path.read_text(encoding="utf-8"))
        self.roles = self.fonts["roles"]
        self.coverage = {}
        self.root = Path(asset_root).resolve()
        self.report = {"images": [], "text_boxes": [], "manual_review": [], "errors": []}
        for key, font in self.fonts["fonts"].items():
            file = path.parent / font["file"]
            if hashlib.sha256(file.read_bytes()).hexdigest() != font["sha256"]:
                raise LayoutError(f"Prepared font hash mismatch: {key}")
            pdfmetrics.registerFont(TTFont("FieldKit-" + key, str(file)))
            with FontFile(file) as ff:
                self.coverage[key] = set(ff.getBestCmap())

    def box(self, e):
        box = [float(e[k]) for k in ("x", "y", "w", "h")]
        if not all(math.isfinite(v) for v in box) or min(box[2:]) <= 0:
            raise LayoutError(f"Invalid box: {e}")
        x, y, w, h = box
        if not e.get("allow_bleed") and (x < 0 or y < 0 or x + w > self.width + .01 or y + h > self.height + .01):
            raise LayoutError(f"Box outside page: {box}")
        return box

    def text(self, e):
        x, y, w, h = self.box(e)
        role = self.roles[e.get("role", "body")]
        font = role["font"]
        size, leading = e.get("size", role["size"]), e.get("leading", role["leading"])
        text = e["text"]
        missing = sorted({ch for ch in text if not ch.isspace() and ord(ch) not in self.coverage[font]})
        if missing:
            raise LayoutError(f"Missing glyphs in {font}: {''.join(missing)}")
        color = e.get("color", "#1d2825")
        if e.get("background"):
            ratio = contrast(color, e["background"])
            threshold = 3 if size >= 18 or (size >= 14 and role.get("weight", 400) >= 700) else 4.5
            if ratio < threshold:
                raise LayoutError(f"Low solid-field text contrast {ratio:.2f}: {text[:30]}")
        elif e.get("over_image"):
            self.report["manual_review"].append({"page": self.page_id, "text": text[:40],
                                                  "reason": "Check full local image background at reading size"})
        style = ParagraphStyle("field", fontName="FieldKit-" + font,
                               fontSize=size, leading=leading, wordWrap="CJK",
                               textColor=HexColor(color), alignment={"left": 0, "center": 1, "right": 2}[e.get("align", "left")])
        p = Paragraph(escape(text).replace("\n", "<br/>"), style)
        _, used = p.wrap(w * mm, self.height * mm * 10)
        if used > h * mm + .01:
            raise LayoutError(f"Text overflow {used/mm:.1f}mm > {h}mm: {text[:40]}")
        p.drawOn(self.c, x * mm, (self.height - y) * mm - used)
        self.report["text_boxes"].append({"page": self.page_id, "text": text[:50],
                                          "height_mm": round(used / mm, 3), "available_mm": h,
                                          "role": e.get("role", "body")})

    def path(self, points, close=False):
        p = self.c.beginPath()
        for i, (x, y) in enumerate(points):
            (p.moveTo if i == 0 else p.lineTo)(x * mm, (self.height - y) * mm)
        if close:
            p.close()
        return p

    def draw(self, e):
        c = self.c
        c.saveState()
        try:
            c.setFillAlpha(e.get("opacity", 1))
            c.setStrokeAlpha(e.get("opacity", 1))
            kind = e["type"]
            if kind == "text":
                self.text(e)
            elif kind in ("rect", "panel"):
                x, y, w, h = self.box(e)
                c.setFillColor(HexColor(e.get("fill", "#f3eddf")))
                c.rect(x * mm, (self.height - y - h) * mm, w * mm, h * mm, fill=1, stroke=0)
            elif kind in ("line", "polygon"):
                if e.get("fill"):
                    c.setFillColor(HexColor(e["fill"]))
                c.setStrokeColor(HexColor(e.get("stroke", "#1d2825")))
                c.setLineWidth(e.get("line_width", .6))
                if e.get("dash"):
                    c.setDash(e["dash"])
                p = self.path(e["points"], kind == "polygon")
                c.drawPath(p, fill=int(bool(e.get("fill"))), stroke=int(e.get("stroke") is not None))
            elif kind == "image":
                x, y, w, h = self.box(e)
                with Image.open(self.root / e["src"]) as original:
                    image = ImageOps.exif_transpose(original)
                    image.load()
                    iw, ih = image.size
                    left, top, dw, dh = crop_geometry(iw, ih, (x, y, w, h),
                                                     e.get("focal", (.5, .5)), e.get("fit", "cover"))
                    if e.get("clip"):
                        points = [(x + px * w, y + py * h) for px, py in e["clip"]]
                        c.clipPath(self.path(points, True), fill=0, stroke=0)
                    else:
                        p = c.beginPath()
                        p.rect(x * mm, (self.height-y-h) * mm, w * mm, h * mm)
                        c.clipPath(p, fill=0, stroke=0)
                    c.drawImage(ImageReader(image), left*mm, (self.height-top-dh)*mm,
                                dw*mm, dh*mm, mask="auto")
                self.report["images"].append({"page": self.page_id, "src": e["src"],
                                               "oriented_pixels": [iw, ih], "focal": e.get("focal", [.5, .5]),
                                               "draw_box_mm": [left, top, dw, dh]})
            elif kind == "quote":
                # Offset filled field plus an open-corner border; child text stays editable.
                self.draw({**e, "type": "rect"})
                x, y, w, h = self.box(e)
                dx, dy = e.get("offset", [3, -3])
                gap = e.get("corner_gap", 7)
                points = [[x+dx, y+dy+gap], [x+dx, y+dy], [x+w+dx, y+dy],
                          [x+w+dx, y+h+dy], [x+dx, y+h+dy], [x+dx, y+h+dy-gap]]
                self.draw({"type": "line", "points": points, "stroke": e.get("border", "#a66d20"),
                           "line_width": e.get("line_width", .7)})
                padding = e.get("padding", 7)
                self.draw({**e, "type": "text", "x": x+padding, "y": y+padding,
                           "w": w-2*padding, "h": h-2*padding, "background": e.get("fill", "#f3eddf")})
            else:
                raise LayoutError(f"Unknown element type: {kind}")
        finally:
            c.restoreState()

    def render(self, plan, spread_path):
        self.c = canvas.Canvas(str(spread_path), pageCompression=1)
        self.c.setTitle(plan["title"])
        self.c.setAuthor(plan.get("author", "原创摄影专题"))
        self.c.setSubject("Layout toolkit output")
        leaf_width, self.height = plan.get("page_mm", [190, 254])
        leaf_number = 1
        for i, page in enumerate(plan["pages"]):
            leaves = page.get("leaves", 2)
            if leaves not in (1, 2):
                raise LayoutError("leaves must be 1 (single) or 2 (spread)")
            self.width = leaf_width * leaves
            self.page_id = page.get("id", str(i + 1))
            self.c.setPageSize((self.width * mm, self.height * mm))
            self.draw({"type": "rect", "x": 0, "y": 0, "w": self.width, "h": self.height,
                       "fill": page.get("background", "#fffdf6")})
            self.c.bookmarkPage("section-" + str(i))
            self.c.addOutlineEntry(page.get("name", self.page_id), "section-" + str(i))
            for e in page["elements"]:
                self.draw(e)
            nav = page.get("navigation")
            if nav:
                for leaf in range(leaves):
                    color = nav.get("color", "#263d35")
                    bg = nav.get("background")
                    for x, w, text in [(leaf*leaf_width+12, leaf_width-45, nav["label"]),
                                       ((leaf+1)*leaf_width-26, 14, f"{leaf_number+leaf:02d}")]:
                        self.draw({"type": "text", "role": "caption", "text": text,
                                   "x": x, "y": self.height-11, "w": w, "h": 6,
                                   "size": 7, "leading": 9, "color": color,
                                   **({"background": bg} if bg else {})})
            leaf_number += leaves
            self.c.showPage()
        self.c.save()


def split_spreads(source, target, plan):
    writer = PdfWriter()
    reader = PdfReader(source)
    width, height = plan.get("page_mm", [190, 254])
    first_leaf = 0
    for page, spec in zip(reader.pages, plan["pages"]):
        leaves = spec.get("leaves", 2)
        if leaves == 1:
            writer.add_page(page)
        else:
            for leaf in range(2):
                new = writer.add_blank_page(width*mm, height*mm)
                new.merge_transformed_page(copy.deepcopy(page), Transformation().translate(-leaf*width*mm, 0))
        writer.add_outline_item(title=spec.get("name", spec.get("id", "Section")), page_number=first_leaf)
        first_leaf += leaves
    writer.add_metadata({"/Title": plan["title"], "/Author": plan.get("author", "原创摄影专题")})
    with Path(target).open("wb") as stream:
        writer.write(stream)


def render_plan(plan_path, font_manifest, out, preview=False, dpi=90, asset_root=None, allow_demo=False):
    plan_path, out = Path(plan_path).resolve(), Path(out).resolve()
    plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    if plan.get("schema_version") != 1 or not plan.get("pages"):
        raise LayoutError("Expected schema_version: 1 and nonempty pages")
    if plan.get("kind") == "component-demo" and not allow_demo:
        raise LayoutError("Component teaching plan: use --demo for technical checks; create a new issue plan for production")
    out.mkdir(parents=True, exist_ok=True)
    names = ["magazine-spreads.pdf", "magazine.pdf", "layout-report.json"]
    if any((out / name).exists() for name in names):
        raise LayoutError("Use a new output directory; existing editions are not overwritten")
    renderer = Renderer(font_manifest, asset_root or plan_path.parent)
    # Reject overflow, missing glyphs and known low contrast before publishing any PDF.
    with tempfile.TemporaryDirectory(prefix="fieldkit-") as temp:
        temp = Path(temp)
        renderer.render(plan, temp/names[0])
        split_spreads(temp/names[0], temp/names[1], plan)
        renderer.report.update({"title": plan["title"], "page_mm": plan.get("page_mm", [190, 254]),
                                "spreads": len(plan["pages"]),
                                "leaves": sum(p.get("leaves", 2) for p in plan["pages"]),
                                "font_profile": renderer.fonts["profile"],
                                "purpose": "technical-demo" if plan.get("kind")=="component-demo" else "issue-layout"})
        (temp/names[2]).write_text(json.dumps(renderer.report, ensure_ascii=False, indent=2), encoding="utf-8")
        for name in names:
            shutil.copy2(temp/name, out/name)
    if preview:
        if not shutil.which("pdftoppm"):
            raise LayoutError("PDFs saved; install Poppler/pdftoppm to render visual previews")
        subprocess.run(["pdftoppm", "-r", str(dpi), "-png", str(out/names[0]), str(out/"preview")], check=True)
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--fonts", type=Path, required=True, help="Prepared font-manifest.json")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--asset-root", type=Path)
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--dpi", type=int, default=90)
    parser.add_argument("--demo", action="store_true", help="Explicitly run a component teaching plan")
    args = parser.parse_args()
    try:
        print(render_plan(args.plan, args.fonts, args.out, args.preview, args.dpi, args.asset_root, args.demo))
    except (LayoutError, KeyError, ValueError) as exc:
        parser.exit(2, f"Layout rejected: {exc}\n")
