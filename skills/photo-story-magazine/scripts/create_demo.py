"""Rebuild the redistributable original layout specimen and its two-page visual pilot."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from magazine_layout import render_plan

ROOT = Path(__file__).resolve().parent.parent
CREAM, INK, GREEN, GOLD, RED = "#f4efdf", "#203e35", "#184b40", "#a06a18", "#a83c2e"


def text(s, x, y, w, h, role="body", **kw):
    return dict(type="text", text=s, x=x, y=y, w=w, h=h, role=role, **kw)


def rect(x, y, w, h, fill):
    return dict(type="rect", x=x, y=y, w=w, h=h, fill=fill)


def line(points, stroke=GOLD, **kw):
    return dict(type="line", points=points, stroke=stroke, **kw)


def photo(x, y, w, h, **kw):
    return dict(type="image", src="landscape.png", x=x, y=y, w=w, h=h, **kw)


def illustration(path):
    # Original flat vector landscape: layout demonstrator, no actual place or photograph.
    c = canvas.Canvas(str(path), pagesize=(1200, 800))
    c.setFillColor(HexColor("#cedfdb")); c.rect(0, 0, 1200, 800, fill=1, stroke=0)
    def polygon(points, fill):
        c.setFillColor(HexColor(fill)); p=c.beginPath(); p.moveTo(*points[0])
        for xy in points[1:]: p.lineTo(*xy)
        p.close(); c.drawPath(p, fill=1, stroke=0)
    c.setFillColor(HexColor("#e6c36a")); c.circle(960, 650, 55, fill=1, stroke=0)
    polygon([(0,300),(0,440),(170,530),(360,680),(510,490),(760,610),(990,480),(1200,530),(1200,0),(0,0)], "#6f938a")
    polygon([(0,0),(0,290),(260,390),(510,300),(710,470),(950,390),(1200,440),(1200,0)], "#315f53")
    polygon([(0,0),(0,130),(260,270),(600,190),(820,310),(1200,200),(1200,0)], "#b49b56")
    polygon([(0,0),(1200,0),(1200,110),(910,230),(680,100),(360,140)], "#dacb92")
    polygon([(410,0),(550,0),(700,100),(670,120)], "#e9e4d1")
    for x,y in [(790,265),(845,250),(910,237)]:
        polygon([(x,y),(x,y+40),(x+40,y+40),(x+40,y)], "#efe5c9")
        polygon([(x-6,y+40),(x+20,y+59),(x+46,y+40)], "#713e30")
    c.showPage(); c.save()


def make_plan():
    nav = dict(label="行见 / 原创版式示范", color=INK, background=CREAM)
    cover = dict(id="cover", name="封面 / T01 分层字场", leaves=1, background=CREAM, elements=[
        rect(0,0,190,254,"#d9af38"), photo(8,8,174,238,fit="cover",focal=[.60,.5]),
        text("行见",19,18,145,25,"title",size=40,leading=45,color=INK),
        text("FIELD JOURNAL",20,46,140,8,"latin",color=INK),
        text("山水\n之间",19,133,151,75,"display",size=64,leading=71,color="#fffdf5",over_image=True),
        # An original foreground shape passes over a small lower edge of the last word.
        dict(type="polygon",points=[[8,192],[66,179],[115,193],[182,183],[182,246],[8,246]],fill=GREEN),
        text("一条线，连接山地与生活",19,214,145,12,"label",color="#ffffff",background=GREEN),
        text("原创版式示范 / 非实景影像",19,233,145,7,"caption",color="#ffffff",background=GREEN)])
    opening = dict(id="opening", name="开篇 / T02 + C05 稳定字场", leaves=2, background=CREAM, navigation=nav, elements=[
        photo(128,0,252,254,focal=[.67,.48]),rect(0,0,133,254,GREEN),
        text("01 / LAND & LIFE",14,17,105,9,"latin",color="#ead49b",background=GREEN),
        rect(0,28,380,87,GREEN),
        text("山水",14,34,171,80,"display",size=200,leading=212,color="#ffffff",background=GREEN),
        text("之间",205,34,171,80,"display",size=200,leading=212,color="#ffffff",background=GREEN),
        line([[14,111],[114,111]],"#cfb774",line_width=1.2),
        text("把风景放回关系之中",14,121,100,18,"title",size=20,leading=27,color="#ffffff",background=GREEN),
        text("山形先进入视野，随后才是坡地、道路与屋顶。开篇用一张主画面建立观看尺度，让文字在稳定色场中提出本期的问题。",14,151,101,46,color="#ffffff",background=GREEN,size=11,leading=19),
        text("本页示范：标题层级、主图比例、文字密度与阅读入口。\n图形为原创示意，不对应实际地点。",14,215,104,22,"caption",color="#ffffff",background=GREEN),
        rect(272,190,94,42,CREAM),
        text("先让读者看见关系，再让知识进入现场。",279,198,79,25,"title",size=17,leading=24,color=INK,background=CREAM),
        rect(0,239,380,15,CREAM)])
    collage = dict(id="collage",name="组照 / P01 + P02 + R02",leaves=2,background=CREAM,navigation=nav,elements=[
        text("02 / 从远景到手边",14,15,150,12,"label"),
        photo(0,39,191,143,clip=[[0,0],[.85,0],[1,1],[0,1]],focal=[.30,.45]),
        rect(157,95,88,112,"#ceae69"),photo(161,99,80,104,focal=[.75,.55]),
        photo(253,39,113,81,focal=[.72,.70]),
        text("一幅大图，\n三种观看尺度。",253,130,111,30,"title",size=23,leading=31),
        text("大图建立环境，近景提供结构，小图保留线索。图片大小表达阅读顺序；让遮叠发生在边缘，把关键主体和中缝留出来。",253,169,111,45),
        text("错层窗口不是随机摆放。\n斜边、共轴和留白共同引导视线。",14,194,118,25,"label"),
        dict(type="quote",x=143,y=216,w=100,h=23,fill="#e7e3d8",border=GOLD,padding=4,offset=[3,-3],
             role="caption",text="摘句撑开白纸，\n底色与框线可以错位。",color=INK)])
    explanation = dict(id="explanation",name="图解 / D04 + D06 可编辑引线",leaves=2,background=CREAM,navigation=nav,elements=[
        text("03 / 读懂一段屋檐",14,15,155,12,"label"),
        text("把整体，拆成可读的层次",14,35,335,26,"title",size=34,leading=43),
        text("图形、引线、标签各自保留矢量。示范对象为原创构形，用来展示信息组织；真实建筑的构件和年代应另据资料绘制。",14,72,139,39),
        text("03",14,127,55,24,"number",size=53,leading=59,color=RED,background=CREAM),
        text("个解释层次",62,142,87,14,"label"),
        text("轮廓 → 构件 → 关系\n先回答读者的问题，再决定需要多少标注。",14,167,136,28),
        dict(type="polygon",points=[[173,151],[255,94],[337,151]],fill="#bb8742"),
        dict(type="polygon",points=[[184,151],[255,107],[326,151]],fill="#e2bb70"),
        rect(190,153,130,9,"#713e30"),rect(200,162,9,45,"#713e30"),rect(302,162,9,45,"#713e30"),
        rect(190,207,130,8,"#b5b5a0"),
        line([[255,100],[281,82],[345,82]],INK),
        text("屋面 / 轮廓",294,70,72,12,"label"),
        line([[310,178],[336,171],[365,171]],INK),
        text("支撑 / 关系",321,158,55,12,"caption"),
        line([[230,211],[247,229],[301,229]],INK),
        text("台基 / 基线",304,224,60,12,"caption"),
        text("从上到下阅读结构；引线落在明确部位，避免交叉。",173,238,192,6,"caption",size=7,leading=9)])
    reading = dict(id="reading",name="阅读 / R04 + D01 窄信息轨",leaves=2,background=CREAM,navigation=nav,elements=[
        rect(0,0,58,254,GREEN),
        text("BY DESIGN",12,18,42,12,"latin",color="#ffffff",background=GREEN),
        text("190",12,52,44,25,"number",color="#ffffff",background=GREEN),
        text("毫米 / 单页宽",12,79,42,11,"caption",color="#ffffff",background=GREEN),
        line([[12,98],[46,98]],"#b9d1c4"),
        text("254",12,110,44,25,"number",color="#ffffff",background=GREEN),
        text("毫米 / 单页高",12,138,42,11,"caption",color="#ffffff",background=GREEN),
        text("本页数字说明\n样册开本，\n不指向实地测量。",12,200,39,29,"caption",color="#ffffff",background=GREEN),
        text("读得下去，才是版式的底座",72,20,292,26,"title",size=29,leading=38),
        text("稳定的阅读层",72,67,100,14,"label"),
        text("正文采用思源宋体四百字重，标题采用六百字重。图注与导航采用黑体五百字重，强标题采用八百字重。拉丁数字使用独立窄体。\n\n这种分工使展示层可以变化，读者仍能辨认正文入口、图注和页码。换字族之后，要重新检查断行、行数和段落高度。",72,89,98,112),
        text("图像与文字的接力",199,67,163,14,"label"),
        photo(199,87,165,80,focal=[.65,.5]),
        text("正文解释关系，图注提供对象信息；二者无需复述同一段话。窄信息轨只承载少量可比数字，长篇解释回到正文中完成。",199,179,165,39),
        text("本样册提供可运行的基础组件，不能代替对本期照片、故事与事实的判断。",72,224,291,12,"caption"),
        rect(0,239,380,15,CREAM)])
    back = dict(id="back",name="字体与组件 / 校准清单",leaves=1,background=GREEN,elements=[
        text("先做一小段，\n再铺开整本。",15,30,160,48,"display",size=35,leading=46,color="#ffffff",background=GREEN),
        text("视觉校准顺序",15,104,159,16,"title",color="#ffffff",background=GREEN),
        text("01  封面缩略图：标题与焦点\n02  代表跨页：裁切与中缝\n03  正文实读：字重与行距\n04  局部检查：图注与引线",15,131,158,61,"label",color="#ffffff",background=GREEN,size=12,leading=24),
        line([[15,209],[173,209]],"#b9d1c4"),
        text("源文件：specimen.json\n样册插画与文字均为本项目原创，可随 Skill 分发。",15,221,159,20,"caption",color="#ffffff",background=GREEN)])
    return dict(schema_version=1,kind="component-demo",title="行见 / 原创版式执行样册",author="照片故事杂志 Skill",page_mm=[190,254],
                pages=[cover,opening,collage,explanation,reading,back])


def create_assets(destination):
    destination=Path(destination); destination.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        artwork=Path(temp)/"landscape.pdf"
        illustration(artwork)
        subprocess.run(["pdftoppm","-singlefile","-scale-to","1600","-png",str(artwork),str(destination/"landscape")],check=True)
    plan=make_plan()
    (destination/"specimen.json").write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding="utf-8")
    pilot={**plan,"title":"行见 / 封面与代表跨页视觉校准","pages":plan["pages"][:2]}
    (destination/"pilot.json").write_text(json.dumps(pilot,ensure_ascii=False,indent=2),encoding="utf-8")


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets",type=Path,default=ROOT/"assets/specimens")
    parser.add_argument("--fonts",type=Path)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    create_assets(args.assets)
    if args.fonts and args.out:
        print(render_plan(args.assets/"specimen.json",args.fonts,args.out,preview=True,allow_demo=True))
