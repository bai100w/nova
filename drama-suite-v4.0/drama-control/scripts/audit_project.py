#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""剧集项目与 skill 套组的结构检查。只用 Python 标准库，3.8 以上可运行。

用法：
  python audit_project.py --root <项目根目录>      检查项目资料库
  python audit_project.py --skills <skills 目录>   检查套组结构和引用
  两个参数可以同时给。

没有 Python 时，按下面的检查项人工核对。

项目检查项：
  1. 项目根目录下有 剧集数据库/（或旧名 漫剧数据库/）和其中的 项目索引.md
  2. 项目索引里出现全部十类槽位的名称
  3. 项目索引里登记了形态、时长、题材、流程档位
  4. 资料库里有 制作状态.md
  5. 资产登记.json 存在时：每个文件在项目内、能找到、SHA256 与登记一致
  6. gates/ 下的关卡记录各有几份

套组检查项：
  1. 每个 drama-* 目录有 SKILL.md，文件头的 name 与目录名一致，有 description
  2. description 里没有半角引号和“半角冒号加空格”（部分工具的 YAML 解析会出错）
  3. SKILL.md 正文不超过 200 行（超过说明该把内容移进 references）
  4. 各 .md 文件里的本地相对链接都能找到目标文件

本脚本只查结构和文件，不代替看片、听片和评审。
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

DB_NAMES = ["剧集数据库", "漫剧数据库"]
SLOTS = [
    "创作方向与档案", "世界观与剧情机制", "剧情与集数", "人物与关系", "资产与版本",
    "尺寸与连续性", "影像与声音参数", "生成配置", "制作状态", "学习与变更",
]
CHOICES = ["形态", "时长", "题材", "流程档位"]
GATES = ["资产关卡", "预演关卡", "终检"]
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
MAX_SKILL_LINES = 200


def read_text(path):
    return path.read_text(encoding="utf-8-sig")


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def inside(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def audit_project(root):
    errors, warnings, info = [], [], {}
    db = next((root / n for n in DB_NAMES if (root / n).is_dir()), None)
    if db is None:
        return {"errors": ["找不到资料库文件夹：" + " 或 ".join(DB_NAMES)], "warnings": [], "info": {}}
    info["资料库"] = db.name
    if db.name != DB_NAMES[0]:
        warnings.append("资料库使用旧名 " + db.name + "，可继续使用")

    index = db / "项目索引.md"
    if not index.is_file():
        errors.append("缺少 项目索引.md")
        text = ""
    else:
        text = read_text(index)
        for slot in SLOTS:
            if slot not in text:
                errors.append("项目索引缺少槽位：" + slot + "（内容未定也要保留并标待定）")
        for choice in CHOICES:
            if choice not in text:
                warnings.append("项目索引未登记：" + choice)

    if not any(db.rglob("制作状态.md")):
        warnings.append("资料库里没有 制作状态.md")

    registry = db / "资产登记.json"
    if registry.is_file():
        try:
            assets = json.loads(read_text(registry)).get("assets", [])
        except (ValueError, AttributeError):
            assets = []
            errors.append("资产登记.json 无法解析，或顶层不是含 assets 列表的对象")
        checked = 0
        for item in assets:
            rel = item.get("path", "") if isinstance(item, dict) else ""
            target = (root / rel).resolve()
            if not rel or not inside(target, root.resolve()):
                errors.append("资产路径不在项目内：" + (rel or "<空>"))
            elif not target.is_file():
                errors.append("资产文件不存在：" + rel)
            elif item.get("sha256") and sha256(target) != item["sha256"]:
                errors.append("资产文件与登记的 SHA256 不一致：" + rel)
            elif not item.get("sha256"):
                warnings.append("资产未登记 SHA256：" + rel)
            checked += 1
        info["已登记资产数"] = checked
    else:
        warnings.append("没有 资产登记.json，未做资产文件核对")

    gates_dir = db / "gates"
    counts = dict.fromkeys(GATES, 0)
    if gates_dir.is_dir():
        for record in gates_dir.rglob("*.md"):
            body = read_text(record)
            for gate in GATES:
                if re.search(r"关卡[：:]\s*" + re.escape(gate), body):
                    counts[gate] += 1
    info["关卡记录数"] = counts
    return {"errors": errors, "warnings": warnings, "info": info}


def audit_skills(skills):
    errors, warnings, info = [], [], {}
    modules = sorted(p for p in skills.iterdir() if p.is_dir() and p.name.startswith("drama-"))
    info["模块"] = [m.name for m in modules]
    if not modules:
        errors.append("目录下没有 drama-* 模块")
    links = 0
    for mod in modules:
        entry = mod / "SKILL.md"
        if not entry.is_file():
            errors.append(mod.name + "：缺少 SKILL.md")
            continue
        text = read_text(entry)
        fm = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
        if not fm:
            errors.append(mod.name + "：SKILL.md 没有文件头")
        else:
            head = fm.group(1)
            name = re.search(r"^name:\s*(.+?)\s*$", head, re.M)
            desc = re.search(r"^description:\s*(.+?)\s*$", head, re.M)
            if not name or name.group(1) != mod.name:
                errors.append(mod.name + "：文件头的 name 与目录名不一致")
            if not desc:
                errors.append(mod.name + "：文件头缺少 description")
            elif re.search(r"[\"']|: ", desc.group(1)):
                warnings.append(mod.name + "：description 含半角引号或“冒号加空格”，部分工具可能解析失败")
            body_lines = text[fm.end():].count("\n")
            if body_lines > MAX_SKILL_LINES:
                warnings.append("%s：SKILL.md 正文 %d 行，建议把细节移进 references" % (mod.name, body_lines))
        for doc in mod.rglob("*.md"):
            for match in LINK.finditer(read_text(doc)):
                ref = match.group(1).split("#")[0]
                if not ref or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", ref) or "<" in ref:
                    continue
                links += 1
                if not (doc.parent / ref).exists():
                    errors.append("%s：%s 里的链接找不到目标 %s" % (mod.name, doc.relative_to(mod), ref))
    info["已检查的本地链接数"] = links
    return {"errors": errors, "warnings": warnings, "info": info}


def main():
    parser = argparse.ArgumentParser(description="剧集项目与 skill 套组的结构检查")
    parser.add_argument("--root", type=Path, help="项目根目录")
    parser.add_argument("--skills", type=Path, help="skills 目录")
    args = parser.parse_args()
    if not args.root and not args.skills:
        parser.error("至少给出 --root 或 --skills 之一")
    result = {"范围": "只检查结构和文件，不代替看片、听片和评审"}
    failed = False
    for label, path, check in (("项目", args.root, audit_project), ("套组", args.skills, audit_skills)):
        if not path:
            continue
        path = path.resolve()
        if not path.is_dir():
            result[label] = {"errors": ["目录不存在：" + str(path)], "warnings": [], "info": {}}
        else:
            result[label] = check(path)
        failed = failed or bool(result[label]["errors"])
    result["ok"] = not failed
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
