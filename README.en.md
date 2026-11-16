# Travelogue Editor · 旅图编辑

**Turn travel photographs into an editorial magazine with stories, explainers and considered page design.**

[中文](README.md) · [Releases](https://github.com/StuPeter/travelogue-editor/releases) · [Development](docs/development.md)

Travelogue Editor combines two AI-assistant skills with reusable PDF production tools. The assistant reviews local photographs, develops an editorial direction, researches context, writes the story, designs a cover and representative spread, and produces the issue.

## Skills

| Stable Skill ID | Purpose |
|---|---|
| `photo-story-magazine` | Issue planning, writing, explainers, typography and PDF production |
| `photo-magazine-cover` | Standalone cover art direction and production |

Skill instructions and detailed references are primarily in Chinese. Sample publication names are illustrative; they are not mandatory names for your magazine.

## Install

Download a full bundle or the platform-lite ZIP from [Releases](https://github.com/StuPeter/travelogue-editor/releases), or clone the repository and run:

The full bundle includes font sources. The platform-lite ZIP contains `SKILL.md` at its root and is built under 10 MB; it downloads and verifies the pinned approximately 48 MB font-source release on first font preparation, then caches the fonts. A standalone cover package is also available.

```sh
python scripts/install_local.py
```

The installer defaults to `CODEX_HOME/skills`, or `~/.codex/skills` when unset. Use `--skills-dir` for another assistant directory. Existing installations are backed up before updates.

Python PDF tools require Python 3.11+:

```sh
python -m pip install -r requirements.txt
```

An assistant with local-file and command-execution access is needed for the full workflow. Image generation is optional for photographic typesetting, and needed for generative cover artwork. Preview rendering requires Poppler's `pdftoppm`.

## Included

- Focus-aware crops, polygon image windows, editable text, layered images, quotation frames and page navigation.
- Single-page and spread PDF output with embedded fonts.
- Bundled OFL font sources, fixed weight/role profiles and preparation/subsetting scripts.
- Four original AI-generated photographic-style cover examples with full recipes and prompts.
- Original layout teaching specimens and reconstructable JSON plans.
- Editorial writing, narrative structure, typography and explainer-planning references.

Finished cover examples guide art direction. Geometric teaching specimens only demonstrate layout components and require an explicit demo flag.

## Contribute

```sh
python -m pip install -r requirements-dev.txt
python scripts/check.py --test
python scripts/build_release.py --out dist
```

Only the two canonical skill folders are maintained. The release builder embeds cover resources into the main distribution automatically. Automated checks and new-subject generation trials do not establish independent full-skill aesthetic transfer.

Original code/documentation use the [MIT License](LICENSE). Fonts retain their OFL licenses; see [third-party notices](THIRD_PARTY_NOTICES.md).
