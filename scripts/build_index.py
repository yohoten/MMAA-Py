#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成仓库首页 index.html：项目介绍、notebook/数据/文档浏览与本地工具集。

单文件、零外部依赖，适合 GitHub Pages 等静态托管。

用法：
    python scripts/build_index.py
    python scripts/build_index.py --repo-url https://github.com/<user>/<repo>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "venv", ".ipynb_checkpoints", "__pycache__"}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def cell_source(cell: dict) -> str:
    return "".join(cell.get("source", []))


def headings(text: str) -> list[dict]:
    out: list[dict] = []
    fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        m = re.match(r"^(#{2,3})\s+(.+)$", line)
        if m:
            out.append({"level": len(m.group(1)), "text": m.group(2).strip()})
    return out


def notebook_summary(cells: list[dict]) -> str:
    for cell in cells:
        if cell.get("cell_type") != "markdown":
            continue
        lines = cell_source(cell).splitlines()
        for i, line in enumerate(lines):
            if re.match(r"^##\s+1\.", line):
                body = []
                for nxt in lines[i + 1 :]:
                    if re.match(r"^##\s+", nxt):
                        break
                    body.append(nxt.strip())
                text = re.sub(r"\s+", " ", " ".join(x for x in body if x))
                if text:
                    return text[:190] + ("…" if len(text) > 190 else "")
    return ""


def notebook_entry(path: Path) -> dict:
    nb = json.loads(read_text(path))
    cells = nb.get("cells", [])
    title = path.stem
    module = "未分类"
    deps: list[str] = []
    for cell in cells:
        if cell.get("cell_type") != "markdown":
            continue
        text = cell_source(cell)
        for line in text.splitlines():
            if line.startswith("# ") and title == path.stem:
                title = re.sub(r"^\d+[.、]?\s*", "", line[2:].strip()).strip()
            m = re.search(r"\*\*模块\*\*[：:]\s*([^｜|\n]+)", line)
            if m:
                module = m.group(1).strip()
            m = re.search(r"\*\*依赖\*\*[：:]\s*([^｜|\n]+)", line)
            if m:
                raw = re.sub(r"等$", "", m.group(1).strip())
                deps = [x.strip() for x in re.split(r"[、,，]", raw) if x.strip() and x.strip() != "—"]

    code = [c for c in cells if c.get("cell_type") == "code"]
    data: list[str] = []
    for cell in code:
        for m in re.finditer(r"\.\./data/([^\"'\n]+)", cell_source(cell)):
            ref = m.group(1).strip().rstrip(")）.,，;；")
            if ref and ref not in data:
                data.append(ref)

    sections: list[dict] = []
    for cell in cells:
        if cell.get("cell_type") == "markdown":
            sections.extend(headings(cell_source(cell)))
    if len(sections) > 80:
        sections = sections[:80]

    num = int(re.match(r"(\d+)", path.name).group(1))
    return {
        "num": num,
        "title": title,
        "file": path.name,
        "path": f"notebooks/{path.name}",
        "module": module,
        "deps": deps,
        "code": len(code),
        "unexec": sum(1 for c in code if c.get("execution_count") is None),
        "data": data,
        "sections": sections,
        "summary": notebook_summary(cells),
        "size": round(path.stat().st_size / 1024, 1),
    }


def run_checks() -> dict:
    baseline = ROOT / ".check_baseline.json"
    try:
        baseline_n = len(json.loads(read_text(baseline))) if baseline.exists() else 0
    except (ValueError, TypeError):
        baseline_n = 0
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check_project.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=180,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        m = re.search(
            r"ERROR\s+(\d+)（基线内\s+(\d+)，基线外\s+(\d+)）\s*/\s*WARN\s+(\d+)\s*/\s*INFO\s+(\d+)",
            text,
        )
        if m:
            return {
                "error": int(m.group(1)),
                "baseline": int(m.group(2)),
                "outside": int(m.group(3)),
                "warn": int(m.group(4)),
                "info": int(m.group(5)),
                "ok": proc.returncode == 0,
            }
    except (OSError, subprocess.SubprocessError):
        pass
    return {"error": baseline_n, "baseline": baseline_n, "outside": 0, "warn": 0, "info": 0, "ok": None}


def working_size_mb() -> float:
    total = 0
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        total += path.stat().st_size
    return round(total / 1024 / 1024, 1)


def is_ignored(rel: str) -> bool:
    """路径是否被 .gitignore 排除；被排除的目录不会出现在 GitHub Pages 上。"""
    try:
        proc = subprocess.run(["git", "check-ignore", "-q", "--", rel], cwd=ROOT,
                              capture_output=True, timeout=10)
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def detect_repo_url() -> str:
    """从 git origin 推断仓库地址，避免页面顶栏留下占位链接。"""
    try:
        proc = subprocess.run(["git", "remote", "get-url", "origin"], cwd=ROOT,
                              capture_output=True, text=True, timeout=10)
        url = (proc.stdout or "").strip()
    except (OSError, subprocess.SubprocessError):
        return ""
    if url.startswith("git@github.com:"):
        url = "https://github.com/" + url.split(":", 1)[1]
    if url.endswith(".git"):
        url = url[:-4]
    return url if url.startswith("https://") else ""


def build_manifest(repo_url: str) -> dict:
    nb_dir = ROOT / "notebooks"
    notebooks = sorted(
        (notebook_entry(p) for p in nb_dir.glob("*.ipynb")),
        key=lambda x: x["num"],
    )

    data_files = []
    for p in sorted((ROOT / "data").glob("*")):
        if p.is_file() and p.suffix.lower() != ".md":
            data_files.append({"name": p.name, "path": f"data/{p.name}", "key": p.name,
                               "kind": "root", "size": round(p.stat().st_size / 1024, 1)})
    for p in sorted((ROOT / "data" / "textbook").glob("*")):
        if p.is_file() and p.suffix.lower() != ".md":
            data_files.append({"name": p.name, "path": f"data/textbook/{p.name}", "key": f"textbook/{p.name}",
                               "kind": "textbook", "size": round(p.stat().st_size / 1024, 1)})

    for item in data_files:
        item["usedBy"] = sorted(
            n["num"] for n in notebooks
            if any(ref == item["key"] or ref == item["name"] for ref in n["data"])
        )

    docs = []
    cn_num = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    for p in sorted((ROOT / "docs").glob("*.pdf")):
        name = p.stem
        order = 999
        m = re.match(r"第\s*(\d+)\s*章\s*(.*)$", name)
        if m:
            chapter, topic = m.group(1), m.group(2).strip()
            order = int(chapter)
        elif (m := re.match(r"附录([一二三四五六七八九十]+)\s*(.*)$", name)):
            chapter, topic = f"附录{m.group(1)}", m.group(2).strip()
            order = 100 + cn_num.get(m.group(1), 0)
        elif name.startswith("参考文献"):
            chapter, topic, order = "参考文献", "引用文献", 200
        else:
            chapter, topic = "其他", name
        docs.append({"file": p.name, "path": f"docs/{p.name}", "chapter": chapter,
                     "topic": topic, "size": round(p.stat().st_size / 1024, 1), "order": order})
    docs.sort(key=lambda d: d["order"])
    for d in docs:
        d.pop("order", None)

    ppts = []
    for p in sorted((ROOT / "ppts").glob("*.pptx")):
        m = re.match(r"(\d+)[_-](.+)$", p.stem)
        chapter, topic = (m.group(1), m.group(2)) if m else ("—", p.stem)
        ppts.append({"file": p.name, "path": f"ppts/{p.name}", "chapter": chapter,
                     "topic": topic, "size": round(p.stat().st_size / 1024, 1)})

    manual_root = ROOT / "manual"
    manual_cats = []
    for d in sorted((p for p in manual_root.iterdir() if p.is_dir()), key=lambda p: p.name):
        files = [f for f in d.rglob("*") if f.is_file()]
        manual_cats.append({"name": d.name, "files": len(files),
                            "size": round(sum(f.stat().st_size for f in files) / 1024 / 1024, 2)})
    manual_files = sum(c["files"] for c in manual_cats)
    manual_size = round(sum(c["size"] for c in manual_cats), 1)

    notes = {
        "Markov_chain": "马尔可夫链与赌博模拟；gamble.py 缺随机种子，gamble_A.py 可运行",
        "Monte_Carlo_simulation": "脚本已损坏，仅保留历史结果图；可运行版本在 Markov_chain/",
        "Object_classification": "CIFAR-10 图像分类，依赖 torch 与 GPU",
    }
    cases = []
    for d in sorted((p for p in (ROOT / "modelit").iterdir() if p.is_dir()), key=lambda p: p.name):
        files = [f for f in d.rglob("*") if f.is_file()]
        cases.append({"name": d.name, "files": len(files),
                      "size": round(sum(f.stat().st_size for f in files) / 1024 / 1024, 2),
                      "note": notes.get(d.name, ""),
                      "published": not is_ignored(f"modelit/{d.name}")})
    modelit_files = sum(c["files"] for c in cases)
    modelit_local_only = bool(cases) and all(not c["published"] for c in cases)

    modules = {}
    for n in notebooks:
        modules[n["module"]] = modules.get(n["module"], 0) + 1
    module_list = [{"name": k, "count": v} for k, v in sorted(modules.items(), key=lambda kv: (-kv[1], kv[0]))]

    return {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "repo": {
            "name": ROOT.name,
            "url": repo_url.rstrip("/"),
            "sizeMB": working_size_mb(),
            "counts": {
                "notebooks": len(notebooks),
                "data": len(data_files),
                "docs": len(docs),
                "ppts": len(ppts),
                "manual": manual_files,
                "modelit": modelit_files,
                "modules": len(module_list),
            },
        },
        "modules": module_list,
        "notebooks": notebooks,
        "data": data_files,
        "docs": docs,
        "ppts": ppts,
        "manual": {"files": manual_files, "sizeMB": manual_size, "categories": manual_cats},
        "modelit": {"files": modelit_files, "cases": cases, "localOnly": modelit_local_only},
        "checks": run_checks(),
    }


