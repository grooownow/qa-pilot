import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from ui_inventory import inventory, main


class InventoryTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.ui = self.root / "src" / "ui"
        self.ui.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, rel, text=""):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def run_inv(self, aliases=None):
        return inventory(self.root, [self.ui], aliases or {})

    def by_name(self, result):
        return {c["name"]: c for c in result["components"]}

    def test_atom_and_composition(self):
        self.write("src/ui/Button.tsx", "export const Button = () => <button/>;\n")
        self.write("src/ui/Dialog.tsx", "import { Button } from './Button';\nexport const Dialog = () => <Button/>;\n")
        c = self.by_name(self.run_inv())
        self.assertEqual(c["Button"]["kind"], "atom")
        self.assertEqual(c["Dialog"]["kind"], "composition")
        self.assertEqual(c["Dialog"]["uses"], ["Button"])

    def test_barrel_resolution(self):
        self.write("src/ui/Button.tsx", "export const Button = () => <button/>;\n")
        self.write("src/ui/Input.tsx", "export const Input = () => <input/>;\n")
        self.write("src/ui/index.ts", "export { Button } from './Button';\nexport * from './Input';\n")
        self.write("src/ui/Form.tsx", "import { Button, Input } from './';\nexport const Form = () => <form/>;\n")
        r = self.run_inv()
        c = self.by_name(r)
        self.assertEqual(c["Form"]["uses"], ["Button", "Input"])
        self.assertNotIn("index", c)
        self.assertEqual(r["summary"]["components"], 3)

    def test_alias_and_unresolved(self):
        self.write("src/ui/Button.tsx", "export const Button = () => <button/>;\n")
        self.write("src/ui/Card.tsx",
                   "import React from 'react';\nimport { Button } from '@/ui/Button';\n"
                   "import x from \"@/lib/missing\";\nexport const Card = () => <div/>;\n")
        r = self.run_inv({"@/ui": self.root / "src" / "ui", "@/lib": self.root / "src" / "lib"})
        c = self.by_name(r)
        self.assertEqual(c["Card"]["uses"], ["Button"])
        self.assertEqual(len(r["unresolved"]), 1)
        self.assertEqual(r["unresolved"][0]["import"], "@/lib/missing")

    def test_cycle_terminates(self):
        self.write("src/ui/A.tsx", "import { B } from './B';\nexport const A = () => <B/>;\n")
        self.write("src/ui/B.tsx", "import { A } from './A';\nexport const B = () => <A/>;\n")
        c = self.by_name(self.run_inv())
        self.assertEqual(c["A"]["kind"], "composition")
        self.assertEqual(c["B"]["kind"], "composition")

    def test_barrel_cycle_terminates(self):
        self.write("src/ui/index.ts", "export * from './A';\nexport * from './index';\n")
        self.write("src/ui/A.tsx", "import { A } from './';\nexport const A = () => <i/>;\n")
        c = self.by_name(self.run_inv())
        self.assertEqual(c["A"]["uses"], [])

    def test_stories_and_play(self):
        self.write("src/ui/Button.tsx", "export const Button = () => <button/>;\n")
        self.write("src/ui/Button.stories.tsx",
                   "export const Primary = {};\nexport const Clicked = { play: async () => {} };\n")
        self.write("src/ui/Button.test.tsx", "test('x', () => {});\n")
        r = self.run_inv()
        c = self.by_name(r)
        self.assertEqual(c["Button"]["stories"], ["Primary", "Clicked"])
        self.assertEqual(c["Button"]["play_stories"], ["Clicked"])
        self.assertEqual(len(c["Button"]["tests"]), 1)
        self.assertEqual(len(r["components"]), 1)

    def test_index_dir_naming(self):
        self.write("src/ui/Select/index.tsx", "export const Select = () => <select/>;\n")
        self.assertIn("Select", self.by_name(self.run_inv()))

    def test_cli_bad_lib_exits_2(self):
        with redirect_stdout(StringIO()):
            self.assertEqual(main(["ui_inventory.py", "--root", str(self.root), "--lib", "nope"]), 2)
            self.assertEqual(main(["ui_inventory.py", "--root", str(self.root)]), 2)

    def test_cli_json(self):
        self.write("src/ui/Button.tsx", "export const Button = () => <button/>;\n")
        out = StringIO()
        with redirect_stdout(out):
            code = main(["ui_inventory.py", "--root", str(self.root), "--lib", "src/ui", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue())["summary"]["atoms"], 1)


if __name__ == "__main__":
    unittest.main()
