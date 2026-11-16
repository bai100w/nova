#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从预演清单生成纸面预演摘要和文字卡预演片。

只用 Python 标准库；生成视频时需要 FFmpeg（含 drawtext 滤镜）。

用法：
  纸面检查（只计算，不出视频）：
    python build_animatic.py 预演清单.csv --check-only [--target 50-70] [--hook-by 3]
  生成文字卡预演片：
    python build_animatic.py 预演清单.csv --out 预演.mp4 [--size 720x1280] [--bgm 临时音乐.mp3] [--font 字体文件]

预演清单是 UTF-8 编码的 CSV，第一行为表头。列：
  必填：镜号, 时长（秒）
  建议：场, 景别, 画面, 台词, 节拍, 强度（1 到 5）
  可选：图片（关键帧路径，有就用图片代替文字卡）, 音频（临时配音路径）
路径相对于 CSV 所在目录。

输出：
  <CSV 同名>-纸面预演.md：时间线、累计时间、钩子与最高点位置、雷同段落、过长镜头、缺台词提示。
  加上 --out 时另出预演视频。临时音频和临时音乐只用于判断节奏，不进入成片。

本脚本只做计算和拼接，不判断故事好坏；盲读测试和看片仍需另做。
"""
import argparse
import csv
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyh.ttf", "C:/Windows/Fonts/simhei.ttf",
    "/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
]
RUN_LIMIT = 3          # 连续多少个相同景别算雷同
LONG_SHOT = 8.0        # 超过多少秒的单镜提示检查
LOW_LEVEL = 2          # 强度不高于它算低强度
LOW_SHARE = 0.15       # 低强度连续占全片时长的比例超过它，提示可能走神


def read_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = [{(k or "").strip(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f)]
    if not rows:
        sys.exit("预演清单是空的")
    missing = [c for c in ("镜号", "时长") if c not in rows[0]]
    if missing:
        sys.exit("预演清单缺少必填列：" + "、".join(missing))
    for i, r in enumerate(rows, 2):
        try:
            r["_dur"] = float(r["时长"])
            if r["_dur"] <= 0:
                raise ValueError
        except ValueError:
            sys.exit("第 %d 行的时长不是正数：%s" % (i, r["时长"]))
    return rows


def fmt(t):
    return "%d:%04.1f" % (int(t // 60), t % 60)


def spoken_len(text):
    """台词的实际字数：去掉说话人前缀（如“唐果：”）、空格和标点。"""
    count = 0
    for part in re.split(r"[\n；;]", text or ""):
        part = re.sub(r"^\s*[^：:\s]{1,8}[：:]", "", part)
        count += len(re.findall(r"[\w]", part))
    return count


def paper_previz(rows, target, hook_by):
    lines, t = [], 0.0
    lines.append("| 镜号 | 场 | 起 | 止 | 时长 | 景别 | 节拍 | 强度 | 台词 |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        start, t = t, t + r["_dur"]
        r["_start"], r["_end"] = start, t
        line = (r.get("台词", "") or "").replace("|", "／").replace("\n", " ")
        lines.append("| %s | %s | %s | %s | %.1f | %s | %s | %s | %s |" % (
            r["镜号"], r.get("场", ""), fmt(start), fmt(t), r["_dur"],
            r.get("景别", ""), r.get("节拍", ""), r.get("强度", ""), line[:40]))
    total = t
    issues, notes = [], []

    if target:
        lo, hi = target
        state = "在范围内" if lo <= total <= hi else "超出范围"
        notes.append("总时长 %s，目标 %s 至 %s 秒，%s" % (fmt(total), lo, hi, state))
        if state != "在范围内":
            issues.append("总时长 %.1f 秒，不在目标范围 %s 至 %s 秒内" % (total, lo, hi))
    else:
        notes.append("总时长 %s（未给目标范围）" % fmt(total))

    hooks = [r for r in rows if "钩子" in r.get("节拍", "")]
    if hooks:
        h = hooks[0]
        notes.append("开场钩子：%s，从 %s 开始" % (h["镜号"], fmt(h["_start"])))
        if hook_by is not None and h["_start"] > hook_by:
            issues.append("开场钩子在 %.1f 秒才出现，晚于要求的 %s 秒" % (h["_start"], hook_by))
    elif hook_by is not None:
        issues.append("节拍列里没有标“钩子”，无法检查开场钩子的时间")

    scored = [r for r in rows if r.get("强度", "").replace(".", "", 1).isdigit()]
    if scored:
        top = max(float(r["强度"]) for r in scored)
        peaks = [r for r in scored if float(r["强度"]) == top]
        notes.append("最高强度 %g：%s，位于全片 %.0f%% 处" % (
            top, "、".join(p["镜号"] for p in peaks), 100 * peaks[0]["_start"] / total))
        has_beats = any(r.get("节拍") for r in rows)
        start = 0
        for k in range(1, len(scored) + 1):
            if k < len(scored) and scored[k]["强度"] == scored[start]["强度"]:
                continue
            seg = scored[start:k]
            beats = []
            for r in seg:
                if r.get("节拍") and r["节拍"] not in beats:
                    beats.append(r["节拍"])
            span = seg[-1]["_end"] - seg[0]["_start"]
            level = float(seg[0]["强度"])
            # 同一个节拍内强度相同是正常的；跨越两个以上节拍还不变，才提示
            if len(seg) > RUN_LIMIT and (not has_beats or len(beats) >= 2):
                where = "，跨越节拍：" + "、".join(beats) if beats else ""
                issues.append("强度 %s 从 %s 到 %s 连续 %d 镜、%.1f 秒没有变化%s，检查是否平" % (
                    seg[0]["强度"], seg[0]["镜号"], seg[-1]["镜号"], len(seg), span, where))
            # 低强度拖得太长，不论是否跨节拍都提示
            elif level <= LOW_LEVEL and span >= LOW_SHARE * total and len(seg) > 1:
                issues.append("低强度 %s 从 %s 到 %s 持续 %.1f 秒，占全片 %.0f%%，观众可能在这里走神" % (
                    seg[0]["强度"], seg[0]["镜号"], seg[-1]["镜号"], span, 100 * span / total))
            start = k

    run, start_idx = 1, 0
    for i in range(1, len(rows) + 1):
        same = i < len(rows) and rows[i].get("景别") and rows[i].get("景别") == rows[i - 1].get("景别")
        if same:
            run += 1
            continue
        if run >= RUN_LIMIT:
            issues.append("景别“%s”连续 %d 镜（%s 至 %s），检查是否需要变化" % (
                rows[i - 1].get("景别"), run, rows[start_idx]["镜号"], rows[i - 1]["镜号"]))
        run, start_idx = 1, i

    for r in rows:
        if r["_dur"] > LONG_SHOT:
            issues.append("%s 时长 %.1f 秒，确认是有意的长镜头，且动作和台词撑得住" % (r["镜号"], r["_dur"]))
        words = spoken_len(r.get("台词", ""))
        if words and words / r["_dur"] > 5:
            issues.append("%s 台词 %d 字只有 %.1f 秒，约每秒 %.1f 字，可能装不下" % (
                r["镜号"], words, r["_dur"], words / r["_dur"]))

    out = ["# 纸面预演摘要", "", "## 概况", ""] + ["- " + n for n in notes]
    out += ["", "## 需要检查的地方", ""] + (["- " + x for x in issues] or ["- 计算范围内没有发现问题"])
    out += ["", "## 时间线", ""] + lines
    out += ["", "本摘要只检查时长、位置和序列。看得懂与否需要盲读测试，画面观感需要看片。", ""]
    return "\n".join(out), issues


def find_font(given):
    if given:
        if not Path(given).is_file():
            sys.exit("找不到字体文件：" + given)
        return given
    for c in FONT_CANDIDATES:
        if Path(c).is_file():
            return c
    found = glob.glob("/usr/share/fonts/**/*CJK*.tt[cf]", recursive=True)
    if found:
        return found[0]
    sys.exit("找不到中文字体，请用 --font 指定一个字体文件")


def esc(path):
    """把路径转成 drawtext 滤镜里可用的形式。"""
    return str(path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def wrap(text, width):
    out, line = [], ""
    for ch in text:
        line += ch
        if len(line) >= width or ch == "\n":
            out.append(line.rstrip("\n"))
            line = ""
    if line:
        out.append(line)
    return "\n".join(out)


def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        sys.exit("FFmpeg 出错：\n" + p.stderr.decode("utf-8", "replace")[-1500:])


def build_video(rows, base, out, size, font, bgm, fps=24):
    if not shutil.which("ffmpeg"):
        sys.exit("没有找到 FFmpeg。纸面预演可以用 --check-only 先做")
    w, h = (int(x) for x in size.lower().split("x"))
    fs = max(18, w // 24)
    chars = max(8, int(w * 0.84 / fs))
    tmp = Path(tempfile.mkdtemp(prefix="animatic_"))
    segs = []
    try:
        for i, r in enumerate(rows):
            head = "%s　%s　%.1f秒" % (r["镜号"], r.get("景别", ""), r["_dur"])
            body = wrap(r.get("画面", ""), chars)
            line = wrap(r.get("台词", ""), chars)
            files = {}
            for key, val in (("head", head), ("body", body), ("line", line)):
                f = tmp / ("%03d_%s.txt" % (i, key))
                f.write_text(val, encoding="utf-8")
                files[key] = f
            font_e = esc(font)
            draw = ("drawtext=fontfile='{f}':textfile='{t}':fontcolor=white:fontsize={s}:x=(w-tw)/2:y={y}"
                    ":box=1:boxcolor=black@0.55:boxborderw=12:line_spacing=10")
            filters = [draw.format(f=font_e, t=esc(files["head"]), s=int(fs * 0.8), y="h*0.06")]
            img = r.get("图片", "")
            if img:
                src = (base / img)
                if not src.is_file():
                    sys.exit("%s 的图片找不到：%s" % (r["镜号"], img))
                vin = ["-loop", "1", "-t", "%.3f" % r["_dur"], "-i", str(src)]
                pre = "scale=%d:%d:force_original_aspect_ratio=decrease,pad=%d:%d:(ow-iw)/2:(oh-ih)/2,setsar=1," % (w, h, w, h)
            else:
                vin = ["-f", "lavfi", "-t", "%.3f" % r["_dur"], "-i", "color=c=0x1e1e24:s=%dx%d:r=%d" % (w, h, fps)]
                pre = ""
                if body:
                    filters.append(draw.format(f=font_e, t=esc(files["body"]), s=fs, y="(h-th)/2-h*0.08"))
            if line:
                filters.append(draw.format(f=font_e, t=esc(files["line"]), s=int(fs * 0.9), y="h*0.72")
                               .replace("fontcolor=white", "fontcolor=0xffe08a"))
            aud = r.get("音频", "")
            if aud:
                a = base / aud
                if not a.is_file():
                    sys.exit("%s 的音频找不到：%s" % (r["镜号"], aud))
                ain = ["-i", str(a)]
            else:
                ain = ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
            seg = tmp / ("%03d.mp4" % i)
            run(["ffmpeg", "-y", "-loglevel", "error"] + vin + ain + [
                "-filter_complex", "[0:v]%s%s,fps=%d,format=yuv420p[v];[1:a]aresample=48000,apad,atrim=0:%.3f,asetpts=N/SR/TB[a]"
                % (pre, ",".join(filters), fps, r["_dur"]),
                "-map", "[v]", "-map", "[a]", "-t", "%.3f" % r["_dur"],
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-c:a", "aac", "-ac", "2", str(seg)])
            segs.append(seg)
        lst = tmp / "list.txt"
        lst.write_text("".join("file '%s'\n" % s.as_posix() for s in segs), encoding="utf-8")
        joined = tmp / "joined.mp4"
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined)])
        if bgm:
            if not Path(bgm).is_file():
                sys.exit("找不到临时音乐：" + bgm)
            run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(joined), "-stream_loop", "-1", "-i", bgm,
                 "-filter_complex", "[1:a]volume=0.25[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
                 "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", str(out)])
        else:
            shutil.copyfile(joined, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="纸面预演与文字卡预演片")
    ap.add_argument("csv", type=Path, help="预演清单 CSV")
    ap.add_argument("--check-only", action="store_true", help="只出纸面预演摘要，不生成视频")
    ap.add_argument("--out", type=Path, help="预演视频的输出路径")
    ap.add_argument("--target", help="目标时长范围，秒，例如 50-70")
    ap.add_argument("--hook-by", type=float, help="开场钩子最晚出现的秒数")
    ap.add_argument("--size", default="720x1280", help="画面尺寸，默认 720x1280（竖屏）")
    ap.add_argument("--font", help="中文字体文件；不给时自动查找")
    ap.add_argument("--bgm", help="临时音乐文件，只用于判断节奏")
    a = ap.parse_args()

    rows = read_rows(a.csv)
    target = None
    if a.target:
        try:
            lo, hi = (float(x) for x in a.target.split("-"))
            target = (lo, hi)
        except ValueError:
            sys.exit("--target 的格式应为 最短-最长，例如 50-70")
    summary, issues = paper_previz(rows, target, a.hook_by)
    report = a.csv.with_name(a.csv.stem + "-纸面预演.md")
    report.write_text(summary, encoding="utf-8")
    print("纸面预演摘要：%s（%d 处需要检查）" % (report, len(issues)))

    if a.check_only:
        return 0
    if not a.out:
        print("没有给 --out，未生成视频。只要纸面预演请加 --check-only")
        return 0
    build_video(rows, a.csv.parent, a.out, a.size, find_font(a.font), a.bgm)
    print("预演视频：%s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
