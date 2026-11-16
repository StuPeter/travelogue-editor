# Travelogue Editor

This repository is the canonical source for 旅图编辑 / Travelogue Editor.

- Edit the two canonical folders under skills/. Do not hand-maintain an embedded cover copy. scripts/build_release.py creates it for self-contained distributions.
- Keep Skill IDs photo-story-magazine and photo-magazine-cover stable; user-facing branding is Travelogue Editor.
- Start with the task's actual photos and content. Open the matching finished cover example; component demos are technical exercises.
- Preserve factual integrity, user originals, exact Chinese text and readable local contrast. Record generated/derived material separately.
- Do not commit user photos, reference magazine PDFs/screenshots, credentials, generated work folders or virtual environments.
- Bundled fonts retain their OFL licenses. Preserve source hashes and record explicit font changes.
- Run python scripts/check.py --test after changes affecting skills or programs. Use python scripts/build_release.py for release archives.
- Update project.json and the matching Skill metadata when bumping a version. Record user-visible changes in CHANGELOG.md.
- Keep validation scope accurate: structure/tests do not prove independent aesthetic transfer.
