#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""仓库规范检查器（仅标准库，Python 3.10+）。

把 README / notebooks/STYLE.md 中的规范变成可执行门禁：数据路径、命名、
执行状态、图片引用、依赖声明与文档链接。

用法：
    python scripts/check_project.py                     # 报告当前问题
    python scripts/check_project.py --update-baseline   # 记录当前 ERROR 为基线
    python scripts/check_project.py --strict            # WARN 也视为失败
    python scripts/check_project.py --rule R009         # 只跑某条规则

退出码：0 通过；1 存在基线外的 ERROR（或 --strict 下存在 WARN）。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / ".check_baseline.json"

SUPPORTED_PY = {(3, 10), (3, 11)}
REQUIRED = ["README.md", "LICENSE", "pyproject.toml", "requirements.txt", ".gitignore", "notebooks", "data"]
SKIP_DIRS = {"docs", "manual", "ppts", ".git", ".venv", "venv", ".ipynb_checkpoints", "cifar-10-batches-py"}
DATA_EXT = {".csv", ".xlsx", ".xls", ".xlsm", ".json", ".txt", ".dat", ".pkl", ".npy", ".mat", ".png", ".jpg", ".jpeg"}

RULES = {
    "R000": "notebook 无法解析",
    "R001": "缺少必需目录/文件",
    "R002": "notebook 命名不合规",
    "R003": "nbformat 版本偏低",
    "R004": "内核 Python 版本不在支持范围",
    "R005": "执行状态异常",
    "R006": "attachment: 图片引用",
    "R007": "绝对路径",
    "R008": "反斜杠路径",
    "R009": "数据文件引用问题",
    "R010": "配图占位行",
    "R011": "空代码单元",
    "R012": "单文件过大",
    "R013": "标题或内联 HTML 不规范",
    "R014": "依赖未在 pyproject 声明",
    "R015": "大文件未纳入 Git LFS",
    "R016": "文档相对链接失效",
    "R017": "运行产物遗留在仓库树",
    "R018": "文档中引用的路径不存在",
}

SEV_ORDER = {"ERROR": 0, "WARN": 1, "INFO": 2}


@dataclass
class Finding:
    sev: str
    rule: str
    path: str
    detail: str

    @property
    def key(self) -> str:
        return f"{self.rule}|{self.path}|{self.detail}"


FINDINGS: list[Finding] = []


def rel_path(p: str | Path) -> str:
    try:
        return Path(p).relative_to(ROOT).as_posix()
    except ValueError:
        return Path(p).as_posix()


def add(sev: str, rule: str, path: str | Path, detail: str) -> None:
    FINDINGS.append(Finding(sev, rule, rel_path(path), detail))


def cell_src(cell: dict) -> str:
    src = cell.get("source", "")
    return "".join(src) if isinstance(src, list) else str(src)


def code_cells(nb: dict) -> list[dict]:
    return [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]


def markdown_cells(nb: dict) -> list[dict]:
    return [c for c in nb.get("cells", []) if c.get("cell_type") == "markdown"]


def find_notebooks() -> list[Path]:
    out = []
    for p in ROOT.rglob("*.ipynb"):
        if any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts):
            continue
        out.append(p)
    return sorted(out)


# ------------------------------------------------------------------ 结构检查


def check_layout() -> None:
    for name in REQUIRED:
        if not (ROOT / name).exists():
            add("ERROR", "R001", name, "缺失；README 中承诺的结构必须在磁盘上成立")


def check_filenames(notebooks: list[Path]) -> None:
    seen: dict[str, str] = {}
    for p in notebooks:
        if p.parent.name != "notebooks":
            continue
        stem = p.stem
        if stem.endswith(" "):
            add("ERROR", "R002", p, "文件名在 .ipynb 前含空格，应删除")
        m = re.match(r"^(\d{2})\.", stem)
        if not m:
            add("ERROR", "R002", p, "不符合 `NN.主题.ipynb`（两位序号 + 半角句点）")
            continue
        num = m.group(1)
        if num in seen:
            add("ERROR", "R002", p, f"序号 {num} 与 {seen[num]} 重复")
        seen[num] = p.name
        if re.search(r"\s{2,}", stem):
            add("WARN", "R002", p, "文件名含连续空格")
        if "—" in stem or " - " in stem:
            add("WARN", "R002", p, "主题与序号间使用破折号，STYLE.md 建议用中文冒号或直接相连")