TEMPLATE = r'''<!doctype html>
<html lang="zh-CN" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>数学建模图谱 · 项目导航</title>
<meta name="description" content="__META_DESC__">
<style>
:root{
  --bg:#f5f6f8; --panel:#ffffff; --panel-2:#fafbfc; --ink:#141a22; --muted:#5c6776;
  --line:#dde2e8; --line-strong:#c6cdd6; --accent:#0e6b5c; --accent-2:#0a5449;
  --accent-soft:#e7f2ef; --ok:#1f6b3a; --ok-soft:#e8f3ec; --warn:#8a5a00; --warn-soft:#fbf1dd;
  --err:#a12d24; --err-soft:#fbeae8; --code:#f2f4f7;
  --sans:"Segoe UI",-apple-system,BlinkMacSystemFont,"Noto Sans SC","Microsoft YaHei",sans-serif;
  --mono:"Cascadia Code",ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace;
  --radius:6px; --topbar:60px; --side:236px;
}
[data-theme="dark"]{
  --bg:#0f1419; --panel:#151c23; --panel-2:#1a222b; --ink:#e6edf3; --muted:#9aa7b4;
  --line:#26313c; --line-strong:#36434f; --accent:#5cc9b4; --accent-2:#8adccb;
  --accent-soft:#16302b; --ok:#7ad19a; --ok-soft:#152c1f; --warn:#e0b25f; --warn-soft:#2e2617;
  --err:#f08a80; --err-soft:#331b19; --code:#0f171f;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.65 var(--sans);-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
button{font:inherit;color:inherit}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.skip{position:absolute;left:-999px;top:8px;background:var(--panel);padding:8px 12px;z-index:99}
.skip:focus{left:8px}
.topbar{position:sticky;top:0;z-index:50;height:var(--topbar);display:grid;grid-template-columns:auto minmax(220px,1fr) auto;gap:18px;align-items:center;padding:0 22px;background:var(--panel);border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:center;gap:10px;background:none;border:0;padding:0;cursor:pointer;text-align:left}
.brand-mark{display:grid;place-items:center;width:30px;height:30px;border:1px solid var(--line-strong);border-radius:4px;font:600 15px/1 var(--mono);color:var(--accent)}
.brand-text{display:flex;flex-direction:column;line-height:1.2}
.brand-text strong{font-size:14px;letter-spacing:.01em}
.brand-text small{color:var(--muted);font-size:11.5px}
.search-open{display:flex;align-items:center;justify-content:space-between;gap:12px;max-width:620px;width:100%;padding:7px 10px;background:var(--panel-2);border:1px solid var(--line);border-radius:var(--radius);color:var(--muted);cursor:pointer;font-size:13px}
.search-open:hover{border-color:var(--line-strong);color:var(--ink)}
kbd{font:11px/1 var(--mono);padding:3px 5px;border:1px solid var(--line-strong);border-bottom-width:2px;border-radius:3px;color:var(--muted);background:var(--panel)}
.top-actions{display:flex;align-items:center;gap:8px}
.icon-btn{display:grid;place-items:center;width:32px;height:32px;border:1px solid var(--line);background:var(--panel);border-radius:var(--radius);cursor:pointer;font-size:16px}
.icon-btn:hover{border-color:var(--line-strong)}
.shell{display:grid;grid-template-columns:var(--side) minmax(0,1fr);max-width:1440px;margin:0 auto}
.sidebar{position:sticky;top:var(--topbar);height:calc(100vh - var(--topbar));overflow:auto;padding:18px 14px 24px;border-right:1px solid var(--line)}
#nav{display:flex;flex-direction:column;gap:2px}
.nav-item{display:flex;align-items:center;justify-content:space-between;gap:8px;width:100%;padding:8px 10px;background:none;border:0;border-radius:4px;cursor:pointer;color:var(--muted);font-size:13.5px;text-align:left}
.nav-item b{font:11.5px/1 var(--mono);color:var(--muted)}
.nav-item:hover{background:var(--panel-2);color:var(--ink)}
.nav-item.active{background:var(--accent-soft);color:var(--accent);box-shadow:inset 2px 0 0 var(--accent)}
.nav-item.active b{color:var(--accent)}
.side-foot{margin-top:22px;padding-top:14px;border-top:1px solid var(--line);color:var(--muted);font-size:11.5px;line-height:1.7}
#main{min-width:0;padding:30px 34px 72px;outline:none}
.eyebrow{margin:0 0 6px;color:var(--muted);font-size:11px;letter-spacing:.14em;text-transform:uppercase}
h1{font-size:27px;line-height:1.25;margin:0 0 8px;letter-spacing:-.01em;font-weight:650}
h2{font-size:17px;margin:0 0 10px;font-weight:620}
h3{font-size:14.5px;margin:20px 0 8px;font-weight:620}
p{margin:0 0 10px}
.lede{color:var(--muted);max-width:760px;font-size:14.5px}
.hero{padding:6px 0 22px;border-bottom:1px solid var(--line);margin-bottom:22px}
.hero h1{font-size:31px}
.hero-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(148px,1fr));gap:10px;margin:18px 0 22px}
.kpi{padding:14px;background:var(--panel);border:1px solid var(--line);border-radius:var(--radius)}
.kpi span{display:block;color:var(--muted);font-size:11.5px;letter-spacing:.04em}
.kpi strong{display:block;margin-top:2px;font:600 24px/1.2 var(--mono);font-variant-numeric:tabular-nums}
.kpi small{color:var(--muted);font-size:11.5px}
.grid-2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-bottom:14px}
.card{padding:18px;background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);margin-bottom:14px}
.card > :last-child{margin-bottom:0}
.bar-row{display:grid;grid-template-columns:110px minmax(0,1fr) 28px;gap:10px;align-items:center;margin:7px 0;font-size:12.5px}
.bar{height:6px;background:var(--panel-2);border:1px solid var(--line);border-radius:2px;overflow:hidden}
.bar i{display:block;height:100%;background:var(--accent);opacity:.75}
.bar-row b{font:12px/1 var(--mono);text-align:right;color:var(--muted)}
.checks{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.checks div{padding:10px;background:var(--panel-2);border:1px solid var(--line);border-radius:4px}
.checks span{display:block;color:var(--muted);font-size:10.5px;letter-spacing:.1em}
.checks strong{display:block;font:600 20px/1.3 var(--mono)}
.checks small{color:var(--muted);font-size:11px}
.ok{color:var(--ok)} .warn{color:var(--warn)} .bad{color:var(--err)}
pre{font-family:var(--mono);font-size:12.5px;line-height:1.6;background:var(--code);border:1px solid var(--line);border-radius:4px;padding:12px;overflow:auto;margin:0 0 10px}
.tree{color:var(--muted);background:var(--panel-2)}
.toolbar{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:0 0 12px}
.input{min-height:34px;padding:6px 9px;background:var(--panel);border:1px solid var(--line);border-radius:4px;color:var(--ink);font:13px var(--sans)}
.input[type=search]{min-width:260px;flex:1 1 260px}
.toolbar-note{margin-left:auto;color:var(--muted);font-size:12px;font-variant-numeric:tabular-nums}
.btn{display:inline-flex;align-items:center;gap:6px;min-height:32px;padding:5px 11px;background:var(--panel);border:1px solid var(--line-strong);border-radius:4px;cursor:pointer;font-size:12.5px;color:var(--ink);text-decoration:none}
.btn:hover{border-color:var(--accent);color:var(--accent);text-decoration:none}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.btn.primary:hover{background:var(--accent-2);color:#fff}
.btn.ghost{border-color:transparent;background:transparent;color:var(--muted)}
.btn.small{min-height:26px;padding:2px 8px;font-size:11.5px}
.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:var(--radius);background:var(--panel)}
.table{width:100%;border-collapse:collapse;font-size:13px}
.table th{padding:9px 10px;text-align:left;font:600 10.5px/1.4 var(--sans);letter-spacing:.09em;text-transform:uppercase;color:var(--muted);background:var(--panel-2);border-bottom:1px solid var(--line);white-space:nowrap}
.table td{padding:8px 10px;border-top:1px solid var(--line);vertical-align:top}
.table tbody tr:hover{background:var(--panel-2)}
.table tbody tr[data-nb]{cursor:pointer}
.num{font-family:var(--mono);font-variant-numeric:tabular-nums;text-align:right}
.mono{font-family:var(--mono)}
.row-title{display:block;font-weight:560}
.row-sub{display:block;color:var(--muted);font-size:11px;font-family:var(--mono)}
.badge{display:inline-flex;align-items:center;padding:1px 7px;border:1px solid var(--line-strong);border-radius:999px;font-size:11px;color:var(--muted);white-space:nowrap}
.badge.accent{border-color:var(--accent);color:var(--accent);background:var(--accent-soft)}
.badge.ok{border-color:var(--ok);color:var(--ok);background:var(--ok-soft)}
.badge.warn{border-color:var(--warn);color:var(--warn);background:var(--warn-soft)}
.badge.bad{border-color:var(--err);color:var(--err);background:var(--err-soft)}
.chips{display:flex;flex-wrap:wrap;gap:4px}
.drawer{position:fixed;inset:0;z-index:70;display:none;background:rgba(10,14,18,.42)}
.drawer.open{display:block}
.drawer-panel{position:absolute;top:0;right:0;height:100%;width:min(560px,100%);background:var(--panel);border-left:1px solid var(--line);display:flex;flex-direction:column;animation:slide .18s ease-out}
@keyframes slide{from{transform:translateX(18px);opacity:.6}to{transform:none;opacity:1}}
.drawer-head,.modal-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;padding:16px 18px;border-bottom:1px solid var(--line)}
.drawer-head h2,.modal-head h2{margin:0;font-size:18px}
.drawer-body{padding:18px;overflow:auto}
.meta-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:4px;overflow:hidden;margin-bottom:14px}
.meta-grid div{background:var(--panel);padding:9px 10px}
.meta-grid span{display:block;color:var(--muted);font-size:10.5px;letter-spacing:.06em}
.meta-grid b{font:13px/1.5 var(--mono)}
.actions{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 16px}
.outline{margin:0;padding-left:20px;color:var(--muted);font-size:12.5px}
.outline li{margin:2px 0}
.outline li.l2{color:var(--ink);font-weight:560;list-style:decimal}
.outline li.l3{list-style:circle}
.modal{position:fixed;inset:0;z-index:80;display:none;background:rgba(10,14,18,.5);padding:3vh 2vw}
.modal.open{display:block}
.modal-panel{display:flex;flex-direction:column;height:94vh;max-width:1120px;margin:0 auto;background:var(--panel);border:1px solid var(--line);border-radius:8px;overflow:hidden}
.modal-actions{display:flex;align-items:center;gap:10px}
.modal-body{padding:18px 22px 40px;overflow:auto}
.switch{display:inline-flex;align-items:center;gap:6px;color:var(--muted);font-size:12px;cursor:pointer}
.nb-meta{color:var(--muted);font-size:11.5px;padding-bottom:10px;border-bottom:1px solid var(--line);margin-bottom:6px}
.cell{border-bottom:1px solid var(--line);padding:12px 0}
.cell-head{font:11px/1.4 var(--mono);color:var(--muted);margin-bottom:5px}
.cell pre.code{margin:0;background:var(--code);border-color:var(--line)}
.out{margin-top:8px;padding:8px 10px;background:var(--panel-2);border-left:3px solid var(--line-strong);font:12.5px/1.6 var(--mono);white-space:pre-wrap;overflow:auto;max-height:420px}
.out.bad{border-left-color:var(--err);color:var(--err)}
.out img{max-width:100%;height:auto;background:#fff;border:1px solid var(--line);margin:4px 0}
.md{padding:2px 0 8px}
.md h1,.md h2,.md h3,.md h4{margin:14px 0 8px;line-height:1.35}
.md h1{font-size:20px} .md h2{font-size:17px} .md h3{font-size:15px} .md h4{font-size:14px}
.md p{margin:0 0 9px}
.md ul,.md ol{margin:0 0 9px;padding-left:22px}
.md li{margin:2px 0}
.md code{font:12px/1.5 var(--mono);background:var(--code);border:1px solid var(--line);border-radius:3px;padding:0 4px}
.md pre.code{margin:8px 0;padding:10px}
.md blockquote{margin:8px 0;padding:6px 12px;border-left:3px solid var(--accent);color:var(--muted);background:var(--panel-2)}
.md hr{border:0;border-top:1px solid var(--line);margin:14px 0}
.md-table{width:100%;border-collapse:collapse;font-size:12.5px;margin:8px 0}
.md-table th,.md-table td{border:1px solid var(--line);padding:5px 7px;text-align:left}
.md-table th{background:var(--panel-2)}
.callout{padding:12px 14px;border:1px solid var(--warn);border-left-width:4px;background:var(--warn-soft);border-radius:4px;color:var(--ink);margin:10px 0}
.callout.bad{border-color:var(--err);background:var(--err-soft)}
.callout code{font-family:var(--mono);font-size:12px}
.palette{position:fixed;inset:0;z-index:90;display:none;background:rgba(10,14,18,.45);padding:12vh 16px 0}
.palette.open{display:block}
.palette-panel{max-width:620px;margin:0 auto;background:var(--panel);border:1px solid var(--line-strong);border-radius:8px;overflow:hidden}
#paletteInput{width:100%;padding:13px 15px;border:0;border-bottom:1px solid var(--line);background:var(--panel);color:var(--ink);font:15px var(--sans);outline:none}
.palette-list{max-height:52vh;overflow:auto}
.palette-item{display:grid;grid-template-columns:68px minmax(0,1fr) auto;gap:10px;align-items:center;width:100%;padding:9px 14px;background:none;border:0;border-bottom:1px solid var(--line);cursor:pointer;text-align:left;font-size:13px}
.palette-item:hover,.palette-item.active{background:var(--accent-soft)}
.palette-item span:first-child{color:var(--muted);font:10.5px/1.4 var(--mono);letter-spacing:.06em;text-transform:uppercase}
.palette-item small{color:var(--muted);font-size:11px}
.palette-hint{margin:0;padding:8px 14px;color:var(--muted);font-size:11px;border-top:1px solid var(--line)}
.toast{position:fixed;left:50%;bottom:24px;z-index:100;transform:translate(-50%,12px);padding:8px 14px;background:var(--ink);color:var(--bg);border-radius:4px;font-size:12.5px;opacity:0;pointer-events:none;transition:.18s}
.toast.show{opacity:1;transform:translate(-50%,0)}
.grid-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}
.case{padding:14px;border:1px solid var(--line);border-radius:var(--radius);background:var(--panel)}
.case h3{margin:0 0 4px;font-size:14px}
.case p{color:var(--muted);font-size:12.5px;margin:0}
.case .mono{font-size:11px;color:var(--muted)}
.tool{display:grid;grid-template-columns:minmax(0,1fr);gap:10px}
.tool-row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.tool-note{color:var(--muted);font-size:12px}
.tool-output{min-height:20px}
progress{width:100%;height:6px}
.small{font-size:12px}
.muted{color:var(--muted)}
.lock{overflow:hidden}
@media (max-width:980px){
  .shell{display:block}
  .sidebar{position:static;height:auto;border-right:0;border-bottom:1px solid var(--line);padding:10px 14px}
  #nav{flex-direction:row;flex-wrap:wrap}
  .nav-item{width:auto}
  .nav-item b{display:none}
  .side-foot{display:none}
  #main{padding:20px 16px 56px}
  .grid-2{grid-template-columns:1fr}
  .kpis{grid-template-columns:repeat(2,1fr)}
  .search-open kbd{display:none}
  .topbar{grid-template-columns:auto 1fr auto;gap:10px;padding:0 12px}
  .brand-text small{display:none}
}
@media (prefers-reduced-motion:reduce){
  *{animation:none!important;transition:none!important;scroll-behavior:auto!important}
}
@media print{
  .topbar,.sidebar,.drawer,.modal,.palette,.toast{display:none!important}
  #main{padding:0}
}
</style>
</head>
<body>
<a class="skip" href="#main">跳到主要内容</a>
<header class="topbar">
  <button class="brand" data-view="overview" aria-label="返回概览">
    <span class="brand-mark">M</span>
    <span class="brand-text"><strong>数学建模图谱</strong><small>Model Atlas · 算法 · 案例 · 复现</small></span>
  </button>
  <button class="search-open" id="searchOpen" aria-label="打开全局搜索">
    <span>搜索 notebook、数据、文档…</span><kbd>Ctrl K</kbd>
  </button>
  <div class="top-actions">
    <button class="icon-btn" id="themeBtn" aria-label="切换深浅色">◐</button>
    <a class="btn ghost" id="repoLink" target="_blank" rel="noopener noreferrer" hidden>GitHub</a>
  </div>
</header>
<div class="shell">
  <aside class="sidebar">
    <nav id="nav" aria-label="主导航"></nav>
    <div class="side-foot" id="sideFoot"></div>
  </aside>
  <main id="main" tabindex="-1"></main>
</div>

<div class="drawer" id="drawer" aria-hidden="true">
  <div class="drawer-panel" role="dialog" aria-modal="true" aria-labelledby="drawerTitle">
    <header class="drawer-head">
      <div><p class="eyebrow" id="drawerKicker"></p><h2 id="drawerTitle"></h2></div>
      <button class="icon-btn" data-close="drawer" aria-label="关闭详情">×</button>
    </header>
    <div class="drawer-body" id="drawerBody"></div>
  </div>
</div>

<div class="modal" id="modal" aria-hidden="true">
  <div class="modal-panel" role="dialog" aria-modal="true" aria-labelledby="modalTitle">
    <header class="modal-head">
      <div><p class="eyebrow">Notebook 预览</p><h2 id="modalTitle"></h2></div>
      <div class="modal-actions">
        <label class="switch"><input type="checkbox" id="imgToggle"> 显示图片</label>
        <button class="icon-btn" data-close="modal" aria-label="关闭预览">×</button>
      </div>
    </header>
    <div class="modal-body" id="modalBody"></div>
  </div>
</div>

<div class="palette" id="palette" aria-hidden="true">
  <div class="palette-panel" role="dialog" aria-modal="true" aria-label="全局搜索">
    <input id="paletteInput" type="search" placeholder="输入编号、标题、文件名…" autocomplete="off">
    <div id="paletteList" class="palette-list" role="listbox"></div>
    <p class="palette-hint">↑↓ 选择 · Enter 打开 · Esc 关闭</p>
  </div>
</div>
<div class="toast" id="toast" role="status" aria-live="polite"></div>

<script>const DATA = __MANIFEST__;</script>
<script>
'use strict';
const M = DATA;
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
const pad = n => String(n).padStart(2, '0');
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = n => new Intl.NumberFormat('zh-CN').format(n);
const size = kb => kb >= 1024 ? (kb / 1024).toFixed(1) + ' MB' : Math.round(kb) + ' KB';
const state = {view:'overview', nbQuery:'', nbModule:'all', nbStatus:'all', dataQuery:'', dataKind:'all', showImages:false, cache:{}, palette:[], pIdx:0};

const NAV = [['overview','概览'],['notebooks','Notebooks'],['data','数据'],['docs','文档'],['ppts','课件'],['manual','历史资料'],['modelit','案例'],['tools','工具'],['about','关于']];

function navCount(id){
  if(id === 'notebooks') return M.notebooks.length;
  if(id === 'data') return M.data.length;
  if(id === 'docs') return M.docs.length;
  if(id === 'ppts') return M.ppts.length;
  if(id === 'manual') return M.manual.files;
  if(id === 'modelit') return M.modelit.cases.length;
  return '';
}
function renderNav(){
  $('#nav').innerHTML = NAV.map(([id,label]) => {
    const c = navCount(id);
    return `<button class="nav-item${state.view===id?' active':''}" data-view="${id}"><span>${label}</span>${c!==''?`<b>${fmt(c)}</b>`:''}</button>`;
  }).join('');
  $('#sideFoot').innerHTML = `${M.repo.counts.notebooks} 篇 notebook · ${M.repo.counts.modules} 类方法<br>生成于 ${esc(M.generated)}<br>ERROR 基线外 ${M.checks.outside} · WARN ${M.checks.warn}`;
}

function go(view, push = true){
  if(!NAV.some(x => x[0] === view)) view = 'overview';
  state.view = view;
  if(push && location.hash !== '#' + view) location.hash = view;
  renderNav();
  const render = RENDER[view] || RENDER.overview;
  $('#main').innerHTML = render();
  window.scrollTo(0, 0);
  if(AFTER[view]) AFTER[view]();
  $('#main').focus({preventScroll:true});
}

function statusOf(n){
  if(!n.code) return ['讲义',''];
  if(!n.unexec) return ['已执行','ok'];
  if(n.unexec === n.code) return ['未执行','warn'];
  return ['部分未执行','warn'];
}
function badge(text, kind = ''){
  return `<span class="badge ${kind}">${esc(text)}</span>`;
}
function dataChips(n){
  if(!n.data.length) return '<span class="muted small">无外部数据</span>';
  return `<span class="chips">${n.data.slice(0,3).map(d => `<span class="badge">${esc(d.split('/').pop())}</span>`).join('')}${n.data.length>3?`<span class="badge">+${n.data.length-3}</span>`:''}</span>`;
}

const RENDER = {};
const AFTER = {};

RENDER.overview = () => {
  const c = M.repo.counts;
  const max = Math.max(...M.modules.map(m => m.count), 1);
  const chk = M.checks;
  return `
  <section class="hero">
    <p class="eyebrow">数学建模 · Python 实践仓库</p>
    <h1>从教材公式到可复现的 notebook</h1>
    <p class="lede">${c.notebooks} 篇 notebook 覆盖综合评价、图论、多元统计、回归、动态模型、模糊与灰色系统、神经网络、时间序列、关联规则、优化、数值方法与机器学习；35 篇教材练习稿已按主题融合，数据、文档与课件可在此统一检索。</p>
    <div class="hero-actions">
      <button class="btn primary" data-view="notebooks">浏览 ${c.notebooks} 篇 notebook</button>
      <button class="btn" data-view="tools">打开工具集</button>
      <a class="btn ghost" href="THIRD-PARTY.md">教材来源与许可</a>
    </div>
  </section>
  <div class="kpis">
    <div class="kpi"><span>Notebooks</span><strong>${c.notebooks}</strong><small>${c.modules} 类方法 · 01—${pad(c.notebooks)}</small></div>
    <div class="kpi"><span>数据文件</span><strong>${c.data}</strong><small>含教材数据 10 个</small></div>
    <div class="kpi"><span>教材 PDF</span><strong>${c.docs}</strong><small>30 章 + 附录 + 参考文献</small></div>
    <div class="kpi"><span>课件</span><strong>${c.ppts}</strong><small>20 章，04 章分册</small></div>
    <div class="kpi"><span>历史资料</span><strong>${fmt(c.manual)}</strong><small>文件 · ${M.manual.sizeMB} MB</small></div>
    <div class="kpi"><span>独立案例</span><strong>${M.modelit.cases.length}</strong><small>${M.modelit.localOnly ? '本地目录 · 未随仓库发布' : fmt(c.modelit) + ' 个文件 · 178 MB'}</small></div>
  </div>
  <div class="grid-2">
    <section class="card">
      <h2>方法分布</h2>
      ${M.modules.map(m => `<div class="bar-row"><span>${esc(m.name)}</span><div class="bar"><i style="width:${(m.count/max*100).toFixed(1)}%"></i></div><b>${m.count}</b></div>`).join('')}
    </section>
    <section class="card">
      <h2>质量门禁</h2>
      <div class="checks">
        <div><span>ERROR</span><strong class="${chk.outside ? 'bad' : 'ok'}">${chk.error}</strong><small>基线内 ${chk.baseline} · 基线外 ${chk.outside}</small></div>
        <div><span>WARN</span><strong class="warn">${chk.warn}</strong><small>执行状态、内嵌图等</small></div>
        <div><span>INFO</span><strong class="muted">${chk.info}</strong><small>提示项</small></div>
      </div>
      <p class="small muted" style="margin-top:12px">${chk.ok ? '检查器通过：基线外无新增 ERROR。' : '检查器未通过，请运行 scripts/check_project.py 查看详情。'} 基线记录 ${chk.baseline} 条已确认问题。</p>
      <pre class="small">python scripts/check_project.py</pre>
    </section>
  </div>
  <section class="card">
    <h2>快速开始</h2>
    <pre id="quickCmds">py -3.11 -m venv .venv
.venv\\Scripts\\activate
python -m pip install -r requirements.txt
python scripts/check_project.py
jupyter lab</pre>
    <div class="tool-row">
      <button class="btn" data-copy-el="quickCmds">复制命令</button>
      <button class="btn ghost" data-view="tools">按需安装 ml 依赖</button>
      <span class="tool-note">内核工作目录须为 notebooks/，相对路径 ../data 才能解析。</span>
    </div>
  </section>
  <section class="card">
    <h2>仓库结构</h2>
    <pre class="tree">notebooks/    ${c.notebooks} 篇（01—${pad(c.notebooks)}），含教材实现融合
data/         ${c.data} 个数据文件（data/textbook/ 为教材数据）
docs/         ${c.docs} 份教材 PDF
ppts/         ${c.ppts} 个授课课件
manual/       ${fmt(c.manual)} 个历史资料文件
modelit/      ${M.modelit.cases.length} 个独立案例${M.modelit.localOnly ? '（本地，未发布）' : ''}
scripts/      check_project.py · merge_textbook.py · build_index.py
THIRD-PARTY.md  上游 MIT 许可与逐篇去向</pre>
  </section>`;
};

RENDER.notebooks = () => `
  <header class="page-head">
    <p class="eyebrow">Notebooks</p>
    <h1>${M.notebooks.length} 篇实践索引</h1>
    <p class="lede">按模块与执行状态筛选；点击任意行查看结构、数据依赖与预览。</p>
  </header>
  <div class="toolbar">
    <input id="nbQuery" class="input" type="search" placeholder="搜索编号、标题、数据文件…" value="${esc(state.nbQuery)}">
    <select id="nbModule" class="input" aria-label="按模块筛选">
      <option value="all">全部模块</option>
      ${M.modules.map(m => `<option value="${esc(m.name)}"${state.nbModule===m.name?' selected':''}>${esc(m.name)}（${m.count}）</option>`).join('')}
    </select>
    <select id="nbStatus" class="input" aria-label="按状态筛选">
      ${[['all','全部状态'],['done','已执行'],['partial','部分未执行'],['none','未执行']].map(([v,t]) => `<option value="${v}"${state.nbStatus===v?' selected':''}>${t}</option>`).join('')}
    </select>
    <span class="toolbar-note" id="nbCount"></span>
  </div>
  <div class="table-wrap">
    <table class="table">
      <thead><tr><th>编号</th><th>主题</th><th>模块</th><th class="num">代码</th><th>数据</th><th>状态</th></tr></thead>
      <tbody id="nbRows"></tbody>
    </table>
  </div>`;

function filteredNotebooks(){
  const q = state.nbQuery.trim().toLowerCase();
  return M.notebooks.filter(n => {
    if(state.nbModule !== 'all' && n.module !== state.nbModule) return false;
    const st = statusOf(n)[0];
    if(state.nbStatus === 'done' && st !== '已执行') return false;
    if(state.nbStatus === 'partial' && st !== '部分未执行') return false;
    if(state.nbStatus === 'none' && st !== '未执行') return false;
    if(!q) return true;
    return (`${n.num} ${n.title} ${n.module} ${n.data.join(' ')}`).toLowerCase().includes(q);
  });
}
function paintNbRows(){
  const list = filteredNotebooks();
  const tbody = $('#nbRows');
  if(!tbody) return;
  tbody.innerHTML = list.map(n => {
    const [st, kind] = statusOf(n);
    return `<tr data-nb="${n.num}" tabindex="0">
      <td class="mono">${pad(n.num)}</td>
      <td><span class="row-title">${esc(n.title)}</span><span class="row-sub">${esc(n.file)}</span></td>
      <td>${badge(n.module)}</td>
      <td class="num">${n.code}</td>
      <td>${dataChips(n)}</td>
      <td>${badge(st, kind)}</td>
    </tr>`;
  }).join('') || '<tr><td colspan="6" class="muted">没有匹配的 notebook。</td></tr>';
  $('#nbCount').textContent = `${list.length} / ${M.notebooks.length} 篇`;
}
AFTER.notebooks = paintNbRows;

RENDER.data = () => `
  <header class="page-head">
    <p class="eyebrow">Data</p>
    <h1>数据字典</h1>
    <p class="lede">${M.data.length} 个文件，原始数据只读；notebook 内统一以 ../data/ 引用。教材数据位于 data/textbook/。</p>
  </header>
  <div class="toolbar">
    <input id="dataQuery" class="input" type="search" placeholder="搜索文件名或引用编号…" value="${esc(state.dataQuery)}">
    <select id="dataKind" class="input" aria-label="数据类型">
      <option value="all">全部</option>
      <option value="root"${state.dataKind==='root'?' selected':''}>根目录</option>
      <option value="textbook"${state.dataKind==='textbook'?' selected':''}>教材数据</option>
    </select>
    <button class="btn" data-action="verify-data">校验可访问性</button>
    <span class="toolbar-note" id="dataCount"></span>
  </div>
  <div class="callout">校验通过 HTTP HEAD 逐个请求，仅在静态服务（本地 http.server 或 GitHub Pages）下有效；用于确认上传后没有漏传数据文件。引用方仅统计 <code>../data/</code> 相对引用。</div>
  <div class="table-wrap">
    <table class="table">
      <thead><tr><th>文件</th><th>类型</th><th class="num">体积</th><th>引用方</th><th>校验</th></tr></thead>
      <tbody id="dataRows"></tbody>
    </table>
  </div>`;

function filteredData(){
  const q = state.dataQuery.trim().toLowerCase();
  return M.data.filter(d => {
    if(state.dataKind !== 'all' && d.kind !== state.dataKind) return false;
    if(!q) return true;
    return (`${d.name} ${d.usedBy.join(' ')}`).toLowerCase().includes(q);
  });
}
function paintDataRows(){
  const tbody = $('#dataRows');
  if(!tbody) return;
  const list = filteredData();
  tbody.innerHTML = list.map((d, i) => `<tr>
    <td><span class="mono">${esc(d.name)}</span></td>
    <td>${d.kind === 'textbook' ? badge('教材', 'accent') : badge('根目录')}</td>
    <td class="num">${size(d.size)}</td>
    <td>${d.usedBy.length ? d.usedBy.map(n => `<button class="btn small" data-nb="${n}">${pad(n)}</button>`).join(' ') : '<span class="muted">未引用</span>'}</td>
    <td class="mono" data-verify="${M.data.indexOf(d)}">—</td>
  </tr>`).join('') || '<tr><td colspan="5" class="muted">没有匹配的数据文件。</td></tr>';
  $('#dataCount').textContent = `${list.length} / ${M.data.length} 个`;
}
AFTER.data = paintDataRows;

RENDER.docs = () => `
  <header class="page-head">
    <p class="eyebrow">Documents</p>
    <h1>教材正文</h1>
    <p class="lede">${M.docs.length} 份 PDF：30 章正文、4 篇附录与参考文献。只读资料，不参与代码运行。</p>
  </header>
  <div class="table-wrap">
    <table class="table">
      <thead><tr><th>章</th><th>主题</th><th>文件</th><th class="num">体积</th></tr></thead>
      <tbody>${M.docs.map(d => `<tr>
        <td class="mono">${esc(d.chapter)}</td>
        <td>${esc(d.topic || '—')}</td>
        <td><a href="${encodeURI(d.path)}" target="_blank" rel="noopener">${esc(d.file)}</a></td>
        <td class="num">${size(d.size)}</td>
      </tr>`).join('')}</tbody>
    </table>
  </div>`;

RENDER.ppts = () => `
  <header class="page-head">
    <p class="eyebrow">Slides</p>
    <h1>授课课件</h1>
    <p class="lede">${M.ppts.length} 个 PPTX，覆盖 20 章；按“工具链 → 方法”组织，与教材章序不同。</p>
  </header>
  <div class="grid-cards">
    ${M.ppts.map(p => `<article class="case">
      <p class="eyebrow">第 ${esc(p.chapter)} 章</p>
      <h3><a href="${encodeURI(p.path)}" target="_blank" rel="noopener">${esc(p.topic)}</a></h3>
      <p class="mono">${esc(p.file)} · ${size(p.size)}</p>
    </article>`).join('')}
  </div>`;

RENDER.manual = () => `
  <header class="page-head">
    <p class="eyebrow">Archive</p>
    <h1>历史资料</h1>
    <p class="lede">${fmt(M.manual.files)} 个文件 / ${M.manual.sizeMB} MB，按 ${M.manual.categories.length} 个专题归档；只读，不承诺可运行。</p>
  </header>
  <div class="callout">这些是教材配套的 MATLAB / C 源码与旧课件，不参与 CI 与依赖管理。Python 等价实现见 notebooks/ 的对应篇目。</div>
  <div class="table-wrap">
    <table class="table">
      <thead><tr><th>专题目录</th><th class="num">文件</th><th class="num">体积</th></tr></thead>
      <tbody>${M.manual.categories.map(c => `<tr><td class="mono">${esc(c.name)}</td><td class="num">${fmt(c.files)}</td><td class="num">${c.size} MB</td></tr>`).join('')}</tbody>
    </table>
  </div>`;

RENDER.modelit = () => `
  <header class="page-head">
    <p class="eyebrow">Cases</p>
    <h1>独立建模案例</h1>
    <p class="lede">${M.modelit.cases.length} 个专题 / ${fmt(M.modelit.files)} 个文件，与 notebook 分开维护，强调可直接运行与结果复现。</p>
    ${M.modelit.localOnly ? '<div class="callout warn">此目录被 .gitignore 排除，仅在本地工作树中可见；GitHub Pages 上只保留说明，不提供文件下载。</div>' : ''}
  </header>
  <div class="grid-cards">
    ${M.modelit.cases.map(c => `<article class="case">
      <h3>${esc(c.name)} ${c.published ? '' : '<span class="badge warn">本地</span>'}</h3>
      <p>${esc(c.note || '—')}</p>
      <p class="mono" style="margin-top:8px">${c.files} 个文件 · ${c.size} MB</p>
    </article>`).join('')}
  </div>
  <section class="card" style="margin-top:14px">
    <h2>约定</h2>
    <p class="small muted">一个案例一个目录；随机过程显式传入种子；输出写入案例内 output/；超过 5 MB 的数据走 LFS 或下载脚本。</p>
  </section>`;

RENDER.tools = () => `
  <header class="page-head">
    <p class="eyebrow">Tools</p>
    <h1>本地工具集</h1>
    <p class="lede">全部在浏览器内执行，不上传任何文件。预览与检索需要 HTTP 静态服务；GitHub Pages 下直接可用。</p>
  </header>
  <div class="grid-2">
    <section class="card">
      <h2>环境与安装命令</h2>
      <div class="tool-row">
        <select id="envOs" class="input" aria-label="操作系统"><option value="win">Windows</option><option value="unix">macOS / Linux</option></select>
        <label class="switch"><input type="checkbox" id="envMl"> 安装 ml 可选组</label>
      </div>
      <pre id="envCmds" style="margin-top:10px"></pre>
      <button class="btn" data-action="copy-env">复制命令</button>
    </section>
    <section class="card">
      <h2>数据可访问性</h2>
      <p class="small muted">对 ${M.data.length} 个数据文件发 HEAD 请求，确认静态托管后路径未失效。</p>
      <button class="btn" data-action="verify-data">开始校验</button>
      <div id="verifyOut" class="tool-output small" style="margin-top:10px"></div>
    </section>
  </div>
  <section class="card">
    <h2>Notebook 全文检索</h2>
    <div class="tool-row">
      <input id="ftQuery" class="input" type="search" placeholder="至少 2 个字符，例如 灰色预测、linprog" style="flex:1 1 260px">
      <select id="ftScope" class="input" aria-label="检索范围"><option value="all">全部模块</option>${M.modules.map(m => `<option value="${esc(m.name)}">${esc(m.name)}</option>`).join('')}</select>
      <button class="btn primary" data-action="fulltext">检索</button>
    </div>
    <progress id="ftBar" value="0" max="1" hidden></progress>
    <div id="ftResults" class="tool-output" style="margin-top:12px"></div>
  </section>
  <div class="grid-2">
    <section class="card">
      <h2>依赖反查</h2>
      <div class="tool-row"><input id="depQuery" class="input" type="search" placeholder="输入库名，如 tensorflow、pulp" style="flex:1"><button class="btn" data-action="dep-search">查找</button></div>
      <div id="depResults" class="tool-output small" style="margin-top:10px"></div>
    </section>
    <section class="card">
      <h2>路径检查</h2>
      <div class="tool-row"><input id="pathInput" class="input" type="text" placeholder="notebooks/31.线性规划.ipynb" style="flex:1"><button class="btn" data-action="check-path">检查</button></div>
      <div id="pathResult" class="tool-output small" style="margin-top:10px"></div>
    </section>
  </div>
  <section class="card">
    <h2>引用复制</h2>
    <div class="tool-row">
      <select id="citeNb" class="input">${M.notebooks.map(n => `<option value="${n.num}">${pad(n.num)} ${esc(n.title)}</option>`).join('')}</select>
      <button class="btn" data-action="cite">复制 Markdown 链接</button>
    </div>
    <p class="tool-note" style="margin-top:8px">输出形如 [31 线性规划](notebooks/31.线性规划.ipynb)，可直接粘贴到 README 或 issue。</p>
  </section>`;

function envCommands(){
  const win = ($('#envOs')?.value || 'win') === 'win';
  const ml = !!$('#envMl')?.checked;
  const lines = win
    ? ['py -3.11 -m venv .venv', '.venv\\Scripts\\activate', 'python -m pip install -r requirements.txt']
    : ['python3.11 -m venv .venv', 'source .venv/bin/activate', 'python -m pip install -r requirements.txt'];
  if(ml) lines.push('python -m pip install -e ".[ml]"');
  lines.push('python scripts/check_project.py', 'jupyter lab');
  return lines.join('\n');
}
function refreshEnv(){
  const el = $('#envCmds');
  if(el) el.textContent = envCommands();
}
AFTER.tools = () => { refreshEnv(); renderDeps(); };

RENDER.about = () => `
  <header class="page-head">
    <p class="eyebrow">About</p>
    <h1>关于这个页面</h1>
    <p class="lede">单文件静态导航页，数据来自仓库真实文件扫描；无后端、无外部依赖、不收集访问数据。</p>
  </header>
  <div class="grid-2">
    <section class="card">
      <h2>重新生成</h2>
      <p class="small muted">仓库结构或篇数变化后，重跑脚本即可刷新内嵌清单：</p>
      <pre>python scripts/build_index.py
python scripts/build_index.py --repo-url https://github.com/yohoten/Mathematical-Modeling-Atlas</pre>
      <p class="small muted">不带参数时自动读取 <code>git remote get-url origin</code>，顶栏仓库链接不会退回占位符。</p>
      <p class="small muted">脚本只读取文件名、标题、H2/H3、数据引用与体积，不写入除 index.html 之外的文件。</p>
    </section>
    <section class="card">
      <h2>部署到 GitHub Pages</h2>
      <ol class="small">
        <li>把仓库推送到 GitHub，默认分支设为 main；仓库根已有 <code>.nojekyll</code>，Pages 不会再做 Jekyll 转换。</li>
        <li>Settings → Pages → Build and deployment → Deploy from a branch。</li>
        <li>选择 main / (root)，保存后等待发布。</li>
        <li>访问 https://yohoten.github.io/Mathematical-Modeling-Atlas/。</li>
      </ol>
      <p class="small muted">.ipynb 预览、全文检索与数据校验都依赖同源 HTTP，Pages 下可用；直接 file:// 打开时仅浏览功能可用。被 <code>.gitignore</code> 排除的目录（当前为 <code>modelit/</code>）不会随 Pages 发布，页面会将它们标注为“本地”。</p>
    </section>
  </div>
  <section class="card">
    <h2>口径与边界</h2>
    <p class="small">篇数与体积由脚本扫描得出：notebook ${M.repo.counts.notebooks} 篇、数据 ${M.repo.counts.data} 个、PDF ${M.repo.counts.docs} 份、课件 ${M.repo.counts.ppts} 个、历史资料 ${fmt(M.repo.counts.manual)} 个文件、案例 ${M.repo.counts.modelit} 个文件。工作树约 ${M.repo.sizeMB} MB（不含 .git）。</p>
    <p class="small">质量门禁读取 scripts/check_project.py 的汇总；ERROR ${M.checks.error}（基线内 ${M.checks.baseline}，基线外 ${M.checks.outside}）、WARN ${M.checks.warn}、INFO ${M.checks.info}。基线是已确认的历史问题，不代表新代码可以新增 ERROR。</p>
  </section>
  <section class="card">
    <h2>许可与第三方</h2>
    <p class="small">原创代码与文字采用 <a href="LICENSE">MIT License</a>。docs/ 教材 PDF、ppts/ 课件、manual/ 配套代码版权归原作者/出版方，不随 MIT 授权发布。35 篇教材练习稿（MIT，2020，Zhanghan Wang）的逐篇去向与许可全文见 <a href="THIRD-PARTY.md">THIRD-PARTY.md</a>。</p>
  </section>`;

function openLayer(id){
  const el = $('#' + id);
  el.classList.add('open');
  el.setAttribute('aria-hidden', 'false');
  document.body.classList.add('lock');
  const focusable = el.querySelector('input,button,a');
  if(focusable) focusable.focus({preventScroll:true});
}
function closeLayer(id){
  const el = $('#' + id);
  el.classList.remove('open');
  el.setAttribute('aria-hidden', 'true');
  if(!$('.drawer.open') && !$('.modal.open') && !$('.palette.open')) document.body.classList.remove('lock');
}

function openNotebook(num){
  const n = M.notebooks.find(x => x.num === num);
  if(!n) return;
  $('#drawerKicker').textContent = `Notebook ${pad(n.num)} · ${n.module}`;
  $('#drawerTitle').textContent = n.title;
  const [st, kind] = statusOf(n);
  $('#drawerBody').innerHTML = `
    <div class="meta-grid">
      <div><span>代码单元</span><b>${n.code}</b></div>
      <div><span>未执行</span><b>${n.unexec}</b></div>
      <div><span>体积</span><b>${size(n.size)}</b></div>
      <div><span>模块</span><b>${esc(n.module)}</b></div>
      <div><span>状态</span><b>${badge(st, kind)}</b></div>
      <div><span>编号</span><b>${pad(n.num)}</b></div>
    </div>
    <div class="actions">
      <button class="btn primary" data-preview="${n.num}">预览内容</button>
      <a class="btn" href="${encodeURI(n.path)}" download>下载 .ipynb</a>
      <button class="btn" data-copy="${esc(n.path)}">复制路径</button>
      <button class="btn" data-copy="jupyter lab ${esc(n.path)}">复制启动命令</button>
      <a class="btn ghost" href="${encodeURI(n.path)}" target="_blank" rel="noopener">原始文件</a>
    </div>
    <h3>数据依赖</h3>
    <p>${n.data.length ? n.data.map(d => `<span class="badge mono">${esc(d)}</span>`).join(' ') : '<span class="muted">无外部数据</span>'}</p>
    <h3>结构</h3>
    ${n.sections.length ? `<ol class="outline">${n.sections.map(s => `<li class="l${s.level}">${esc(s.text)}</li>`).join('')}</ol>` : '<p class="muted">无 H2/H3 标题。</p>'}
    <h3>摘要</h3>
    <p>${esc(n.summary || '（该篇没有“1. 问题背景”段落）')}</p>
    <p class="muted small mono">${esc(n.file)}</p>`;
  openLayer('drawer');
}

function srcOf(c){ return Array.isArray(c.source) ? c.source.join('') : (c.source || ''); }
function safeUrl(u){
  const s = String(u || '').trim();
  if(/^javascript:/i.test(s)) return '#';
  if(/^(https?:|mailto:|#|\.{0,2}\/)/i.test(s)) return esc(s);
  return '#';
}
function inlineMd(raw){
  let s = esc(raw);
  const codes = [];
  s = s.replace(/`([^`]+)`/g, (m, c) => { codes.push(`<code>${c}</code>`); return `\u0001${codes.length - 1}\u0001`; });
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, '$1<em>$2</em>');
  s = s.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, (m, alt) => `<span class="badge">图片：${alt || '未命名'}</span>`);
  s = s.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (m, text, url) => {
    const href = safeUrl(url);
    const ext = /^https?:/i.test(url) ? ' target="_blank" rel="noopener noreferrer"' : '';
    return `<a href="${href}"${ext}>${text}</a>`;
  });
  s = s.replace(/\u0001(\d+)\u0001/g, (m, i) => codes[+i]);
  return s;
}
function tableMd(rows){
  const cells = r => r.trim().replace(/^\||\|$/g, '').split('|').map(x => x.trim());
  const head = cells(rows[0]);
  const body = rows.slice(rows[1] && /^\|?\s*:?-{3,}/.test(rows[1]) ? 2 : 1).map(cells);
  return `<table class="md-table"><thead><tr>${head.map(h => `<th>${inlineMd(h)}</th>`).join('')}</tr></thead><tbody>${body.map(r => `<tr>${r.map(c => `<td>${inlineMd(c)}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
}
function mdToHtml(src){
  const blocks = [];
  let text = String(src || '').replace(/\r\n/g, '\n');
  text = text.replace(/```[^\n]*\n([\s\S]*?)```/g, (m, code) => {
    blocks.push(`<pre class="code"><code>${esc(code.replace(/\n$/, ''))}</code></pre>`);
    return `\n\u0000${blocks.length - 1}\u0000\n`;
  });
  const lines = text.split('\n');
  const out = [];
  let i = 0;
  const blank = s => !s.trim();
  const startsBlock = s => /^(#{1,6}\s|>|\||\s*[-*]\s+|\s*\d+\.\s+|\u0000)/.test(s);
  while(i < lines.length){
    const line = lines[i];
    if(blank(line)){ i++; continue; }
    let m = line.match(/^\u0000(\d+)\u0000$/);
    if(m){ out.push(blocks[+m[1]]); i++; continue; }
    m = line.match(/^(#{1,6})\s+(.*)$/);
    if(m){ const l = Math.min(m[1].length, 4); out.push(`<h${l}>${inlineMd(m[2])}</h${l}>`); i++; continue; }
    if(/^\s*([-*_])\1{2,}\s*$/.test(line)){ out.push('<hr>'); i++; continue; }
    if(/^>\s?/.test(line)){
      const buf = [];
      while(i < lines.length && /^>\s?/.test(lines[i])){ buf.push(lines[i].replace(/^>\s?/, '')); i++; }
      out.push(`<blockquote>${inlineMd(buf.join(' '))}</blockquote>`); continue;
    }
    if(/^\|/.test(line)){
      const rows = [];
      while(i < lines.length && /^\|/.test(lines[i])){ rows.push(lines[i]); i++; }
      out.push(tableMd(rows)); continue;
    }
    if(/^\s*[-*]\s+/.test(line)){
      const items = [];
      while(i < lines.length && /^\s*[-*]\s+/.test(lines[i])){ items.push(lines[i].replace(/^\s*[-*]\s+/, '')); i++; }
      out.push(`<ul>${items.map(x => `<li>${inlineMd(x)}</li>`).join('')}</ul>`); continue;
    }
    if(/^\s*\d+\.\s+/.test(line)){
      const items = [];
      while(i < lines.length && /^\s*\d+\.\s+/.test(lines[i])){ items.push(lines[i].replace(/^\s*\d+\.\s+/, '')); i++; }
      out.push(`<ol>${items.map(x => `<li>${inlineMd(x)}</li>`).join('')}</ol>`); continue;
    }
    const buf = [];
    while(i < lines.length && !blank(lines[i]) && !startsBlock(lines[i])){ buf.push(lines[i]); i++; }
    if(!buf.length){ i++; continue; }
    out.push(`<p>${inlineMd(buf.join(' '))}</p>`);
  }
  return out.join('\n');
}
function outputHtml(outs){
  return outs.map(o => {
    if(o.output_type === 'stream') return `<div class="out">${esc((o.text || []).join(''))}</div>`;
    if(o.output_type === 'error') return `<div class="out bad">${esc((o.traceback || []).join('\n'))}</div>`;
    const d = o.data || {};
    let html = '';
    if(d['text/plain']) html += `<div class="out">${esc((d['text/plain'] || []).join(''))}</div>`;
    if(d['image/png']){
      if(state.showImages){
        const b64 = (d['image/png'] || []).join('');
        html += `<div class="out"><img loading="lazy" alt="notebook 输出图片" src="data:image/png;base64,${b64}"></div>`;
      } else {
        html += `<div class="out muted">[图片输出已折叠，可在右上角开启“显示图片”]</div>`;
      }
    }
    if(d['text/html']) html += `<div class="out muted">[HTML 输出已省略渲染，共 ${(d['text/html'] || []).join('').length} 字符]</div>`;
    return html;
  }).join('');
}
function countImages(nb){
  let n = 0;
  (nb.cells || []).forEach(c => (c.outputs || []).forEach(o => { if(o.data && o.data['image/png']) n++; }));
  return n;
}
function renderCells(nb){
  return `<div class="nb-meta">${nb.cells.length} 个单元 · ${countImages(nb)} 张输出图片 · ${nb.nbformat}.${nb.nbformat_minor}</div>` +
    nb.cells.map(c => {
      if(c.cell_type === 'markdown') return `<div class="md">${mdToHtml(srcOf(c))}</div>`;
      if(c.cell_type !== 'code') return '';
      return `<div class="cell"><div class="cell-head">In [${c.execution_count == null ? ' ' : c.execution_count}]</div><pre class="code"><code>${esc(srcOf(c))}</code></pre>${outputHtml(c.outputs || [])}</div>`;
    }).join('');
}
async function previewNotebook(num){
  const n = M.notebooks.find(x => x.num === num);
  if(!n) return;
  $('#modalTitle').textContent = `${pad(n.num)} ${n.title}`;
  $('#imgToggle').checked = state.showImages;
  openLayer('modal');
  const body = $('#modalBody');
  body.innerHTML = '<p class="muted">正在读取 notebook…</p>';
  try{
    let nb = state.cache[num];
    if(!nb){
      const res = await fetch(encodeURI(n.path), {cache:'no-store'});
      if(!res.ok) throw new Error('HTTP ' + res.status);
      nb = JSON.parse(await res.text());
      state.cache[num] = nb;
    }
    body.innerHTML = renderCells(nb);
  }catch(err){
    body.innerHTML = `<div class="callout bad">无法读取 <code>${esc(n.path)}</code>：${esc(err.message)}。<br><br>预览依赖 fetch 同源读取。请通过 HTTP 打开本页，例如在仓库根运行 <code>python -m http.server 8000</code> 后访问 <code>http://localhost:8000/</code>；直接双击 file:// 打开时浏览器会拦截。GitHub Pages 部署后可直接使用。</div>`;
  }
}

function toast(msg){
  const el = $('#toast');
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(toast._t);
  toast._t = setTimeout(() => el.classList.remove('show'), 2200);
}
function copyText(text){
  const done = () => toast('已复制到剪贴板');
  if(navigator.clipboard && window.isSecureContext){
    navigator.clipboard.writeText(text).then(done, () => fallbackCopy(text, done));
  } else fallbackCopy(text, done);
}
function fallbackCopy(text, done){
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  try{ document.execCommand('copy'); done(); }catch(e){ toast('复制失败，请手动选择'); }
  ta.remove();
}

function buildPalette(){
  const items = [];
  M.notebooks.forEach(n => items.push({kind:'Notebook', label:`${pad(n.num)} ${n.title}`, meta:n.module, run:() => openNotebook(n.num)}));
  M.data.forEach(d => items.push({kind:'数据', label:d.name, meta:size(d.size), run:() => { go('data'); state.dataQuery = d.name; const q = $('#dataQuery'); if(q) q.value = d.name; paintDataRows(); }}));
  M.docs.forEach(d => items.push({kind:'文档', label:`第 ${d.chapter} 章 ${d.topic}`, meta:'PDF', run:() => go('docs')}));
  M.ppts.forEach(p => items.push({kind:'课件', label:`${p.chapter} ${p.topic}`, meta:'PPTX', run:() => go('ppts')}));
  return items;
}
function openPalette(){
  state.palette = buildPalette();
  state.pIdx = 0;
  $('#paletteInput').value = '';
  renderPalette('');
  openLayer('palette');
  $('#paletteInput').focus();
}
function renderPalette(q){
  const list = state.palette.filter(it => !q || (it.label + ' ' + it.meta).toLowerCase().includes(q.toLowerCase())).slice(0, 40);
  state.paletteShown = list;
  state.pIdx = Math.min(state.pIdx, Math.max(list.length - 1, 0));
  $('#paletteList').innerHTML = list.map((it, i) => `<button class="palette-item${i === state.pIdx ? ' active' : ''}" data-palette="${i}" role="option">
    <span>${it.kind}</span><span>${esc(it.label)}</span><small>${esc(it.meta || '')}</small>
  </button>`).join('') || '<p class="muted" style="padding:14px">没有匹配项。</p>';
}
function runPalette(i){
  const it = (state.paletteShown || [])[i];
  if(!it) return;
  closeLayer('palette');
  setTimeout(() => it.run(), 0);
}

async function verifyData(){
  const out = $('#verifyOut');
  if(out) out.textContent = '校验中…';
  const list = M.data;
  let next = 0, ok = 0, fail = [];
  async function worker(){
    while(next < list.length){
      const i = next++;
      const d = list[i];
      const cell = document.querySelector(`[data-verify="${i}"]`);
      try{
        const res = await fetch(encodeURI(d.path), {method:'HEAD', cache:'no-store'});
        if(res.ok){ ok++; if(cell) cell.textContent = '✓'; }
        else { fail.push(d.path); if(cell){ cell.textContent = '✗'; cell.classList.add('bad'); } }
      }catch(e){ fail.push(d.path); if(cell) cell.textContent = '—'; }
    }
  }
  await Promise.all([worker(), worker(), worker()]);
  const msg = `完成：${ok}/${list.length} 个可访问${fail.length ? `，失败 ${fail.length} 个` : ''}`;
  if(out) out.innerHTML = `<p class="${fail.length ? 'bad' : 'ok'}">${msg}</p>${fail.length ? `<pre>${esc(fail.join('\n'))}</pre>` : ''}`;
  toast(msg);
}

async function fullText(){
  const q = ($('#ftQuery')?.value || '').trim();
  if(q.length < 2){ toast('请输入至少 2 个字符'); return; }
  const scope = $('#ftScope')?.value || 'all';
  const list = M.notebooks.filter(n => scope === 'all' || n.module === scope);
  const bar = $('#ftBar'), box = $('#ftResults');
  bar.hidden = false; bar.max = list.length; bar.value = 0;
  box.innerHTML = '<p class="muted">正在读取并检索…</p>';
  const queue = list.slice();
  const hits = [];
  let done = 0;
  async function worker(){
    while(queue.length){
      const nb = queue.shift();
      try{
        const res = await fetch(encodeURI(nb.path), {cache:'no-store'});
        if(!res.ok) throw new Error(res.status);
        const json = JSON.parse(await res.text());
        const found = [];
        (json.cells || []).forEach((c, ci) => {
          const text = srcOf(c);
          const idx = text.toLowerCase().indexOf(q.toLowerCase());
          if(idx >= 0) found.push({ci, snippet: text.slice(Math.max(0, idx - 50), idx + q.length + 80).replace(/\s+/g, ' ')});
        });
        if(found.length) hits.push({nb, found});
      }catch(e){ /* 单个失败不阻断 */ }
      done++; bar.value = done;
    }
  }
  await Promise.all([worker(), worker(), worker()]);
  box.innerHTML = hits.length
    ? `<p class="small muted">${hits.length} 篇命中，共 ${hits.reduce((s, h) => s + h.found.length, 0)} 处。</p>` + hits.map(h => `
      <div class="case" style="margin-bottom:8px">
        <h3><button class="btn small" data-nb="${h.nb.num}">${pad(h.nb.num)}</button> ${esc(h.nb.title)}</h3>
        ${h.found.slice(0, 4).map(f => `<p class="small mono muted">单元 ${f.ci}：…${esc(f.snippet)}…</p>`).join('')}
        ${h.found.length > 4 ? `<p class="small muted">另有 ${h.found.length - 4} 处</p>` : ''}
      </div>`).join('')
    : '<p class="muted">没有命中。该功能按原文字符串匹配，不做分词。</p>';
}

function renderDeps(q){
  q = (q || '').trim().toLowerCase();
  const box = $('#depResults');
  if(!box) return;
  if(!q){ box.innerHTML = '<p class="muted">输入库名后显示引用它的 notebook。</p>'; return; }
  const list = M.notebooks.filter(n => n.deps.some(d => d.toLowerCase().includes(q)));
  box.innerHTML = list.length
    ? list.map(n => `<p><button class="btn small" data-nb="${n.num}">${pad(n.num)}</button> ${esc(n.title)} <span class="muted">· ${esc(n.deps.join('、'))}</span></p>`).join('')
    : '<p class="muted">没有 notebook 在元信息中声明该依赖。</p>';
}
async function checkPath(){
  const p = ($('#pathInput')?.value || '').trim();
  const box = $('#pathResult');
  if(!p){ box.textContent = '请输入仓库内相对路径。'; return; }
  box.textContent = '检查中…';
  try{
    const res = await fetch(encodeURI(p), {method:'HEAD', cache:'no-store'});
    box.innerHTML = res.ok
      ? `<p class="ok">HTTP ${res.status} · 可访问</p><p class="mono small">${esc(p)}</p>`
      : `<p class="bad">HTTP ${res.status} · 不可访问</p>`;
  }catch(e){
    box.innerHTML = `<p class="bad">请求失败：${esc(e.message)}</p><p class="small muted">请通过 HTTP 服务访问，或在 Pages 上测试。</p>`;
  }
}

document.addEventListener('click', e => {
  const t = e.target;
  const nav = t.closest('[data-view]');
  if(nav){ go(nav.dataset.view); return; }
  const nb = t.closest('[data-nb]');
  if(nb){ openNotebook(Number(nb.dataset.nb)); return; }
  const pv = t.closest('[data-preview]');
  if(pv){ previewNotebook(Number(pv.dataset.preview)); return; }
  const close = t.closest('[data-close]');
  if(close){ closeLayer(close.dataset.close); return; }
  const copy = t.closest('[data-copy]');
  if(copy){ copyText(copy.dataset.copy); return; }
  const copyEl = t.closest('[data-copy-el]');
  if(copyEl){ const el = document.getElementById(copyEl.dataset.copyEl); if(el) copyText(el.textContent); return; }
  const pal = t.closest('[data-palette]');
  if(pal){ runPalette(Number(pal.dataset.palette)); return; }
  const act = t.closest('[data-action]');
  if(act){
    const a = act.dataset.action;
    if(a === 'verify-data') verifyData();
    if(a === 'copy-env') copyText(envCommands());
    if(a === 'fulltext') fullText();
    if(a === 'dep-search') renderDeps($('#depQuery')?.value);
    if(a === 'check-path') checkPath();
    if(a === 'cite'){
      const n = M.notebooks.find(x => x.num === Number($('#citeNb')?.value));
      if(n) copyText(`[${pad(n.num)} ${n.title}](${n.path})`);
    }
    return;
  }
  if(t.id === 'drawer') closeLayer('drawer');
  if(t.id === 'modal') closeLayer('modal');
  if(t.id === 'palette') closeLayer('palette');
});

document.addEventListener('input', e => {
  const t = e.target;
  if(t.id === 'nbQuery'){ state.nbQuery = t.value; paintNbRows(); }
  if(t.id === 'dataQuery'){ state.dataQuery = t.value; paintDataRows(); }
  if(t.id === 'paletteInput'){ state.pIdx = 0; renderPalette(t.value); }
  if(t.id === 'depQuery'){ renderDeps(t.value); }
});
document.addEventListener('change', e => {
  const t = e.target;
  if(t.id === 'nbModule'){ state.nbModule = t.value; paintNbRows(); }
  if(t.id === 'nbStatus'){ state.nbStatus = t.value; paintNbRows(); }
  if(t.id === 'dataKind'){ state.dataKind = t.value; paintDataRows(); }
  if(t.id === 'envOs' || t.id === 'envMl'){ refreshEnv(); }
  if(t.id === 'imgToggle'){
    state.showImages = t.checked;
    const num = Number(($('#modalTitle').textContent || '').slice(0, 2));
    const nb = state.cache[num];
    if(nb) $('#modalBody').innerHTML = renderCells(nb);
  }
});
document.addEventListener('keydown', e => {
  if((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k'){ e.preventDefault(); openPalette(); return; }
  if(e.key === 'Escape'){
    if($('.palette.open')) closeLayer('palette');
    else if($('.modal.open')) closeLayer('modal');
    else if($('.drawer.open')) closeLayer('drawer');
    return;
  }
  if($('.palette.open')){
    const list = state.paletteShown || [];
    if(e.key === 'ArrowDown'){ e.preventDefault(); state.pIdx = Math.min(state.pIdx + 1, list.length - 1); renderPalette($('#paletteInput').value); }
    if(e.key === 'ArrowUp'){ e.preventDefault(); state.pIdx = Math.max(state.pIdx - 1, 0); renderPalette($('#paletteInput').value); }
    if(e.key === 'Enter'){ e.preventDefault(); runPalette(state.pIdx); }
    return;
  }
  const row = e.target.closest && e.target.closest('tr[data-nb]');
  if(row && (e.key === 'Enter' || e.key === ' ')){ e.preventDefault(); openNotebook(Number(row.dataset.nb)); }
});

function applyTheme(theme){
  document.documentElement.dataset.theme = theme;
  try{ localStorage.setItem('index-theme', theme); }catch(e){}
}
function initTheme(){
  let saved = null;
  try{ saved = localStorage.getItem('index-theme'); }catch(e){}
  if(saved){ document.documentElement.dataset.theme = saved; return; }
  if(window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches) document.documentElement.dataset.theme = 'dark';
}
$('#themeBtn').addEventListener('click', () => {
  applyTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
});
$('#searchOpen').addEventListener('click', openPalette);
if(M.repo.url){
  const a = $('#repoLink');
  a.href = M.repo.url;
  a.hidden = false;
}

window.addEventListener('hashchange', () => go(location.hash.slice(1) || 'overview', false));
initTheme();
renderNav();
go(location.hash.slice(1) || 'overview', false);
</script>
</body>
</html>
'''


def main() -> None:
    parser = argparse.ArgumentParser(description="生成仓库首页 index.html")
    parser.add_argument("--repo-url", default="", help="GitHub 仓库地址，用于顶栏入口")
    args = parser.parse_args()

    repo_url = args.repo_url or detect_repo_url()
    manifest = build_manifest(repo_url)
    payload = json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    meta_desc = (
        f"{manifest['repo']['counts']['notebooks']} 个数学建模 notebook、"
        f"{manifest['repo']['counts']['data']} 个数据文件、"
        f"{manifest['repo']['counts']['docs']} 份教材 PDF 与 "
        f"{manifest['repo']['counts']['ppts']} 个课件的浏览与检索入口。"
    )
    html = TEMPLATE.replace("__MANIFEST__", payload).replace("__META_DESC__", meta_desc)
    out = ROOT / "index.html"
    out.write_text(html, encoding="utf-8", newline="\n")
    print(f"wrote {out}")
    print(f"size {out.stat().st_size / 1024:.1f} KB | notebooks {len(manifest['notebooks'])} | "
          f"data {len(manifest['data'])} | docs {len(manifest['docs'])} | ppts {len(manifest['ppts'])} | "
          f"checks {manifest['checks']}")


if __name__ == "__main__":
    main()
