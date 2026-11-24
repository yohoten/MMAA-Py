#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 notebooks/textbook/ 的教材参考实现并入 notebooks/ 正式 notebook（一次性迁移）。

规则：
1. 主题已有对应 notebook 的，作为该篇“方法与实现”下的新小节插入（自动续编号）；
2. 主题无对应的，按 31—43 新建正式 notebook（STYLE 五段式骨架）；
3. 数据路径统一改写为 ../data/textbook/；代码输出清空，避免把上游运行结果带进来；
4. 脚本可重复执行：已存在同名小节或目标编号时跳过。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

BASE = Path("D:/CodingRation")
ROOT = next(p for p in BASE.iterdir() if p.is_dir() and p.name.startswith("10-"))
NB = ROOT / "notebooks"
TB = NB / "textbook"
DATA = "../data/textbook"

# 上游输入数据（写操作的目标不在此列，避免把结果写进 data/）
INPUTS = [
    "SVM_data.txt",
    "15.D 水库年径流与因子特征.txt",
    "12.D 飞机侦察地理坐标数据.txt",
    "12.D 遗传算法初步结果.txt",
    "14.D 多层次模糊综合评判数据.txt",
    "14.D 供应商选择决策.txt",
    "14.D 宏观投资效益.txt",
    "14.D 医院工作质量统计指标.txt",
    "15.D 导弹.txt",
]

# ---------------------------------------------------------------- 合并映射
MERGES = [
    ("04 图与网络模型及方法.ipynb", "03.networkx的基础操作及画图.ipynb", "4", "图的矩阵表示与基本运算"),
    ("10.1 聚类分析.ipynb", "10.系统聚类和K均值聚类.ipynb", "4", "Q 型聚类与树状图"),
    ("10.2 主成分分析.ipynb", "08.基于主成分分析的评价分析.ipynb", "4", "协方差特征值法"),
    ("10.3 因子分析.ipynb", "09.基于因子分析的学生成绩排序.ipynb", "4", "主成分法提取因子"),
    ("10.4 判别分析.ipynb", "07.基于线性判别分析的分类预测.ipynb", "4", "马氏距离判别与 Fisher 判别"),
    ("14.1 理想解法.ipynb", "02.综合评价法—TOPSIS法.ipynb", "4", "理想解法（TOPSIS 原型）"),
    ("14.2 模糊综合评判法.ipynb", "15.模糊数学的基本概念和基本运算.ipynb", "4", "模糊综合评判"),
    ("14.4 灰色关联分析法.ipynb", "17.灰色关联分析.ipynb", "4", "灰色关联度计算"),
    ("15.2 灰色预测模型.ipynb", "18.灰色GM预测模型.ipynb", "4", "GM(1,1) 完整算例"),
    ("15.3 差分方程.ipynb", "13.差分方程的概念和求解.ipynb", "4", "差分方程数值求解"),
    ("15.5 时间序列.ipynb", "20.时间序列数据准备.ipynb", "4", "时间序列分解"),
    ("08 时间序列.ipynb", "20.时间序列数据准备.ipynb", "4", "时间序列分析提纲"),
    ("15.7 神经元网络.ipynb", "19.人工神经网络.ipynb", "5", "BP 网络完整实现"),
    ("MPLClassifier.ipynb", "19.人工神经网络.ipynb", "5", "sklearn MLPClassifier"),
]