def check_notebook(nb: dict, p: Path) -> None:
    if nb.get("nbformat") != 4:
        add("ERROR", "R003", p, f"nbformat={nb.get('nbformat')}，应为 4")
    elif nb.get("nbformat_minor", 0) < 5:
        add("WARN", "R003", p, f"nbformat_minor={nb.get('nbformat_minor')}，建议统一为 4.5")

    version = str(nb.get("metadata", {}).get("language_info", {}).get("version", ""))
    m = re.match(r"(\d+)\.(\d+)", version)
    if m and (int(m.group(1)), int(m.group(2))) not in SUPPORTED_PY:
        add("WARN", "R004", p, f"内核 Python {version}，仓库只支持 3.10/3.11（见 pyproject requires-python）")

    codes = code_cells(nb)
    counts = [c.get("execution_count") for c in codes]
    nulls = sum(1 for c in counts if not isinstance(c, int))
    seq = [c for c in counts if isinstance(c, int)]
    if nulls:
        add("WARN", "R005", p, f"{nulls}/{len(codes)} 个代码单元无执行计数；提交前执行 Restart & Run All")
    if seq and (seq != sorted(seq) or seq[0] != 1):
        add("WARN", "R005", p, f"执行计数不连续（{seq[0]}…{seq[-1]}，共 {len(seq)} 个）")

    empty = sum(1 for c in codes if not cell_src(c).strip())
    if empty:
        add("WARN", "R011", p, f"{empty} 个空代码单元")

    if p.stat().st_size > 1024 * 1024:
        add("WARN", "R012", p, f"{p.stat().st_size / 1024 / 1024:.1f} MB，建议把内嵌图片外置到 notebooks/assets/")

    refs = 0
    has_payload = False
    for c in nb.get("cells", []):
        refs += cell_src(c).count("attachment:")
        if c.get("attachments"):
            has_payload = True
    if refs:
        add("WARN" if has_payload else "ERROR", "R006", p, f"{refs} 处 `attachment:` 引用；应改为外部相对路径 ../data/images/…")

    placeholders = sum(cell_src(c).count("原稿配图未随") for c in nb.get("cells", []))
    if placeholders:
        add("INFO", "R010", p, f"{placeholders} 处配图占位行待回补（见 notebooks/FIGURE_TODO.csv）")

    h1 = sum(1 for c in markdown_cells(nb) if cell_src(c).lstrip().startswith("# "))
    if h1 != 1:
        add("WARN", "R013", p, f"一级标题 {h1} 个，应恰好 1 个（`# NN 标题`）")
    for c in markdown_cells(nb):
        src = cell_src(c)
        for tag in ("<span", "<font", "<div", "<center", "<br"):
            if tag in src:
                add("WARN", "R013", p, f"存在内联 HTML `{tag}>`，改用 Markdown 层级表达")
                break


# ------------------------------------------------------------------ 路径检查

READ_CALL = re.compile(
    r"\b(read_csv|read_excel|read_table|read_json|read_pickle|read_parquet|"
    r"loadtxt|genfromtxt|imread|load|open)\s*\("
)
LITERAL = re.compile(r"""(['"])([^'"\n]{1,300})\1""")
ABS_PATH = re.compile(r"(?<![\w.])[A-Za-z]:[\\/]")
POSIX_ABS = re.compile(r"(?<![\w.])/(?:Users|home|mnt|Volumes)/")
WRITE_MODE = re.compile(r"""['"][waxrb+]{1,4}['"]""")


