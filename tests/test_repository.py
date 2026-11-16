"""Repository packaging and install behavior; no GitHub or user-profile mutations."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"scripts"))
from repository import META,SKILLS,assemble,inventory,validate_links
from install_local import install


class RepositoryTests(unittest.TestCase):
    def test_main_is_self_contained_and_source_is_single_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            result=assemble("photo-story-magazine",Path(temp)/"main")
            validate_links(result)
            self.assertTrue((result/"skills/photo-magazine-cover/cover-guide.md").is_file())
            self.assertNotIn("../photo-magazine-cover/SKILL.md",(result/"SKILL.md").read_text(encoding="utf-8"))
            self.assertFalse((SKILLS/"photo-story-magazine/skills").exists())
            self.assertTrue((result/"LICENSE").is_file())

    def test_install_preserves_previous_version_and_custom_files(self):
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/"profile/skills"
            old=target/"photo-story-magazine"; old.mkdir(parents=True)
            (old/"SKILL.md").write_text("previous local version",encoding="utf-8")
            (old/"local-note.txt").write_text("keep my note",encoding="utf-8")
            result,backup=install(target)
            self.assertEqual((backup/"photo-story-magazine/SKILL.md").read_text(encoding="utf-8"),"previous local version")
            self.assertEqual((result/"photo-story-magazine/local-note.txt").read_text(encoding="utf-8"),"keep my note")
            self.assertIn("旅图编辑",(result/"photo-story-magazine/SKILL.md").read_text(encoding="utf-8"))
            validate_links(result/"photo-story-magazine")
            self.assertTrue((result/"photo-magazine-cover/SKILL.md").is_file())


if __name__=="__main__":
    unittest.main(verbosity=2)
