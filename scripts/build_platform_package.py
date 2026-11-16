"""Build a compact single-skill ZIP with on-demand verified fonts."""
import argparse
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path
from PIL import Image
from repository import ROOT, assemble, inventory, validate_links


def build(out):
    out=Path(out).resolve()
    out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists(): raise ValueError("Output already exists: "+str(out))
    with tempfile.TemporaryDirectory(prefix="platform-lite-") as directory:
        temp=Path(directory).resolve()
        stage=assemble("photo-story-magazine",temp/"photo-story-magazine")
        fonts=stage/"assets/fonts"
        for name in ("SourceHanSerifCN-VF.ttf","NotoSansSC-VF.ttf","RobotoCondensed-VF.ttf"):
            (fonts/name).unlink()
        loader=(ROOT/"scripts/platform_font_loader.py").read_bytes()
        (stage/"scripts/platform_font_loader.py").write_bytes(loader)
        prepare=stage/"scripts/prepare_fonts.py"
        text=prepare.read_text(encoding="utf-8")
        needle='        if sha(source) != spec["sha256"]:'
        if needle not in text: raise ValueError("Unexpected font preparation script")
        replacement=('        if not source.is_file():\n'
                     '            from platform_font_loader import ensure_font\n'
                     '            source = ensure_font(source.name, spec["sha256"])\n'
                     +needle)
        prepare.write_text(text.replace(needle,replacement),encoding="utf-8")
        cover=stage/"skills/photo-magazine-cover"
        examples=cover/"assets/examples"
        ids=["river-journey","architecture-close","stone-macro","mountain-depth"]
        for name in ids:
            png=examples/(name+".png")
            with Image.open(png) as image:
                image.convert("RGB").save(examples/(name+".jpg"),"JPEG",quality=92,subsampling=0,optimize=True)
            png.unlink()
        for path in cover.rglob("*"):
            if path.is_file() and path.suffix in (".md",".html",".py",".json"):
                data=path.read_text(encoding="utf-8")
                for name in ids: data=data.replace(name+".png",name+".jpg")
                path.write_text(data,encoding="utf-8")
        index=cover/"assets/examples-index.json"
        data=json.loads(index.read_text(encoding="utf-8"))
        for item in data["examples"]:
            image=cover/"assets"/item["image"]
            item["sha256"]=hashlib.sha256(image.read_bytes()).hexdigest()
            item["distribution_note"]="JPEG quality 92, original pixel dimensions; compressed reference for platform package."
        index.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
        guide=stage/"references/production-toolkit.md"
        text=guide.read_text(encoding="utf-8")
        text=text.replace("没有系统字体依赖，也不需要联网下载字体","没有系统字体依赖；轻量包首次准备字体时从固定的 GitHub 版本下载并校验，之后使用本地缓存")
        text=text.replace("包内保留未修改的三份 OFL 字体源及许可证","轻量包保留三份 OFL 许可证及字体哈希，字体源在首次使用时下载并校验")
        guide.write_text(text,encoding="utf-8")
        type_guide=stage/"references/type-and-components.md"
        text=type_guide.read_text(encoding="utf-8").replace("随包字体源", "按需下载的字体源")
        type_guide.write_text(text,encoding="utf-8")
        notices=stage/"THIRD_PARTY_NOTICES.md"
        text=notices.read_text(encoding="utf-8").replace(
            "The project bundles original font sources in skills/photo-story-magazine/assets/fonts/:",
            "The lightweight package downloads the original font sources on first use and includes their license notices in assets/fonts/:")
        notices.write_text(text,encoding="utf-8")
        entry=stage/"SKILL.md"
        text=entry.read_text(encoding="utf-8").replace("包内有字体源与实例化脚本","包内有字体实例化脚本；轻量包首次使用时下载并校验字体源")
        entry.write_text(text,encoding="utf-8")
        note=stage/"references/platform-package.md"
        note.write_text("# 平台轻量包\n\n此包含完整主 Skill、嵌套封面指导、四张原尺寸压缩参考图、排版程序及字体许可证。首次运行 prepare_fonts.py 时，从项目 v2.1.0 发布包下载约48 MB、校验发布包及字体 SHA-256，并缓存字体；后续复用缓存。无网络时，可将与 assets/default-fonts.json 哈希一致的字体放入 assets/fonts。图像生成工具仍需运行环境提供。\n",encoding="utf-8")
        entry.write_text(entry.read_text(encoding="utf-8").replace("## 按需读取","轻量版安装与字体说明见[平台包说明](references/platform-package.md)。\n\n## 按需读取",1),encoding="utf-8")
        validate_links(stage)
        with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zip:
            for rel in inventory(stage):
                zip.write(stage/rel,rel)
        with zipfile.ZipFile(out) as zip:
            if zip.testzip() is not None: raise ValueError("ZIP CRC failure")
            names=zip.namelist()
            if sum(n == "SKILL.md" or n.endswith("/SKILL.md") for n in names)!=1: raise ValueError("Unexpected Skill entry count")
        if out.stat().st_size>10_000_000: raise ValueError("Package exceeds 10 MB")
    return out


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    path=build(args.out)
    print(json.dumps({"path":str(path),"bytes":path.stat().st_size,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()},ensure_ascii=False,indent=2))
