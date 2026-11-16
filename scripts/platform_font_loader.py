"""Fetch the exact v2.1.0 OFL font sources for the lightweight distribution."""
import hashlib
import os
import tempfile
import urllib.request
import zipfile
from pathlib import Path

URL = "https://github.com/StuPeter/travelogue-editor/releases/download/v2.1.0/travelogue-editor-v2.1.0.zip"
ARCHIVE_SHA256 = "f443ed2636c5ad54bab702c2a77673205be8090a74f942b769d89b66ddbf9773"
FONTS = {
    "SourceHanSerifCN-VF.ttf": "8e052cbcdbd0f03496c9ad05da7d57901549286d5efd30f3caf66a393f6c389b",
    "NotoSansSC-VF.ttf": "763146584cf0710223441356b4395e279021b0806c196614377a7a0174ae074a",
    "RobotoCondensed-VF.ttf": "dace262afcee68a5276f200d8026c57221735c0118ab5fda8c2c0d3dc409a8d0",
}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_font(filename, expected_hash):
    if FONTS.get(filename) != expected_hash:
        raise ValueError("This lightweight package has no download source for the requested font")
    base = Path(os.environ.get("TRAVELOGUE_FONT_CACHE", str(Path.home()/".cache/travelogue-editor/fonts"))).expanduser()
    base.mkdir(parents=True, exist_ok=True)
    target = base/filename
    if target.exists() and digest(target) == expected_hash:
        return target
    with tempfile.TemporaryDirectory(prefix="travelogue-fonts-", dir=base) as directory:
        temp = Path(directory)
        archive = temp/"original-release.zip"
        try:
            request = urllib.request.Request(URL, headers={"User-Agent":"Travelogue-Editor/2.1.0"})
            with urllib.request.urlopen(request,timeout=120) as response, archive.open("wb") as output:
                while True:
                    data=response.read(1024*1024)
                    if not data: break
                    output.write(data)
        except Exception as error:
            raise RuntimeError("Unable to download fonts; connect to GitHub or place the matching original fonts in assets/fonts.") from error
        if digest(archive) != ARCHIVE_SHA256:
            raise ValueError("Downloaded release checksum mismatch")
        with zipfile.ZipFile(archive) as source:
            for name, expected in FONTS.items():
                staged = temp/name
                with source.open("photo-story-magazine/assets/fonts/"+name) as src, staged.open("wb") as dst:
                    while True:
                        data=src.read(1024*1024)
                        if not data: break
                        dst.write(data)
                if digest(staged) != expected:
                    raise ValueError("Downloaded font checksum mismatch: "+name)
                os.replace(staged, base/name)
    return target