def _call_args(src: str, open_idx: int) -> str:
    depth = 0
    for i in range(open_idx, len(src)):
        ch = src[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return src[open_idx + 1 : i]
    return src[open_idx + 1 :]


def _pathlike(s: str) -> bool:
    return any(ch in s for ch in "/\\") or Path(s).suffix.lower() in DATA_EXT


def check_paths(nb: dict, p: Path) -> None:
    nb_dir = p.parent
    for idx, cell in enumerate(code_cells(nb), start=1):
        src = cell_src(cell)
        hit = ABS_PATH.search(src)
        if hit:
            add("ERROR", "R007", p, f"代码单元 {idx} 含绝对路径 `{hit.group(0)}`；改用相对仓库根的路径")
        else:
            hit = POSIX_ABS.search(src)
            if hit:
                add("ERROR", "R007", p, f"代码单元 {idx} 含绝对路径 `{hit.group(0)}…`")

        for m in READ_CALL.finditer(src):
            name = m.group(1)
            args = _call_args(src, m.end() - 1)
            if name == "open" and WRITE_MODE.search(args):
                continue

            joined = []
            for jm in re.finditer(r"os\.path\.join\s*\(", args):
                inner = _call_args(args, jm.end() - 1)
                parts = [s for _, s in LITERAL.findall(inner)]
                if parts:
                    joined.append("/".join(parts))

            literals = [s for _, s in LITERAL.findall(args)]
            candidates = joined or [s for s in literals if _pathlike(s)][:1]
            if not candidates:
                continue

            ref = candidates[0]
            if ABS_PATH.match(ref) or POSIX_ABS.match(ref):
                continue

            normalized = ref.replace("\\", "/")
            if "\\" in ref:
                add("WARN", "R008", p, f"代码单元 {idx} 使用反斜杠路径 `{ref}`")
            if normalized.startswith("data/"):
                rest = normalized[len("data/") :]
                if not (ROOT / "data" / rest).exists():
                    add("ERROR", "R009", p, f"代码单元 {idx} 引用缺失文件 `data/{rest}`")
                else:
                    add("WARN", "R009", p, f"代码单元 {idx} 用 `data/…` 根相对路径；仅当内核工作目录为仓库根时成立，应改为 `../data/…`")
                continue

            if not (nb_dir / normalized).resolve().exists():
                if "/" not in normalized:
                    add("INFO", "R009", p, f"代码单元 {idx} 以裸文件名 `{normalized}` 读取，依赖变量锚点，未能静态校验")
                else:
                    add("ERROR", "R009", p, f"代码单元 {idx} 引用缺失文件 `{normalized}`")


# ------------------------------------------------------------------ 依赖检查

MODULE_TO_DIST = {
    "sklearn": "scikit-learn",
    "skimage": "scikit-image",
    "skfuzzy": "scikit-fuzzy",
    "fuzzy": "scikit-fuzzy",
    "cv2": "opencv-python",
    "pil": "pillow",
    "yaml": "pyyaml",
    "dateutil": "python-dateutil",
    "bs4": "beautifulsoup4",
    "mpl_toolkits": "matplotlib",
}

_IMPORT_RE = re.compile(r"\s*(?:from\s+([A-Za-z_][\w.]*)\s+import|import\s+([A-Za-z_][\w.]*))")


def _scan_imports(text: str) -> set[str]:
    out = set()
    for line in text.splitlines():
        m = _IMPORT_RE.match(line)
        if m:
            out.add((m.group(1) or m.group(2)).split(".")[0])
    return out


def _imports_from_py(path: Path) -> set[str]:
    import ast

    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return _scan_imports(text)
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            mods.add(node.module.split(".")[0])
    return mods


def declared_distributions() -> set[str]:
    p = ROOT / "pyproject.toml"
    if not p.exists():
        return set()
    text = p.read_text(encoding="utf-8")
    if tomllib is None:
        specs = re.findall(r'"([A-Za-z0-9_.\-]+)(?:\[[^\]]*\])?[><=!~;]', text)
        return {s.lower().replace("_", "-") for s in specs}

    data = tomllib.loads(text)
    project = data.get("project", {})
    raw = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        raw.extend(extra)
    out = set()
    for item in raw:
        m = re.match(r"([A-Za-z0-9_.\-]+)", item.strip())
        if m:
            out.add(m.group(1).lower().replace("_", "-"))
    return out


def check_dependencies(notebooks: list[Path]) -> None:
    declared = declared_distributions()
    if not declared:
        add("ERROR", "R014", "pyproject.toml", "未能读取依赖声明，依赖检查已跳过")
        return

    stdlib = set(getattr(sys, "stdlib_module_names", set())) | {"__future__"}
    local = {p.name for p in ROOT.iterdir() if p.is_dir()}
    seen: dict[str, list[str]] = defaultdict(list)

    for p in list(notebooks) + sorted((ROOT / "modelit").rglob("*.py")):
        mods: set[str] = set()
        if p.suffix == ".ipynb":
            try:
                nb = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            for cell in code_cells(nb):
                src = "\n".join(
                    ln for ln in cell_src(cell).splitlines() if not ln.lstrip().startswith(("%", "!", "?"))
                )
                mods |= _scan_imports(src)
        else:
            mods = _imports_from_py(p)
        for mod in mods:
            if mod and mod not in stdlib and mod not in local:
                seen[mod].append(rel_path(p))

    for mod, where in sorted(seen.items()):
        dist = MODULE_TO_DIST.get(mod.lower(), mod.lower().replace("_", "-"))
        if dist not in declared:
            add("ERROR", "R014", where[0], f"导入 `{mod}`（发行包 {dist}）未在 pyproject 依赖中声明，涉及 {len(where)} 个文件")


# ------------------------------------------------------------------ 体积与文档


def check_large_files() -> None:
    attrs = ROOT / ".gitattributes"
    lfs_on = attrs.exists() and "filter=lfs" in attrs.read_text(encoding="utf-8")
    big = [
        p
        for p in ROOT.rglob("*")
        if p.is_file() and ".git" not in p.parts and p.stat().st_size > 5 * 1024 * 1024
    ]
    if not big or lfs_on:
        return
    big.sort(key=lambda q: q.stat().st_size, reverse=True)
    total = sum(q.stat().st_size for q in big) / 1024 / 1024
    add("INFO", "R015", ".gitattributes", f"{len(big)} 个文件 >5 MB，合计 {total:.0f} MB，尚未启用 LFS；最大项 {rel_path(big[0])}（{big[0].stat().st_size / 1024 / 1024:.0f} MB）")


def check_artifacts() -> None:
    for d in [p for p in ROOT.rglob("output") if p.is_dir() and ".git" not in p.parts]:
        files = [f for f in d.rglob("*") if f.is_file()]
        if files:
            add("INFO", "R017", d, f"{len(files)} 个运行产物在树内（.gitignore 已忽略 output/，需清理或确认是否保留样例）")


LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)\)")
BACKTICK = re.compile(r"`([^`\n]+)`")
PLACEHOLDER_HINT = re.compile(r"x{2,}|\*|…|\.\.\.|待补|\{|\}")

