"""Shared source/distribution helpers. Run from any working directory."""
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
META=json.loads((ROOT/"project.json").read_text(encoding="utf-8"))
SKILLS=ROOT/"skills"
IGNORE=shutil.ignore_patterns("__pycache__","*.pyc",".venv","venv","work","output","dist","build",".cache","*.log",".env",".env.*")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inventory(root):
    return {p.relative_to(root).as_posix():sha(p) for p in sorted(Path(root).rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and p.suffix!=".pyc"}


def validate_links(root, boundary=None):
    root=Path(root).resolve(); boundary=Path(boundary or root).resolve()
    for doc in root.rglob("*.md"):
        if any(part in {".git",".venv","venv","work","output","dist","build",".cache","__pycache__"} for part in doc.relative_to(root).parts):
            continue
        for link in re.findall(r"\]\(([^)]+)\)",doc.read_text(encoding="utf-8")):
            if "://" in link or link.startswith(("#","mailto:")):
                continue
            target=(doc.parent/link.split("#")[0]).resolve()
            if not target.is_relative_to(boundary) or not target.exists():
                raise ValueError(f"Broken/outside link: {doc.relative_to(root)} -> {link}")


def assemble(name,dest):
    """Build a self-contained installable skill; canonical sources remain separate."""
    dest=Path(dest)
    if name not in META["skills"]:
        raise ValueError("Unknown skill: "+name)
    shutil.copytree(SKILLS/name,dest,ignore=IGNORE)
    if name=="photo-story-magazine":
        embedded=dest/"skills/photo-magazine-cover"
        shutil.copytree(SKILLS/"photo-magazine-cover",embedded,ignore=IGNORE)
        (embedded/"SKILL.md").rename(embedded/"cover-guide.md")
        rewrites={
            "SKILL.md":("../photo-magazine-cover/SKILL.md","skills/photo-magazine-cover/cover-guide.md"),
            "references/visual-specimens.md":("../../photo-magazine-cover/SKILL.md","../skills/photo-magazine-cover/cover-guide.md")}
        for relative,(old,new) in rewrites.items():
            path=dest/relative; content=path.read_text(encoding="utf-8")
            if old not in content:
                raise ValueError("Missing expected source link in "+relative)
            path.write_text(content.replace(old,new),encoding="utf-8")
    for name in ("LICENSE","THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT/name,dest/name)
    validate_links(dest)
    return dest
