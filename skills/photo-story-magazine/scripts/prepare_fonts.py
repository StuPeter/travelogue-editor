"""Prepare deterministic static fonts from bundled OFL sources. No system-font lookup."""
import argparse
import hashlib
import json
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools import subset

ROOT = Path(__file__).resolve().parent.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(profile, output, text_files=()):
    profile = Path(profile).resolve()
    cfg = json.loads(profile.read_text(encoding="utf-8"))
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    chars = None
    if text_files:
        chars = set(range(32, 127))
        for file in text_files:
            chars.update(map(ord, Path(file).read_text(encoding="utf-8-sig")))
    result = {"profile": cfg["name"], "roles": {}, "fonts": {}, "subset": chars is not None}
    for key, spec in cfg["fonts"].items():
        source = (profile.parent / spec["source"]).resolve()
        license_path = (profile.parent / spec["license"]).resolve()
        if sha(source) != spec["sha256"]:
            raise ValueError(f"Font source hash mismatch: {source}")
        font = TTFont(source)
        if "OS/2" in font and font["OS/2"].fsType & 0x0002:
            raise ValueError(f"Font embedding restricted: {source}")
        if chars is not None:
            options = subset.Options()
            options.hinting = False
            sub = subset.Subsetter(options=options)
            sub.populate(unicodes=chars)
            sub.subset(font)
        if "fvar" in font:
            axes = {a.axisTag: a.defaultValue for a in font["fvar"].axes}
            axes.update(spec["axes"])
            font = instantiateVariableFont(font, axes, inplace=True)
        # Modified instances have distinct primary names; retain copyright/license records.
        family = "FieldKit" + key
        names = {1: family, 2: "Regular", 3: family + "-1", 4: family, 6: family,
                 16: family, 17: "Regular"}
        for record in font["name"].names:
            if record.nameID in names:
                record.string = names[record.nameID].encode(record.getEncoding(), errors="replace")
        dest = output / (key + ".ttf")
        font.save(dest)
        font.close()
        license_dest = output / license_path.name
        license_dest.write_bytes(license_path.read_bytes())
        result["fonts"][key] = {
            "file": dest.name, "sha256": sha(dest), "source_sha256": spec["sha256"],
            "source_family": spec["family"], "axes": spec["axes"], "license": license_dest.name
        }
    result["roles"] = cfg["roles"]
    (output / "font-manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return output / "font-manifest.json"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=ROOT / "assets/default-fonts.json")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--text", type=Path, action="append", default=[],
                        help="Optional UTF-8 content files; omit for full glyph coverage.")
    args = parser.parse_args()
    print(prepare(args.profile, args.out, args.text))