# ---------------------------------------------------------------- 新建清单
NEW = [
    dict(
        num="31", title="线性规划", module="优化", sources=["01 线性规划.ipynb"],
        background="线性规划在一组线性约束下优化线性目标，是资源分配、生产计划与运输问题的基础模型。本节用 `scipy.optimize.linprog` 求解标准形式，并对照教材算例核对结果。",
        goals=["掌握 `linprog` 的参数含义与不等式方向", "把实际问题整理为 A_ub·x ≤ b_ub 的标准形", "用约束回代与目标值校验求解结果"],
        summary="`linprog` 默认求最小值，约束需整理成 ≤ 形式；求解后应回代检查可行性，并留意无界与不可行两种状态。",
    ),
    dict(
        num="32", title="整数规划与目标规划", module="优化", sources=["02 整数规划.ipynb", "16 目标规划.ipynb"],
        background="整数规划要求部分或全部变量取整，目标规划则用偏差变量处理多目标冲突。两者都是线性规划的扩展，常见于排班、选址与多目标决策。",
        goals=["用 `pulp` 建立整数规划模型并求解", "理解目标规划中正、负偏差变量的含义", "能解读求解状态与灵敏度信息"],
        summary="`pulp` 建模按“变量—目标—约束—求解”四步进行；目标规划把多个目标写成偏差之和，再最小化总偏差。",
    ),
    dict(
        num="33", title="非线性规划", module="优化", sources=["03 非线性规划.ipynb"],
        background="当目标函数或约束含非线性项时，需要非线性规划方法。本节用 `scipy.optimize.minimize` 演示无约束与带约束问题的求解。",
        goals=["区分 `eq` 与 `ineq` 约束的写法", "根据问题特点选择求解方法", "识别局部最优与初值敏感性"],
        summary="约束以字典形式传入；非线性问题通常只保证局部最优，应换初值多次求解并比较。",
    ),
    dict(
        num="34", title="插值与拟合", module="数值方法", sources=["05 插值与拟合.ipynb", "15.6 插值与拟合.ipynb"],
        background="插值要求曲线通过已知点，拟合只要求整体误差最小。两者常用于数据补全、曲线平滑与经验公式提取，教材中分别给出了一维、二维与多项式情形的算例。",
        goals=["掌握一维与二维插值的使用", "理解多项式拟合与最小二乘的关系", "能判断何时用插值、何时用拟合"],
        summary="插值适合精确已知点，拟合适合含噪声数据；多项式阶数过高会出现过拟合，应结合残差判断。",
    ),
    dict(
        num="35", title="数理统计", module="统计", sources=["07 数理统计.ipynb"],
        background="参数估计与假设检验是统计推断的两条主线：前者估计总体参数及其区间，后者判断关于总体的命题是否成立。",
        goals=["会做点估计与区间估计", "理解 t 检验的前提与 p 值含义", "能用 `scipy.stats` 完成常见检验"],
        summary="检验结论依赖显著性水平与前提假设；报告应同时给出统计量、p 值与置信区间，而不是只写“显著”。",
    ),
    dict(
        num="36", title="支持向量机", module="机器学习", sources=["09 支持向量机.ipynb"],
        background="支持向量机通过最大化间隔寻找分类超平面，并用核函数处理非线性可分问题，适合小样本、高维数据的分类。",
        goals=["理解间隔、支持向量与软间隔", "会用 `sklearn` 训练并评估 SVM", "能调整核函数与惩罚参数 C"],
        summary="核函数与 C 共同决定边界复杂度；特征标准化对 SVM 的结果影响显著。",
    ),
    dict(
        num="37", title="典型相关分析与多维标度", module="多元分析", sources=["10.5 典型相关分析.ipynb", "10.7 多维标度法.ipynb"],
        background="典型相关分析寻找两组变量的线性组合，使二者相关系数最大；多维标度把样本间的距离矩阵还原为低维坐标，用于结构可视化。",
        goals=["理解典型相关系数与典型变量的含义", "会用 MDS 还原低维坐标并作图", "能解释 stress 指标衡量拟合优劣"],
        summary="CCA 关注两组变量之间的关联，MDS 关注距离结构的保序还原；两者都需结合业务含义解释维度。",
    ),
    dict(
        num="38", title="偏最小二乘回归", module="回归分析", sources=["11 偏最小二乘回归分析.ipynb"],
        background="当自变量多、彼此共线且样本量小时，偏最小二乘回归通过提取潜变量同时解释自变量与因变量，常用于光谱与化学计量数据。",
        goals=["理解潜变量提取的基本思想", "会用交叉验证确定成分数", "能解读回归系数与变量重要性"],
        summary="成分数过少欠拟合、过多过拟合；应以交叉验证误差最小为准，而不是一味增加成分。",
    ),
    dict(
        num="39", title="智能优化算法", module="优化", sources=["12.1 模拟退火算法.ipynb", "12.2 遗传算法.ipynb"],
        background="模拟退火与遗传算法不依赖梯度，适合组合优化与多峰问题。前者以概率接受劣解跳出局部最优，后者通过选择、交叉、变异迭代种群。",
        goals=["理解退火温度与 Metropolis 接受准则", "掌握遗传算法的编码、选择、交叉与变异", "能调参并观察收敛过程"],
        summary="初温、降温系数、种群规模与变异率决定搜索效果；随机算法应多次运行并报告统计结果。",
    ),
    dict(
        num="40", title="综合评价扩展方法", module="综合评价", sources=["14.3 数据包络分析.ipynb", "14.5 主成分分析法.ipynb", "14.6 秩和比综合评价法.ipynb"],
        background="除 AHP 与 TOPSIS 外，DEA 用投入产出比评价决策单元效率，主成分法用降维合成综合指标，秩和比按秩次排序分档，三者适用于不同的数据条件。",
        goals=["理解 DEA 的效率值与投入产出导向", "会用主成分构造综合评价得分", "掌握秩和比的编秩与分档方法"],
        summary="方法选择取决于指标性质与样本量；不同方法的排序结果应相互对照，而非只报单一结论。",
    ),
    dict(
        num="41", title="微分方程模型", module="动态模型", sources=["15.1 微分方程模型.ipynb"],
        background="微分方程描述连续变化的动态系统，常用于人口、传染病与物理过程建模。解析解难以求得时，用数值积分近似。",
        goals=["会从机理出发建立一阶或高阶方程", "能用 `scipy.integrate` 求数值解", "能分析平衡点及其稳定性"],
        summary="建模关键是厘清变量与变化率的因果关系；数值解需检查步长、刚性与初值敏感性。",
    ),
    dict(
        num="42", title="马尔可夫预测", module="动态模型", sources=["15.4 马尔可夫预测.ipynb"],
        background="马尔可夫链用转移概率描述状态演化，适合天气、市场份额等具有无后效性的序列预测。",
        goals=["会从历史数据估计转移矩阵", "计算多步转移概率", "判断平稳分布与长期趋势"],
        summary="转移矩阵每行元素和为 1；长期行为由平稳分布刻画，短期预测依赖当前状态。",
    ),
    dict(
        num="43", title="机器学习补充方法", module="机器学习", sources=["GMM.ipynb", "高斯过程回归.ipynb", "CS299_MDP.ipynb"],
        background="高斯混合模型做概率密度聚类，高斯过程回归给出带不确定性的预测，价值迭代求解马尔可夫决策过程。三者分别代表概率建模、贝叶斯回归与序贯决策的常用工具。",
        goals=["理解 GMM 的 EM 迭代与协方差结构", "会用高斯过程回归给出预测区间", "掌握价值迭代的收敛条件"],
        summary="三种方法都显式建模不确定性；超参数、核函数与收敛阈值直接影响结果，应结合验证集判断。",
    ),
]