README_TARGETS = [
    "README.md",
    "docs/README.md",
    "notebooks/README.md",
    "notebooks/STYLE.md",
    "notebooks/textbook/README.md",
    "ppts/README.md",
    "manual/README.md",
    "modelit/README.md",
    "data/README.md",
]


def _resolve_link(doc: Path, target: str) -> Path | None:
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return None
    target = target.split("#", 1)[0].strip()
    if not target or ("." not in target and "/" not in target):
        return None  # 纯中文词是语法示例，不是链接
    return (doc.parent / target).resolve()


def check_docs() -> None:
    top_dirs = {p.name for p in ROOT.iterdir() if p.is_dir()}
    for doc in [ROOT / name for name in README_TARGETS if (ROOT / name).exists()]:
        text = doc.read_text(encoding="utf-8", errors="replace")
        # 行内代码里的“链接”是语法示例（如 `![](../data/images/xxx.png)`），不算真实链接
        prose = re.sub(r"`[^`\n]*`", "", text)
        for target in LINK.findall(prose):
            resolved = _resolve_link(doc, target)
            if resolved is not None and not resolved.exists():
                add("ERROR", "R016", doc, f"链接目标不存在：`{target}`")
        for token in BACKTICK.findall(text):
            token = token.strip()
            if "/" not in token or PLACEHOLDER_HINT.search(token):
                continue
            head = token.split("/", 1)[0]
            if head not in top_dirs:
                continue
            if not (ROOT / token).exists():
                add("WARN", "R018", doc, f"正文提及的路径不存在：`{token}`")


# ---------------------------------------------------------------------- 主流程


