"""Create versioned self-contained skill archives and verify their bytes."""
import argparse
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path
from repository import ROOT,META,assemble,inventory,sha


def archive(source,target):
    if target.exists():
        raise ValueError("Refusing to overwrite release: "+str(target))
    files=inventory(source)
    with zipfile.ZipFile(target,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zip:
        for relative in files:
            zip.write(source/relative,relative)
    with zipfile.ZipFile(target) as zip:
        if zip.testzip() is not None:
            raise ValueError("ZIP CRC check failed")
        for relative,digest in files.items():
            if hashlib.sha256(zip.read(relative)).hexdigest()!=digest:
                raise ValueError("Archive mismatch: "+relative)
    return {"file":target.name,"bytes":target.stat().st_size,"sha256":sha(target)}


def build(output):
    output=Path(output).resolve(); output.mkdir(parents=True,exist_ok=True)
    bundle=output/f'travelogue-editor-v{META["version"]}.zip'
    cover_zip=output/f'photo-magazine-cover-v{META["skills"]["photo-magazine-cover"]}.zip'
    manifest_path=output/f'release-v{META["version"]}.json'
    checksums=output/"SHA256SUMS.txt"
    if any(p.exists() for p in (bundle,cover_zip,manifest_path,checksums)):
        raise ValueError("Use a new output directory; existing releases are preserved")
    with tempfile.TemporaryDirectory(prefix="travelogue-release-") as temp:
        stage=Path(temp)/"bundle"; stage.mkdir()
        for name in META["skills"]:
            assemble(name,stage/name)
        for name in ("LICENSE","THIRD_PARTY_NOTICES.md"):
            (stage/name).write_bytes((ROOT/name).read_bytes())
        (stage/"INSTALL.md").write_text(
            "# Travelogue Editor / 旅图编辑\n\n"
            "Copy both skill directories into your assistant's skill directory. "
            "The main skill embeds its own cover resources and can also be installed alone.\n\n"
            "Skill IDs: photo-story-magazine and photo-magazine-cover. "
            "Read the main skill's references/production-toolkit.md for Python/PDF setup.\n"
            "Repository: "+META["repository"]+"\n",encoding="utf-8")
        manifest={"project":META,"files_sha256":inventory(stage)}
        (stage/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
        cover_stage=Path(temp)/"cover"; cover_stage.mkdir()
        assemble("photo-magazine-cover",cover_stage/"photo-magazine-cover")
        results=[archive(stage,bundle),archive(cover_stage,cover_zip)]
    manifest_path.write_text(json.dumps({"project":META,"archives":results},ensure_ascii=False,indent=2),encoding="utf-8")
    checksums.write_text("".join(f'{r["sha256"]}  {r["file"]}\n' for r in results),encoding="ascii")
    return results


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=ROOT/"dist")
    parser.add_argument("--expected-tag",help="Fail when the pushed tag differs from project.json")
    args=parser.parse_args()
    if args.expected_tag and args.expected_tag!="v"+META["version"]:
        parser.error("Tag does not match project.json")
    print(json.dumps(build(args.out),ensure_ascii=False,indent=2))
