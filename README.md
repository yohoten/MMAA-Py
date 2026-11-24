# Python数学建模算法与应用

# Mathematical Modeling Atlas

> 以 Jupyter Notebook 为载体的数学建模学习仓库：43 个实践 notebook（01—43）、20 章配套课件、35 份教材正文 PDF，以及按专题归档的历史资料与独立建模案例。35 篇教材参考实现已按主题并入对应 notebook。
>
> 在线浏览：根目录 [`index.html`](index.html) 提供 notebook、数据与文档的检索、结构查看与按需预览；GitHub Pages 部署后即为仓库首页。

## 项目特色

- **系统性**：教材正文（`docs/`）、授课课件（`ppts/`）、实践代码（`notebooks/`）三者按主题互相呼应。
- **实践导向**：每个 notebook 含任务说明、算法实现与结果可视化，编号 01—43 与主题一一对应。
- **教材融合**：35 篇教材参考实现（MIT，2020）已按主题拆入 01—43 的对应小节；其中 21 篇主题原先空缺，整理为 31—43 号，不再单列归档目录。
- **可追踪**：版式规范（`notebooks/STYLE.md`）、缺图清单（`notebooks/FIGURE_TODO.csv`）与自动检查（`scripts/check_project.py`）共同约束内容质量。
- **模块化**：`modelit/` 存放相对独立的完整建模案例，可与 notebook 分开维护。

## 项目结构

```text
Python数学建模算法与应用/
├── notebooks/                  # 43 个 notebook（01—43，含教材实现融合）
│   ├── README.md               # 索引与状态表（数据、缺图、待修项）
│   ├── STYLE.md                # Notebook 版式规范
│   ├── FIGURE_TODO.csv         # 66 处待回补配图（35 行，按章节定位）
│   ├── 01.综合评价法—AHP层次分析法.ipynb …
│   └── 43.机器学习补充方法.ipynb
├── data/                       # 27 个数据文件（含 data/textbook/ 10 个教材数据）
│   └── README.md               # 数据字典：体积、引用方、缺失项
├── docs/                       # 教材正文：30 章 + 4 篇附录 + 参考文献（35 个 PDF / 8.5 MB）
│   └── README.md               # 章节索引、与 notebook 的主题对照、使用约定
├── ppts/                       # 章节课件 21 个（20 章，04 章分上下册，91 MB）
│   └── README.md               # 课件清单与体积
├── manual/                     # 历史 MATLAB / C 资料归档（522 文件 / 107 MB，只读）
│   └── README.md               # 31 类专题清单；上游第三方 README 保持原样
├── modelit/                    # 独立建模案例（19 文件 / 178 MB）
│   ├── README.md               # 案例说明与运行方式
│   ├── Markov_chain/           # 马尔可夫链与赌博模拟
│   ├── Monte_Carlo_simulation/ # 蒙特卡洛模拟
│   └── Object_classification/  # 物体分类（含 CIFAR-10 六个 batch）
├── scripts/                    # 规范检查、迁移与导航页生成脚本
│   ├── check_project.py        # 仓库规范检查（纯标准库，无需额外安装）
│   ├── merge_textbook.py       # 教材实现融合的逐篇映射（迁移记录）
│   └── build_index.py          # 扫描仓库并生成 index.html
├── index.html                  # 静态项目导航：浏览、预览、检索与工具集
├── THIRD-PARTY.md              # 上游教材实现的 MIT 许可与逐篇去向
├── pyproject.toml              # 依赖与工具配置的唯一来源
├── requirements.txt            # pip 兼容入口（等价于 -e ".[dev]"）
├── .pre-commit-config.yaml     # 提交前钩子
├── .gitattributes              # 行尾规范 + Git LFS 规则说明
├── .check_baseline.json        # 已确认问题的基线（修复后逐条删除）
├── Makefile                    # 常用任务封装（Windows 可直接用 python 命令）
├── LICENSE                     # MIT（不含 docs/、ppts/、manual/ 中的第三方资料）
└── README.md
```

工作树约 487 MB，其中 94 MB 数据、178 MB 案例数据、91 MB 课件、107 MB 历史资料（另有 `.git` 历史约 307 MB）。克隆前请留意：`data/bitcoin_data.csv`（73 MB）与 `modelit/Object_classification/cifar-10-batches-py/`（178 MB）是主要体积来源，LFS 规则见 `.gitattributes`。