MODULE_DISPLAY = {
    "sklearn": "scikit-learn", "skimage": "scikit-image", "pil": "pillow",
    "yaml": "pyyaml", "dateutil": "python-dateutil", "mpl_toolkits": "matplotlib",
}
STDLIB = set(getattr(__import__("sys"), "stdlib_module_names", set())) | {"pprint", "random", "warnings", "IPython"}


def to_lines(text: str) -> list[str]:
    lines = text.splitlines(keepends=True)
    if lines and lines[-1].endswith("\n"):
        lines[-1] = lines[-1][:-1]
    return lines or [""]


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": to_lines(text)}


def code(text: str) -> dict:
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": to_lines(text)}


def rewrite(text: str) -> str:
    for name in INPUTS:
        text = text.replace(f"'{name}'", f"'{DATA}/{name}'").replace(f'"{name}"', f'"{DATA}/{name}"')
    return text


def demote(text: str) -> str:
    out = []
    in_fence = False
    for ln in text.splitlines():
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(ln)
            continue
        if in_fence:
            out.append(ln)
            continue
        if ln.startswith("# "):
            continue  # 去掉源文件一级标题
        if ln.startswith("### "):
            out.append("#####" + ln[3:])
        elif ln.startswith("## "):
            out.append("####" + ln[2:])
        else:
            out.append(ln)
    return "\n".join(out).strip("\n")


def source_cells(path: Path) -> list[dict]:
    nb = json.loads(path.read_text(encoding="utf-8"))
    cells = []
    for c in nb["cells"]:
        text = "".join(c.get("source", []))
        if c.get("cell_type") == "markdown":
            text = demote(text)
            if text.strip():
                cells.append(md(text))
        else:
            text = rewrite(text)
            if text.strip():
                cells.append(code(text))
    return cells


def find_section(cells: list[dict], no: str) -> int:
    pat = re.compile(rf"^##\s+{no}\.\s")
    for i, c in enumerate(cells):
        if c.get("cell_type") != "markdown":
            continue
        if any(pat.match(ln) for ln in "".join(c.get("source", [])).splitlines()):
            return i
    return -1


def next_section_no(cells: list[dict], anchor: int, stop: int, no: str) -> int:
    minor = 0
    for c in cells[anchor:stop]:
        if c.get("cell_type") != "markdown":
            continue
        for ln in "".join(c.get("source", [])).splitlines():
            m = re.match(rf"###\s+{no}\.(\d+)", ln)
            if m:
                minor = max(minor, int(m.group(1)))
    return minor + 1


