import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from validate_script import validate_text  # noqa: E402


VALID_EPISODE = """\
第1集
1-1 日 内 客厅
人物：林夏、周明
△ 林夏握紧门把手。
林夏：你终于来了。
△ 门外突然传来一声枪响！
"""


class ValidateScriptTests(unittest.TestCase):
    def test_valid_episode_has_no_issues(self) -> None:
        self.assertEqual([], validate_text(VALID_EPISODE))

    def test_missing_scene_heading_is_an_error(self) -> None:
        script = """\
第1集
人物：林夏
△ 林夏抬起头。
林夏：是谁？
"""

        issues = validate_text(script)

        self.assertTrue(
            any(issue["code"] == "E002" and issue["severity"] == "error" for issue in issues)
        )
        self.assertIn(
            "缺少场景标题",
            next(issue["message"] for issue in issues if issue["code"] == "E002"),
        )

    def test_missing_character_column_is_an_error(self) -> None:
        script = """\
第1集
1-1 夜 外 天台
△ 林夏走到天台边缘。
林夏：别过来！
"""

        issues = validate_text(script)

        self.assertTrue(
            any(issue["code"] == "E003" and issue["severity"] == "error" for issue in issues)
        )
        self.assertIn(
            "缺少“人物：”栏",
            next(issue["message"] for issue in issues if issue["code"] == "E003"),
        )

    def test_weak_episode_ending_is_a_warning(self) -> None:
        script = """\
第1集
1-1 日 内 餐厅
人物：林夏、周明
△ 两人坐下吃饭。
林夏：今天的菜还不错。
△ 两人吃完饭，各自回家。
"""

        issues = validate_text(script)

        self.assertTrue(
            any(issue["code"] == "W001" and issue["severity"] == "warning" for issue in issues)
        )
        self.assertFalse(any(issue["severity"] == "error" for issue in issues))

    def test_cli_json_and_exit_codes_distinguish_pass_warning_and_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            valid = root / "valid.md"
            weak = root / "weak.txt"
            invalid = root / "invalid.md"
            valid.write_text(VALID_EPISODE, encoding="utf-8")
            weak.write_text(
                "第1集\n1-1 日 内 餐厅\n人物：甲\n△ 甲吃完饭后回家。\n",
                encoding="utf-8",
            )
            invalid.write_text("第1集\n△ 无场景标题。\n", encoding="utf-8")

            def run(path: Path) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [sys.executable, str(SCRIPTS_DIR / "validate_script.py"), "--json", str(path)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )

            passed = run(valid)
            warned = run(weak)
            failed = run(invalid)

            self.assertEqual(0, passed.returncode)
            self.assertEqual("pass", json.loads(passed.stdout)["status"])
            self.assertEqual(1, warned.returncode)
            self.assertEqual("warning", json.loads(warned.stdout)["status"])
            self.assertEqual(2, failed.returncode)
            failed_payload = json.loads(failed.stdout)
            self.assertEqual("error", failed_payload["status"])
            self.assertEqual(
                ["缺少场景标题（如“1-1 日 内 客厅”）。", "缺少“人物：”栏。"],
                [
                    issue["message"].removeprefix("第1个剧集")
                    for issue in failed_payload["issues"]
                    if issue["severity"] == "error"
                ],
            )

    def test_cli_writes_utf8_even_when_process_environment_requests_gbk(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "中文错误.md"
            script_path.write_text("第1集\n△ 无场景标题。\n", encoding="utf-8")
            environment = dict(__import__("os").environ)
            environment["PYTHONIOENCODING"] = "gbk"

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "validate_script.py"),
                    "--json",
                    str(script_path),
                ],
                capture_output=True,
                env=environment,
            )

            self.assertEqual(2, result.returncode)
            stdout = result.stdout.decode("utf-8")
            payload = json.loads(stdout)
            self.assertEqual("error", payload["status"])
            self.assertIn("缺少场景标题", stdout)
            self.assertIn("人物：", stdout)


if __name__ == "__main__":
    unittest.main()