## 目录索引

每个主目录都有一份与当前状态一致的 README；`manual/` 下另有 9 个上游第三方 README（GALib、模拟退火工具箱），保持原样不改写。

| 目录 | README | 内容 |
| --- | --- | --- |
| `notebooks/` | [`notebooks/README.md`](notebooks/README.md) | 43 个 notebook 的索引、数据依赖与待修项（含 35 篇教材实现的融合去向） |
| `data/` | [`data/README.md`](data/README.md) | 数据字典：体积、引用方、缺失引用 |
| `docs/` | [`docs/README.md`](docs/README.md) | 教材章节索引、与 notebook 的主题对照 |
| `ppts/` | [`ppts/README.md`](ppts/README.md) | 21 个课件的章节与体积 |
| `manual/` | [`manual/README.md`](manual/README.md) | 31 类历史资料清单与使用约定 |
| `modelit/` | [`modelit/README.md`](modelit/README.md) | 3 个案例的运行方式与已知缺陷 |

## 环境要求

- **Python 3.10 或 3.11**（`pyproject.toml` 已声明 `requires-python >=3.10,<3.12`）。3.12 及以上与当前 `numpy<2`、`pmdarima` 组合不兼容，3.9 及以下不在支持范围。
- **JupyterLab**（已列入依赖）或 VS Code + Jupyter 扩展。
- 依赖清单只维护在 `pyproject.toml`：直接依赖 17 个，`ml` 可选组（torch / tensorflow / prophet / neuralprophet / apyori）仅供 10、19、26、29、30、43 号 notebook 使用。

## 快速开始

```bash
# 1. 建环境（Windows 下用 py -3.11 指定解释器）
py -3.11 -m venv .venv
.venv\Scripts\activate

# 2. 安装（requirements.txt 只是 -e ".[dev]" 的转发）
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
# 需要深度学习或 Prophet 相关 notebook（10/19/26/29/30/43）时追加：
python -m pip install -e ".[ml]"

# 3. 启动
jupyter lab
```