def do_merge(src_name: str, dst_name: str, section_no: str, title: str) -> str:
    src = TB / src_name
    dst = NB / dst_name
    if not src.exists():
        return f"SKIP 源缺失 {src_name}"
    nb = json.loads(dst.read_text(encoding="utf-8"))
    cells = nb["cells"]
    for c in cells:
        if c.get("cell_type") != "markdown":
            continue
        if any(ln.startswith("### ") and title in ln for ln in "".join(c.get("source", [])).splitlines()):
            return f"SKIP 已存在 {dst_name} :: {title}"

    anchor = find_section(cells, section_no)
    if anchor < 0:
        return f"FAIL 找不到锚点 ## {section_no}. @ {dst_name}"
    stop = len(cells)
    for i in range(anchor + 1, len(cells)):
        if cells[i].get("cell_type") != "markdown":
            continue
        lines = "".join(cells[i].get("source", [])).splitlines()
        if any(ln.startswith("## ") and "小结" in ln for ln in lines):
            stop = i
            break

    minor = next_section_no(cells, anchor, stop, section_no)
    heading = f"### {section_no}.{minor} {title}"
    chapter = src_name.split()[0]
    intro = (
        f"{heading}\n\n"
        f"> 来源：教材参考实现《数学建模算法与应用》第 {chapter} 章的练习稿"
        "（MIT，Zhanghan Wang），代码保持原样，仅将数据路径改为 `../data/textbook/` 并清空输出。"
    )
    block = [md(intro)] + source_cells(src)
    nb["cells"] = cells[:stop] + block + cells[stop:]
    dst.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return f"MERGE {src_name} -> {dst_name} as {heading}"


def collect_meta(srcs: list[Path]) -> tuple[list[str], list[str]]:
    deps, data = [], []
    for p in srcs:
        nb = json.loads(p.read_text(encoding="utf-8"))
        for c in nb["cells"]:
            if c.get("cell_type") != "code":
                continue
            text = "".join(c.get("source", []))
            for ln in text.splitlines():
                m = re.match(r"\s*(?:from\s+([A-Za-z_][\w.]*)\s+import|import\s+([A-Za-z_][\w.]*))", ln)
                if m:
                    mod = (m.group(1) or m.group(2)).split(".")[0]
                    if mod not in STDLIB:
                        name = MODULE_DISPLAY.get(mod.lower(), mod)
                        if name not in deps:
                            deps.append(name)
            for name in INPUTS:
                if name in text and name not in data:
                    data.append(name)
    return deps, data


def make_new(spec: dict) -> str:
    num, title = spec["num"], spec["title"]
    dst = NB / f"{num}.{title}.ipynb"
    if dst.exists():
        return f"SKIP 已存在 {dst.name}"

    srcs = [TB / s for s in spec["sources"]]
    if any(not s.exists() for s in srcs):
        return f"FAIL 源缺失 {spec['sources']}"
    deps, data = collect_meta(srcs)
    deps_text = "、".join(deps[:5]) + ("等" if len(deps) > 5 else "")
    data_text = "、".join(f"`{DATA}/{d}`" for d in data) if data else "无（内置示例）"
    cells = [
        md(f"# {num} {title}"),
        md(f"> **模块**：{spec['module']} ｜ **数据**：{data_text} ｜ **依赖**：{deps_text or '—'}"),
        md("## 1. 问题背景\n\n" + spec["background"]),
        md("## 2. 学习目标\n\n" + "\n".join(f"- {g}" for g in spec["goals"])),
        md("## 3. 环境与数据\n\n" + f"- 依赖：{deps_text or '无第三方依赖'}\n- 数据：{data_text}"),
        md("## 4. 方法与实现"),
    ]
    for k, (src, path) in enumerate(zip(spec["sources"], srcs), start=1):
        topic = re.sub(r"^\d+(\.\d+)?\s*", "", src)[:-6].strip()
        cells.append(md(f"### 4.{k} {topic}"))
        cells.extend(source_cells(path))
    cells.append(md("## 5. 小结\n\n" + spec["summary"]))
    cells.append(
        md(
            "> 内容来源：教材参考实现《数学建模算法与应用》练习稿（MIT，Zhanghan Wang），"
            "原始文件已并入本篇，见 `THIRD-PARTY.md`。"
        )
    )
    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11.9"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    dst.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return f"NEW {dst.name} (sources={len(srcs)}, cells={len(cells)}, deps={len(deps)})"


def main() -> None:
    report = []
    for src, dst, section_no, title in MERGES:
        report.append(do_merge(src, dst, section_no, title))
    for spec in NEW:
        report.append(make_new(spec))
    print("\n".join(report))
    print(f"\nmerged={sum(r.startswith('MERGE') for r in report)} new={sum(r.startswith('NEW') for r in report)} "
          f"skip={sum(r.startswith('SKIP') for r in report)} fail={sum(r.startswith('FAIL') for r in report)}")


if __name__ == "__main__":
    main()
