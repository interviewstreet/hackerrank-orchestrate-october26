"""No key-like strings in code/, and .env can never enter code.zip (AGENTS.md 4.4, 6.9)."""

import re
import tempfile
import unittest
import zipfile
from pathlib import Path

import config
import helpers  # noqa: F401
import package

TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".toml", ".cfg", ".ini", ".yaml", ".yml", ".example"}
KEY_LIKE = re.compile(
    r"\bsk-[A-Za-z0-9_-]{16,}"                                    # OpenAI-style secret keys
    r"|\b(?:api[_-]?key|token|secret|password)\s*[:=]\s*['\"][A-Za-z0-9_\-./+]{16,}['\"]"
    r"|\bBearer\s+[A-Za-z0-9_\-.]{20,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----", re.I)


def _text_files(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and (
                path.suffix in TEXT_SUFFIXES or path.name.startswith(".env")):
            yield path


class SecretScanTest(unittest.TestCase):
    def test_no_key_like_strings_in_code(self):
        hits = []
        for path in _text_files(config.CODE_DIR):
            for n, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if KEY_LIKE.search(line):
                    hits.append(f"{path.relative_to(config.REPO_ROOT)}:{n}")
        self.assertEqual(hits, [])

    def test_configured_key_value_appears_in_no_committed_text(self):
        key = config.api_key()
        if not key:
            self.skipTest("no key configured")
        files = [*_text_files(config.CODE_DIR), config.REPO_ROOT / "log.txt", config.REPO_ROOT / ".env.example"]
        leaked = [str(p.relative_to(config.REPO_ROOT)) for p in files
                  if p.is_file() and key in p.read_text(encoding="utf-8", errors="replace")]
        self.assertEqual(leaked, [])   # the value itself is never printed

    def test_env_example_has_placeholders_only(self):
        values = config._read_env_file(config.REPO_ROOT / ".env.example")
        self.assertEqual(values.get("ZENMUX_API_KEY"), "")
        self.assertEqual(values.get("ZENMUX_BASE_URL"), "https://zenmux.ai/api/v1")

    def test_env_file_loader_and_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text('# comment\nexport A="one"\nB=two\n\nC\n', encoding="utf-8")
            self.assertEqual(config._read_env_file(path), {"A": "one", "B": "two"})


class PackagingTest(unittest.TestCase):
    def test_env_files_are_forbidden(self):
        for rel in (".env", "code/.env", "code/.env.local", "evaluation/x.zip", "code/dataset/a.csv",
                    "code/.cache/llm/k.json", "code/__pycache__/m.pyc"):
            with self.subTest(rel):
                self.assertTrue(package.forbidden(Path(rel)))
        self.assertEqual(package.forbidden(Path("code/.env.example")), "")
        self.assertEqual(package.forbidden(Path("code/main.py")), "")

    def test_check_refuses_env_even_if_listed(self):
        with self.assertRaises(package.PackagingError):
            package.check([Path("code/main.py"), Path("code/.env")])

    def test_archive_never_contains_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "code").mkdir()
            (root / "code" / "main.py").write_text("print(1)\n", encoding="utf-8")
            (root / "code" / ".env").write_text("ZENMUX_API_KEY=placeholder\n", encoding="utf-8")
            (root / ".env").write_text("ZENMUX_API_KEY=placeholder\n", encoding="utf-8")
            out = root / "code.zip"
            self.assertEqual(package.build(out, root), 1)
            with zipfile.ZipFile(out) as archive:
                self.assertEqual(archive.namelist(), ["code/main.py"])


if __name__ == "__main__":
    unittest.main()
