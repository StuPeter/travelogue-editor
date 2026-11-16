"""Cover recipe and CLI behavior tests; these do not claim to test aesthetic judgement."""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from build_cover_prompt import build, validate

ROOT = Path(__file__).resolve().parent.parent


class CoverTests(unittest.TestCase):
    def recipe(self):
        return json.loads((ROOT/"assets/examples/stone-macro.json").read_text(encoding="utf-8"))

    def test_shipped_examples_and_v5_recipe_compile(self):
        paths=list((ROOT/"assets/examples").glob("*.json"))+[ROOT/"assets/railway-cover-recipe.json"]
        self.assertEqual(len(paths),5)
        for path in paths:
            recipe=json.loads(path.read_text(encoding="utf-8"))
            prompt=build(recipe)
            self.assertTrue(prompt)
            for item in recipe["text"]:
                self.assertIn(json.dumps(item["content"],ensure_ascii=False),prompt)
            self.assertEqual(prompt,path.with_suffix(".prompt.txt").read_text(encoding="utf-8")
                             if path.parent.name=="examples" else
                             (ROOT/"assets/railway-cover-prompt.txt").read_text(encoding="utf-8"))

    def test_publication_is_not_inherited(self):
        recipe=self.recipe(); recipe["publication"]="远行"
        masthead=next(t for t in recipe["text"] if t["role"]=="masthead")
        masthead.update(content="远行",lines=["远行"])
        prompt=build(recipe)
        self.assertIn("远行",prompt)
        self.assertNotIn("行见",prompt)

    def test_incomplete_art_direction_rejected(self):
        recipe=self.recipe(); del recipe["art_direction"]["camera"]
        with self.assertRaisesRegex(ValueError,"camera"): validate(recipe)

    def test_photographic_mode_requires_actual_content_role(self):
        recipe=self.recipe(); recipe["mode"]="photo-derivative"
        with self.assertRaisesRegex(ValueError,"content/edit input"): validate(recipe)
        recipe["inputs"]=[dict(id="Image 1",role="style-reference",description="A cover style only")]
        with self.assertRaisesRegex(ValueError,"content/edit input"): validate(recipe)

    def test_text_zones_and_exact_line_order(self):
        recipe=self.recipe(); recipe["text"][0]["box"]=[.90,.1,.5,.2]
        with self.assertRaisesRegex(ValueError,"inside the frame"): validate(recipe)
        recipe=self.recipe(); recipe["text"][1]["lines"]=["石上","时"]
        with self.assertRaisesRegex(ValueError,"concatenate"): validate(recipe)

    def test_occlusion_must_name_the_foreground(self):
        recipe=self.recipe(); recipe["text"][1]["occlusion"]={"enabled":True}
        with self.assertRaisesRegex(ValueError,"foreground"): validate(recipe)

    def test_incomplete_legacy_recipe_and_nonfinite_geometry(self):
        with self.assertRaisesRegex(ValueError,"schema_version"): validate({"publication":"行见"})
        recipe=self.recipe(); recipe["aspect_ratio"]=[float("nan"),4]
        with self.assertRaisesRegex(ValueError,"aspect_ratio"): validate(recipe)

    def test_cli_input_paths_and_no_overwrite(self):
        with tempfile.TemporaryDirectory(prefix="cover-portable-") as temp:
            temp=Path(temp); recipe=self.recipe(); recipe["mode"]="photo-layout"
            recipe["inputs"]=[dict(id="Image 1",role="content-reference",description="Actual local artwork",
                                  source="input with spaces.png")]
            plan=temp/"recipe.json"; plan.write_text(json.dumps(recipe,ensure_ascii=False),encoding="utf-8")
            command=[sys.executable,"-X","utf8",str(ROOT/"scripts/build_cover_prompt.py"),
                     "--recipe",str(plan),"--out",str(temp/"prompt.txt"),"--check-inputs"]
            missing=subprocess.run(command,cwd=temp,capture_output=True)
            self.assertNotEqual(missing.returncode,0)
            self.assertFalse((temp/"prompt.txt").exists())
            shutil.copy2(ROOT/"assets/examples/stone-macro.png",temp/"input with spaces.png")
            result=subprocess.run(command,cwd=temp,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            before=(temp/"prompt.txt").read_bytes()
            again=subprocess.run(command,cwd=temp,capture_output=True)
            self.assertNotEqual(again.returncode,0)
            self.assertEqual(before,(temp/"prompt.txt").read_bytes())


if __name__=="__main__":
    unittest.main()
