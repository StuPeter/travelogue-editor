"""Compile explicit cover art direction; structure checks do not measure aesthetic quality."""
import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODES = {"photo-layout", "photo-derivative", "original-illustration"}
ROLES = {"masthead", "headline", "location", "secondary", "issue"}


def text_value(obj, key, where="recipe"):
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where}.{key} requires a concrete nonempty string")
    return value


def text_list(obj, key):
    value = obj.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(v,str) and v.strip() for v in value):
        raise ValueError(f"{key} requires explicit statements")
    return value


def numeric(v):
    return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)


def validate(recipe):
    if recipe.get("schema_version") != 2:
        raise ValueError("Expected schema_version 2; migrate prose recipes using supplied examples")
    for key in ("publication","topic","content_promise"):
        text_value(recipe,key)
    if recipe.get("mode") not in MODES:
        raise ValueError("Unsupported production mode")
    inputs = recipe.get("inputs")
    if not isinstance(inputs,list):
        raise ValueError("inputs must be a list")
    ids=[]
    for item in inputs:
        ids.append(text_value(item,"id","inputs"))
        text_value(item,"description","inputs")
        if item.get("role") not in ("edit-target","content-reference","style-reference"):
            raise ValueError("Each image requires a supported role")
    if len(set(ids))!=len(ids):
        raise ValueError("Input ids must be unique")
    if recipe["mode"]!="original-illustration" and not any(i["role"] in ("edit-target","content-reference") for i in inputs):
        raise ValueError("Photographic modes need a content/edit input")
    if recipe["mode"]=="photo-derivative" and not any(i["role"]=="edit-target" for i in inputs):
        raise ValueError("photo-derivative needs an edit-target")
    direction=recipe.get("direction",{})
    for key in ("route","why_this_image","rejected_route","why_rejected"):
        text_value(direction,key,"direction")
    visual=recipe.get("art_direction",{})
    for key in ("subject","camera","subject_scale","foreground","middle_ground",
                "background","eye_path","light","palette","texture"):
        text_value(visual,key,"art_direction")
    frame=recipe.get("frame",{})
    border=frame.get("width_ratio")
    if not numeric(border) or not 0<=border<=.12:
        raise ValueError("frame.width_ratio must be 0..0.12")
    text_value(frame,"color","frame")
    ratio=recipe.get("aspect_ratio")
    if not isinstance(ratio,list) or len(ratio)!=2 or not all(numeric(v) and v>0 for v in ratio):
        raise ValueError("aspect_ratio requires two positive numbers")
    items=recipe.get("text")
    if not isinstance(items,list) or not items:
        raise ValueError("text requires masthead and headline")
    roles=[]
    for item in items:
        if item.get("role") not in ROLES:
            raise ValueError("Unknown text role")
        roles.append(item["role"])
        for key in ("content","font_character","contrast_plan"):
            text_value(item,key,"text")
        box=item.get("box")
        if not isinstance(box,list) or len(box)!=4 or not all(numeric(v) for v in box):
            raise ValueError("Each text box needs normalized [x,y,w,h]")
        x,y,w,h=box
        if min(x,y)<border or min(w,h)<=0 or x+w>1-border+1e-8 or y+h>1-border+1e-8:
            raise ValueError("Text box must remain inside the frame")
        lines=item.get("lines")
        if not isinstance(lines,list) or not lines or not all(isinstance(v,str) and v for v in lines) or "".join(lines)!=item["content"]:
            raise ValueError("Text lines must concatenate exactly to content")
        occ=item.get("occlusion",{})
        if not isinstance(occ.get("enabled"),bool):
            raise ValueError("Specify whether text occlusion is enabled")
        if occ["enabled"]:
            text_value(occ,"foreground","occlusion")
            text_value(occ,"protected_features","occlusion")
    if roles.count("masthead")!=1 or roles.count("headline")!=1:
        raise ValueError("Exactly one masthead and one headline required")
    for key in ("factual_anchors","allowed_changes","forbidden_changes","review_checks"):
        text_list(recipe,key)
    return recipe


def build(recipe,preset=None):
    validate(recipe)
    preset=preset or json.loads((ROOT/"assets/editorial-photography-defaults.json").read_text(encoding="utf-8"))
    blocks=[
        "Use case: original editorial photography magazine cover, ONE flat finished artwork, NOT a mockup.",
        f'Output aspect ratio: {recipe["aspect_ratio"][0]}:{recipe["aspect_ratio"][1]}.',
        "Original publication for THIS issue: "+recipe["publication"],
        "Topic: "+recipe["topic"]+"\nEditorial promise: "+recipe["content_promise"],
        "Production mode: "+recipe["mode"],
        "Art-direction baseline:\n"+"\n".join(preset[k] for k in ("medium","identity","type","layering","composition")),
        "Image inputs:\n"+("\n".join(f'{i["id"]}: {i["role"]}; {i["description"]}' for i in recipe["inputs"]) or
                            "No supplied source photograph. Create original concept artwork; do not imply actual documentary evidence."),
        "Composition choice:\n"+json.dumps(recipe["direction"],ensure_ascii=False),
        "Concrete camera, subject, planes and eye path:\n"+json.dumps(recipe["art_direction"],ensure_ascii=False),
        "Frame (width ratio relative to full cover width): "+json.dumps(recipe["frame"],ensure_ascii=False),
        "Preserve anchors: "+"; ".join(recipe["factual_anchors"]),
        "EXACT text with normalized zones [x,y,w,h] measured from top-left of whole cover:"
    ]
    blocks.extend(json.dumps(item,ensure_ascii=False) for item in recipe["text"])
    blocks.extend([
        "Allowed changes: "+"; ".join(recipe["allowed_changes"]),
        "Do not add/change: "+"; ".join(recipe["forbidden_changes"]),
        "Visual acceptance checks: "+"; ".join(recipe["review_checks"]),
        "Avoid: "+"; ".join(preset["avoid"]),
        "Render ONLY the listed text strings. No extra copy, watermark or official National Geographic masthead/logo. Correct Chinese spelling and recognizable glyphs outrank occlusion."
    ])
    return "\n\n".join(blocks)+"\n"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--check-inputs",action="store_true")
    args=parser.parse_args()
    try:
        recipe=json.loads(args.recipe.read_text(encoding="utf-8-sig"))
        prompt=build(recipe)
        if args.check_inputs:
            for item in recipe["inputs"]:
                if not item.get("source") or not (args.recipe.parent/item["source"]).is_file():
                    raise ValueError("Missing actual input file for "+item["id"])
        if args.out.exists():
            raise ValueError("Use a new output path; approved prompts are not overwritten")
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(prompt,encoding="utf-8")
        print(args.out)
    except (ValueError,KeyError) as exc:
        parser.exit(2,f"Art direction rejected: {exc}\n")


if __name__=="__main__":
    main()
