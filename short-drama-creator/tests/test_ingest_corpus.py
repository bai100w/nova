import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from docx import Document


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ingest_corpus import ingest_corpus  # noqa: E402


def make_docx(path: Path, paragraphs: list[str]) -> None:
    document = Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    document.save(path)


class IngestCorpusTests(unittest.TestCase):
    def test_extracts_docx_and_generates_required_catalog_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "sources"
            output = root / "library"
            source.mkdir()
            script_path = source / "试播集.docx"
            paragraphs = ["第1集", "1-1 日 内 客厅", "人物：林夏、周明", "△ 林夏推门而入。"]
            make_docx(script_path, paragraphs)

            catalog = ingest_corpus(source, output)

            self.assertEqual(1, len(catalog))
            record = catalog[0]
            self.assertEqual("试播集", record["title"])
            self.assertEqual("试播集.docx", record["source_file"])
            self.assertEqual("docx", record["source_format"])
            self.assertEqual(hashlib.sha256(script_path.read_bytes()).hexdigest(), record["sha256"])
            self.assertEqual(1, record["episode_count"])
            self.assertGreaterEqual(record["characters"], len("".join(paragraphs)))
            self.assertEqual(len(paragraphs), record["lines"])
            self.assertRegex(record["source_id"], r"^[0-9a-f]{16}$")
            self.assertTrue(record["imported_at"].endswith("Z"))

            catalog_path = output / "catalog.json"
            self.assertEqual(catalog, json.loads(catalog_path.read_text(encoding="utf-8")))
            text_path = output / record["text_path"]
            self.assertEqual("\n".join(paragraphs) + "\n", text_path.read_text(encoding="utf-8"))

    def test_source_id_is_stable_and_repeated_ingestion_does_not_duplicate_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "sources"
            output = root / "library"
            source.mkdir()
            make_docx(source / "同一剧本.docx", ["第1集", "1-1 夜 外 天台", "人物：甲、乙"])

            first = ingest_corpus(source, output)
            second = ingest_corpus(source, output)

            self.assertEqual(1, len(second))
            self.assertEqual(first[0]["source_id"], second[0]["source_id"])
            self.assertEqual(first[0]["imported_at"], second[0]["imported_at"])
            self.assertEqual(
                [first[0]["text_path"]],
                [path.relative_to(output).as_posix() for path in (output / "corpus").glob("*.txt")],
            )

    def test_missing_source_directory_raises_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "not-there"
            with self.assertRaisesRegex(FileNotFoundError, "Source directory does not exist"):
                ingest_corpus(missing, Path(temp_dir) / "library")

    def test_cli_reports_missing_source_directory_with_usage_error_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            command = [
                sys.executable,
                str(SCRIPTS_DIR / "ingest_corpus.py"),
                "--source-dir",
                str(Path(temp_dir) / "missing"),
                "--output-dir",
                str(Path(temp_dir) / "library"),
            ]
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")

            self.assertEqual(2, result.returncode)
            self.assertIn("Source directory does not exist", result.stderr)

    def test_cli_writes_utf8_metadata_for_chinese_source_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "剧本来源"
            output = root / "剧本库"
            source.mkdir()
            make_docx(
                source / "试播集.docx",
                ["第1集", "1-1 夜 外 天台", "人物：甲、乙", "△ 门外突然传来枪响！"],
            )
            environment = dict(__import__("os").environ)
            environment["PYTHONIOENCODING"] = "gbk"

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "ingest_corpus.py"),
                    "--source-dir",
                    str(source),
                    "--output-dir",
                    str(output),
                ],
                capture_output=True,
                env=environment,
            )

            self.assertEqual(0, result.returncode)
            self.assertEqual(
                "已导入 1 个剧本来源。\n",
                result.stdout.decode("utf-8"),
            )
            catalog_text = (output / "catalog.json").read_text(encoding="utf-8")
            self.assertIn("试播集.docx", catalog_text)


if __name__ == "__main__":
    unittest.main()
