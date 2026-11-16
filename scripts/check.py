"""Validate public sources, self-contained packaging, and optional behavioral tests."""
import argparse
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
import yaml
from repository import ROOT,META,SKILLS,assemble,inventory,sha,validate_links


def run(*arguments):
    subprocess.run([sys.executable,"-X","utf8",*map(str,arguments)],cwd=ROOT,check=True)


def check_sources():
    validate_links(ROOT)
    if (SKILLS/"photo-story-magazine/skills").exists():
        raise ValueError("Embedded cover must be generated, not hand-maintained")
    for name,version in META["skills"].items():
        root=SKILLS/name
        content=(root/"SKILL.md").read_text(encoding="utf-8")
        match=re.match(r"\A---\s*\n(.*?)\n---",content,re.S)
        if not match:
            raise ValueError("Invalid Skill frontmatter: "+name)
        metadata=yaml.safe_load(match[1])
        assert metadata["name"]==name
        assert metadata.get("description") and str(metadata["metadata"]["version"])==version
        agent=yaml.safe_load((root/"agents/openai.yaml").read_text(encoding="utf-8"))
        assert "$"+name in agent["interface"]["default_prompt"]
        for path in root.rglob("*"):
            if path.suffix in (".md",".py",".json",".yaml",".yml",".html") and "__pycache__" not in path.parts:
                text=path.read_text(encoding="utf-8")
                if re.search(r"(?i)[A-Z]:[\\/](?:Users|ProgramData|Windows)",text):
                    raise ValueError("Machine-specific path in "+str(path.relative_to(ROOT)))
    profile=json.loads((SKILLS/"photo-story-magazine/assets/default-fonts.json").read_text(encoding="utf-8"))
    for font in profile["fonts"].values():
        base=SKILLS/"photo-story-magazine/assets"
        assert sha(base/font["source"])==font["sha256"]
        assert (base/font["license"]).is_file()
    cover=SKILLS/"photo-magazine-cover/assets"
    for item in json.loads((cover/"examples-index.json").read_text(encoding="utf-8"))["examples"]:
        assert sha(cover/item["image"])==item["sha256"]
        assert (cover/item["recipe"]).is_file() and (cover/item["prompt"]).is_file()
    with tempfile.TemporaryDirectory(prefix="travelogue-package-check-") as temp:
        temp=Path(temp)
        for name in META["skills"]:
            assemble(name,temp/name)
        embedded=temp/"photo-story-magazine/skills/photo-magazine-cover"
        expected={("cover-guide.md" if p=="SKILL.md" else p):h for p,h in inventory(SKILLS/"photo-magazine-cover").items()}
        assert inventory(embedded)==expected
    print("Source, links, font/image hashes and self-contained packaging: passed",flush=True)


def test_behavior():
    main=SKILLS/"photo-story-magazine"
    run(SKILLS/"photo-magazine-cover/scripts/test_cover_prompt.py","-v")
    with tempfile.TemporaryDirectory(prefix="travelogue-tests-") as temp:
        temp=Path(temp)
        # Include the actual test text when producing a small portable font fixture.
        content="\n".join(p.read_text(encoding="utf-8") for p in main.rglob("*")
                          if p.suffix in (".py",".json") and "__pycache__" not in p.parts)
        corpus=temp/"test-content.txt"; corpus.write_text(content,encoding="utf-8")
        run(main/"scripts/prepare_fonts.py","--out",temp/"fonts","--text",corpus)
        run(main/"scripts/test_toolkit.py","--fonts",temp/"fonts/font-manifest.json","-v")
        run(ROOT/"tests/test_repository.py")
    print("Behavioral tests: passed",flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test",action="store_true")
    args=parser.parse_args()
    check_sources()
    if args.test:
        test_behavior()