def collect() -> tuple[list[Path], int]:
    notebooks = find_notebooks()
    check_layout()
    check_filenames(notebooks)
    for p in notebooks:
        try:
            nb = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            add("ERROR", "R000", p, f"无法解析 notebook：{exc}")
            continue
        check_notebook(nb, p)
        check_paths(nb, p)
    check_dependencies(notebooks)
    check_large_files()
    check_artifacts()
    check_docs()
    n_data = (
        len([q for q in (ROOT / "data").glob("*") if q.is_file() and q.suffix.lower() != ".md"])
        if (ROOT / "data").exists()
        else 0
    )
    return notebooks, n_data


def load_baseline() -> set[str]:
    if not BASELINE.exists():
        return set()
    try:
        return set(json.loads(BASELINE.read_text(encoding="utf-8")).get("entries", []))
    except (OSError, json.JSONDecodeError):
        return set()


def write_baseline(entries: list[str]) -> None:
    payload = {
        "说明": "仓库当前已知问题基线；修复后请删除对应条目。由 scripts/check_project.py 生成。",
        "entries": sorted(entries),
    }
    BASELINE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render(findings: list[Finding], baseline: set[str], limit: int) -> None:
    grouped: dict[tuple[str, str], list[Finding]] = defaultdict(list)
    for f in findings:
        grouped[(f.rule, f.sev)].append(f)

    for rule, sev in sorted(grouped, key=lambda k: (SEV_ORDER[k[1]], k[0])):
        items = grouped[(rule, sev)]
        in_base = sum(1 for f in items if f.key in baseline)
        extra = f"，基线内 {in_base} 项" if in_base and sev == "ERROR" else ""
        print(f"\n{rule} {RULES.get(rule, '')}  [{sev}] {len(items)} 项{extra}")

        cells: dict[str, list[Finding]] = defaultdict(list)
        for f in items:
            cells[f.path].append(f)
        shown = 0
        for path, group in sorted(cells.items()):
            detail = group[0].detail + (f"（同类 {len(group)} 处）" if len(group) > 1 else "")
            print(f"  {path} — {detail}")
            shown += 1
            if shown >= limit:
                print(f"  … 另有 {len(cells) - shown} 个文件同类问题")
                break


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="仓库规范检查")
    parser.add_argument("--update-baseline", action="store_true", help="将当前 ERROR 写入基线")
    parser.add_argument("--strict", action="store_true", help="WARN 也计为失败")
    parser.add_argument("--rule", default="", help="只显示包含该规则码的问题")
    parser.add_argument("--limit", type=int, default=6, help="每条规则最多列出的文件数")
    args = parser.parse_args(argv)

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    notebooks, n_data = collect()
    if args.rule:
        FINDINGS[:] = [f for f in FINDINGS if args.rule.upper() in f.rule]

    baseline = set() if args.update_baseline else load_baseline()

    print(f"仓库规范检查  {ROOT}")
    print(f"Python {sys.version.split()[0]} | notebook {len(notebooks)} 个 | data 文件 {n_data} 个")
    render(FINDINGS, baseline, args.limit)

    errors = [f for f in FINDINGS if f.sev == "ERROR"]
    warns = [f for f in FINDINGS if f.sev == "WARN"]
    infos = [f for f in FINDINGS if f.sev == "INFO"]
    new_errors = [f for f in errors if f.key not in baseline]
    fixed = sorted(baseline - {f.key for f in errors})

    print("\n" + "-" * 78)
    print(f"汇总：ERROR {len(errors)}（基线内 {len(errors) - len(new_errors)}，基线外 {len(new_errors)}） / WARN {len(warns)} / INFO {len(infos)}")

    if args.update_baseline:
        write_baseline([f.key for f in errors])
        print(f"已写入基线 {BASELINE.name}：{len(errors)} 条 ERROR 记为已知问题。")
        return 0

    if fixed:
        print(f"提示：{len(fixed)} 条基线项已不再复现，可从 {BASELINE.name} 删除。")

    if new_errors:
        print("存在基线外 ERROR，检查未通过。")
        if not BASELINE.exists():
            print("首次接入可先执行：python scripts/check_project.py --update-baseline")
        return 1
    if args.strict and warns:
        print("--strict：存在 WARN，检查未通过。")
        return 1
    print("检查通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
