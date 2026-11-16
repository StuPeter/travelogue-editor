"""Build/install the two skills locally, preserving backups before updates."""
import argparse
import os
import shutil
import tempfile
from datetime import datetime,timezone
from pathlib import Path
from repository import META,IGNORE,assemble,inventory


def install(target):
    target=Path(target).expanduser().resolve(); target.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup=target.parent/"backups/travelogue-editor"/stamp
    with tempfile.TemporaryDirectory(prefix="travelogue-install-") as temp:
        stage=Path(temp)
        for name in META["skills"]:
            assemble(name,stage/name)
        # Back up all existing folders before changing either skill.
        for name in META["skills"]:
            previous=target/name
            if previous.exists():
                shutil.copytree(previous,backup/name,ignore=IGNORE)
        for name in META["skills"]:
            shutil.copytree(stage/name,target/name,dirs_exist_ok=True,ignore=IGNORE)
            actual=inventory(target/name)
            if not all(actual.get(path)==digest for path,digest in inventory(stage/name).items()):
                raise ValueError("Installed file verification failed: "+name)
    return target,backup if backup.exists() else None


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    home=Path(os.environ.get("CODEX_HOME",str(Path.home()/".codex")))
    parser.add_argument("--skills-dir",type=Path,default=home/"skills")
    args=parser.parse_args()
    target,backup=install(args.skills_dir)
    print("Installed:",target)
    if backup:
        print("Previous versions:",backup)
