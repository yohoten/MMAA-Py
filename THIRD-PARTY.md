# 第三方内容与许可

本仓库的 notebook 中包含来自下列上游项目的代码与文字。原始版权归原作者所有，按 MIT 许可使用；本仓库对融合内容做了路径与版式适配（见文末“修改说明”）。

## 数学建模教材参考实现

- **项目**：`RabbitWhite1/Mathematical-Modeling-In-Python`
- **作者**：Zhanghan Wang
- **许可**：MIT，Copyright (c) 2020 Zhanghan Wang
- **内容**：35 个 Jupyter 练习稿及 10 个配套 `.txt` 数据，对应《数学建模算法与应用》的章节编号（01—16 及 10.x / 12.x / 14.x / 15.x 子编号）。

35 篇练习稿已全部并入 `notebooks/`，原 `notebooks/textbook/` 归档目录不再保留。其中 14 篇作为既有 notebook 的新小节插入，21 篇整理为 31—43 号正式 notebook。

### 逐篇去向

| 原文件 | 去向 | 形式 |
| --- | --- | --- |
| `04 图与网络模型及方法.ipynb` | 03 号 4.3 | 并入小节 |
| `10.1 聚类分析.ipynb` | 10 号 4.4 | 并入小节 |
| `10.2 主成分分析.ipynb` | 08 号 4.3 | 并入小节 |
| `10.3 因子分析.ipynb` | 09 号 4.3 | 并入小节 |
| `10.4 判别分析.ipynb` | 07 号 4.3 | 并入小节 |
| `14.1 理想解法.ipynb` | 02 号 4.4 | 并入小节 |
| `14.2 模糊综合评判法.ipynb` | 15 号 4.3 | 并入小节 |
| `14.4 灰色关联分析法.ipynb` | 17 号 4.3 | 并入小节 |
| `15.2 灰色预测模型.ipynb` | 18 号 4.3 | 并入小节 |
| `15.3 差分方程.ipynb` | 13 号 4.3 | 并入小节 |
| `15.5 时间序列.ipynb` | 20 号 4.4 | 并入小节 |
| `08 时间序列.ipynb` | 20 号 4.5 | 并入小节（提纲） |
| `15.7 神经元网络.ipynb` | 19 号 5.3 | 并入小节 |
| `MPLClassifier.ipynb` | 19 号 5.4 | 并入小节 |
| `01 线性规划.ipynb` | 31 号 4.1 | 新建篇 |
| `02 整数规划.ipynb` | 32 号 4.1 | 新建篇 |
| `16 目标规划.ipynb` | 32 号 4.2 | 新建篇（提纲） |
| `03 非线性规划.ipynb` | 33 号 4.1 | 新建篇 |
| `05 插值与拟合.ipynb` | 34 号 4.1 | 新建篇 |
| `15.6 插值与拟合.ipynb` | 34 号 4.2 | 新建篇 |
| `07 数理统计.ipynb` | 35 号 4.1 | 新建篇 |
| `09 支持向量机.ipynb` | 36 号 4.1 | 新建篇 |
| `10.5 典型相关分析.ipynb` | 37 号 4.1 | 新建篇（提纲） |
| `10.7 多维标度法.ipynb` | 37 号 4.2 | 新建篇 |
| `11 偏最小二乘回归分析.ipynb` | 38 号 4.1 | 新建篇 |
| `12.1 模拟退火算法.ipynb` | 39 号 4.1 | 新建篇 |
| `12.2 遗传算法.ipynb` | 39 号 4.2 | 新建篇 |
| `14.3 数据包络分析.ipynb` | 40 号 4.1 | 新建篇 |
| `14.5 主成分分析法.ipynb` | 40 号 4.2 | 新建篇 |
| `14.6 秩和比综合评价法.ipynb` | 40 号 4.3 | 新建篇 |
| `15.1 微分方程模型.ipynb` | 41 号 4.1 | 新建篇 |
| `15.4 马尔可夫预测.ipynb` | 42 号 4.1 | 新建篇 |
| `GMM.ipynb` | 43 号 4.1 | 新建篇 |
| `高斯过程回归.ipynb` | 43 号 4.2 | 新建篇 |
| `CS299_MDP.ipynb` | 43 号 4.3 | 新建篇 |

### 数据文件

10 个 `.txt` 已迁入 `data/textbook/`，路径与引用方见 [`data/README.md`](data/README.md#教材数据textbook)。

### 修改说明

融合时对上游内容做了以下最小改动：

1. 数据路径改写为 `../data/textbook/文件名`（仅真实读取的输入；运行时写出的 `遗传算法初步结果.txt` 保持原样）。
2. 清空代码单元的输出与执行计数，避免把上游运行结果当作本仓库结果。
3. 标题层级下移（`##` → `####`，`###` → `#####`），以适配目标 notebook 的 `4.x` / `5.x` 小节。
4. 去掉原文件的一级标题，其余正文与代码保持原样。
5. 31 号补充了一个 `linprog` 标准形算例；43 号把误放在代码单元的博客链接改为 Markdown。

迁移脚本见 [`scripts/merge_textbook.py`](scripts/merge_textbook.py)，可复核逐篇映射。

## MIT 许可全文

```text
MIT License

Copyright (c) 2020 Zhanghan Wang

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 其他第三方资料

`docs/` 中的教材 PDF、`ppts/` 中的课程课件、`manual/` 中的配套代码与旧课件，版权归原作者/出版方所有，仅作学习参考，**不随本仓库的 MIT 授权发布**；如需再分发请自行取得授权。