使用 [uv](https://docs.astral.sh/uv/) 时：`uv sync --extra dev`。

内核工作目录应为 notebook 所在目录（JupyterLab 与 VS Code 默认如此），因此 notebook 里的 `../data/xxx` 才能正确解析。仓库根目录不是合法的工作目录。

## 在线浏览与导航页

根目录 `index.html` 是单文件静态导航页，无后端、无外部依赖：

- 浏览 43 篇 notebook 的模块、代码量、数据依赖与 H2/H3 结构；
- 预览 `.ipynb`（Markdown、代码与文本输出，图片按需展开）；
- 数据、教材 PDF、课件、历史资料与案例的统一索引；
- 工具集：环境命令生成、数据 HEAD 自检、notebook 全文检索、依赖反查、引用复制。

```bash
python scripts/build_index.py
python scripts/build_index.py --repo-url https://github.com/<user>/<repo>
```

页面内嵌清单由脚本扫描仓库生成，篇数或文件变化后重跑即可。预览与检索需要 HTTP 访问：GitHub Pages 部署后直接可用；直接双击 `file://` 打开时仅浏览功能可用。

## 规范与自动化门禁

| 命令 | 作用 |
| --- | --- |
| `python scripts/check_project.py` | 规范检查：数据路径、命名、执行状态、图片引用、依赖声明、文档链接 |
| `python scripts/check_project.py --strict` | 连 WARN 一起拦（CI 用） |
| `python scripts/check_project.py --update-baseline` | 把当前 ERROR 记为已知问题 |
| `make check` / `make lint` / `make fmt` | 等价封装（Windows 未装 make 时直接用上面的 python 命令） |
| `pre-commit install` | 提交前自动跑 ruff、nbqa 与规范检查 |

检查器只依赖标准库，在 3.10+ 上可直接运行；问题分 ERROR（阻断）、WARN（应修）、INFO（提示）三级。已有 `.check_baseline.json` 记录当前的 4 条已知 ERROR，因此门禁当天即可用：修好一条就从基线里删一条，而不是无限期豁免。

规则清单见 `scripts/check_project.py` 顶部的 `RULES`。其中最关键的几条：

- **R007** 禁止 `F:/`、`C:\` 之类的绝对路径；
- **R009** 校验 `read_csv` / `read_excel` / `np.loadtxt` / `os.path.join` 引用的数据文件是否真实存在；
- **R014** 校验代码里 import 的第三方库是否都在 `pyproject.toml` 中声明；
- **R006** 禁止 `attachment:` 图片引用（依赖 notebook 内嵌附件，导出即失效）；
- **R016** 校验 README / STYLE 中的相对链接是否存在。

## 内容地图

| 主题 | Notebook 编号 |
| --- | --- |
| 综合评价（AHP、TOPSIS） | 01—02 |
| 图论与网络（networkx、Floyd） | 03—06、28 |
| 多元分析与聚类（LDA、PCA、因子分析、聚类） | 07—10 |
| 回归分析（线性回归、正则化、多元线性回归） | 11—12、23 |
| 差分方程与 Leslie 种群模型 | 13—14 |
| 模糊数学（基础运算、模糊 C 均值） | 15—16 |
| 灰色系统（关联分析、GM 预测） | 17—18 |
| 人工神经网络 | 19 |
| 时间序列（数据准备、平滑、ARMA、ARIMA、Prophet、LSTM） | 20—22、24、27、29—30 |
| 关联规则挖掘（Apriori） | 25—26 |
| 优化模型（线性、整数、非线性、智能优化） | 31—33、39 |
| 数值方法（插值、拟合） | 34 |
| 统计推断与机器学习（SVM、PLS、GMM/GPR/MDP） | 35—36、38、43 |
| 多元分析补充（典型相关、多维标度） | 37 |
| 综合评价扩展（DEA、主成分评价、秩和比） | 40 |
| 微分方程与马尔可夫预测 | 41—42 |

教材章节与 notebook 并非一一对应，章节主题见 [`docs/README.md`](docs/README.md)。

## 推荐学习路径

1. **基础方法**：01—02（评价方法）→ 07—10（降维与聚类）。
2. **网络优化**：03—06 → 28（最短路径算法对照）。
3. **统计建模**：11—12、23（回归）→ 13—14（动态模型）。
4. **不确定性建模**：15—18（模糊数学与灰色系统）。
5. **预测专题**：20—22 → 24 → 27 → 29—30。
6. **关联分析**：25—26。
7. **优化与机器学习**：31—34 → 36 → 38—39 → 40—43。

## Notebook 命名与版式规范

统一格式 `NN.主题.ipynb`：两位序号 + 半角句点；主题用简洁中文，库名按官方写法（`NetworkX`、`Prophet`、`NeuralProphet`、`AHP`、`TOPSIS`、`ARMA`、`ARIMA`）；文件名末尾不留空格。

版式（标题与元信息、`1 / 1.1 / 1.1.1` 层级、H2 拆章、无内联 HTML）见 [`notebooks/STYLE.md`](notebooks/STYLE.md)。实验型 notebook 的固定骨架：

```text
# NN 标题
> **模块**：xx ｜ **数据**：`../data/xxx.csv` ｜ **依赖**：numpy、pandas
## 1. 问题背景
## 2. 学习目标      # 无序列表
## 3. 环境与数据    # 无序列表
## 4. 方法与实现    # 4.1 / 4.1.1 …
## 5. 小结
```

提交前必须 `Kernel → Restart & Run All`：`execution_count` 应从 1 连续递增，不提交报错堆栈与本机路径。当前检查器报出 45 项执行状态告警，包括既有 notebook 的跳号与新增 31—43 号的整体未执行，属于待修项。

## 数据约定

- `data/` 保存原始输入数据，只读；中间产物写入各案例 `output/`，该目录已在 `.gitignore` 中忽略。
- 路径统一相对 notebook 目录，用 `pathlib` 或字符串均可，但不得出现盘符路径：

```python
from pathlib import Path
DATA = Path("..") / "data"
df = pd.read_csv(DATA / "basketball.csv")
```

- 新增数据文件须是公开、可再分发的小体积数据集；超过 5 MB 的走 Git LFS 或提供下载脚本 + 校验和。`data/bitcoin_data.csv` 与 `data/Online_Retail.xlsx` 属于此列。

## 已知事项与待办

按检查器规则归类，均已进入 `.check_baseline.json` 或 WARN 清单：

**路径与数据**

- `28.Floyd算法求解最短路径问题 .ipynb` 的文件名在 `.ipynb` 前多一个空格（R002），改名时需同步 README 与正文引用。
- `notebooks/30.基于LSTM与Prophet的时间序列预测与对比.ipynb` 有 2 处 `F:/_4.Pycode_integration/...` 绝对路径（R007），应改为 `../data/flight.csv` 与 `../data/AirPassengers.csv`。
- `07` 号引用 `./experiment/data/data.xlsx`、`09` 号引用 `../data/score.xlsx`，两者仓库内不存在（R009）；`09` 另引用 `rule1.csv`，实际文件为 `data/rule1.xlsx`。
- `05`、`25`、`26` 使用 `data/xxx` 根相对路径（R009 WARN），仅在仓库根启动内核时有效。

**图片**

- 7 个 notebook 仍有 16 处 `attachment:` 引用（01 两处、02/03/07/11/25 各一处、19 九处）（R006）。19 号 3.0 MB，主要来自内嵌图片。
- 19 个 notebook 的 35 个单元共 66 处配图占位行，清单见 [`notebooks/FIGURE_TODO.csv`](notebooks/FIGURE_TODO.csv)，需从原始课件回补。

**环境与元数据**

- 30 份主干 notebook 与 modelit 1 份的内核版本不一致：29 份为 3.9.13，26 号为 3.13.2，29 号为 3.14.0，均不在 `requires-python` 声明的范围内（R004）；nbformat 混用 4.2（4 份）/ 4.4（24 份）/ 4.5（15 份）（R003）。统一做法：用 3.11 解释器重开内核后重新执行并保存。
- `23`、`24` 号为零代码单元的讲义型 notebook，`29` 号仍为占位稿（单单元格、无代码、无数据）。

**案例与资料**

- `modelit/Monte_Carlo_simulation/Simple_betting_system.py` 内容已损坏（`def rolupice（）`、`if roll =- 100` 等），无法执行；同名可用文件在 `modelit/Markov_chain/`。建议合并为单一案例目录。
- `modelit/Markov_chain/output/` 留有 5 个运行产物，按 `.gitignore` 本不该入库。
- `manual/` 522 文件 / 107 MB 为教材配套 MATLAB/C 代码与旧课件，**只读归档，不承诺可运行**；是否移出主仓（改为单独 release 或 LFS）待决策。
- 35 篇教材参考实现（MIT，2020，Zhanghan Wang）已按主题并入 01—43 的对应小节，原教材归档目录已移出项目；其中 21 篇主题在主干中空缺，整理为 31—43 号。逐篇去向与上游许可见 [`THIRD-PARTY.md`](THIRD-PARTY.md)。
- 新增的 31—43 号尚未执行（`execution_count` 为空）；其中 10、19、43 号的部分单元依赖 `tensorflow`，需先安装 `.[ml]` 再整篇运行。
- 仓库根目录尚未 `git init`。首次入库前请先决定 LFS 策略，否则一次提交会写入约 470 MB 二进制历史。

## 贡献指南

1. 一个 notebook 只解决一个主题，文件名符合 `NN.主题.ipynb`，序号不重复。
2. 顶部元信息的模块、数据、依赖与实际代码一致；数据只写真实读取的文件。
3. 提交前 `Restart & Run All`，删除空单元、报错堆栈与个人路径。
4. 运行 `python scripts/check_project.py`，确保没有新增 ERROR；修好既往问题后从 `.check_baseline.json` 删除对应条目。
5. 不提交 `.ipynb_checkpoints/`、`output/` 运行产物与超过 5 MB 且未走 LFS 的文件。

## 许可证与第三方资料

代码与原创文字采用 [MIT License](LICENSE)。`docs/` 中的教材 PDF、`ppts/` 中的课程课件、`manual/` 中的配套代码与旧课件版权归原作者/出版方所有，仅作学习参考，**不随本仓库的 MIT 授权发布**；如需再分发请自行取得授权。教材参考实现（MIT，2020，Zhanghan Wang）已并入 `notebooks/` 的对应小节，完整许可文本与逐篇对应关系见 [`THIRD-PARTY.md`](THIRD-PARTY.md)。
