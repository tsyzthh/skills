---
name: proj-survey
description: >-
  Brownfield 历史项目接管的「逆向勘测」skill：AI 自动读既有系统（按 测试>代码>git>docs>口述
  优先级采集真相源），产出三分离（事实/推理/待验证）现状基线，做意图(to-be)重建评估 →
  GATE-S 人审批分支：intent 可信重建 → 交 proj-plan 规划（brownfield 入口 + WBS 三态）；
  intent 不可重建 → 完整性审计报告（findings + 置信度，不作"无缺失/无 bug"保证），可回流
  proj-shape 补 intent。是 proj-* 体系的接管入口（与正向 proj-shape 并列）。Use when 接管
  历史项目 / 遗留代码 / legacy / brownfield / 现状基线 / 逆向盘点 / 完整性评审 / takeover。
compatibility: >-
  目标 = 任意已有代码/文档的项目根。产出现状基线（默认 docs/survey/）。可衔接 proj-plan
  （brownfield 入口，见 proj-plan §Brownfield 接管入口 · ORD-26）或产出终端审计报告。不写新 INV/ORD（归 proj-shape）；不执行、不规划。
---

<!--
input: 既有项目根（代码 + 文档 + git）
output: docs/survey/（现状基线 + 分支产出：handoff 或 审计报告）
pos: brownfield 接管入口；与正向 proj-shape 并列；上游无、下游 = proj-plan 或 proj-shape（回流）

修改本文件后，请同步更新根 README.md 的 skill 索引表与 proj-survey 详细节。
来源：DECISIONS.md ORD-23~26（轮次 09 立项）+ EXP-05 passed（baseline 流程固化）+ EXP-06（分支判据待验证）；起草见 docs/discuss/10-proj-survey起草.md。
-->

# 现状勘测（proj-survey）

读一个**已经存在的系统**，自动产出**现状基线**，判定能否直接规划、还是只能审计——是 proj-* 体系的 **brownfield 接管入口**。

**勘测归本 skill；讨论 / 规划 / 执行不归本 skill**（补 intent → `proj-shape`；规划未完成工作 → `proj-plan`；执行 → `proj-run`）。

## 设计 vision

正向流水线从「人的想法」出发；本 skill 从「既有系统」出发，是**第二个入口**：

```text
正向(新项目):  proj-experts → proj-shape → proj-plan → proj-run
接管(历史项目): proj-survey → ┬─[intent 可信]→ proj-plan → proj-run
                              └─[intent 不可信]→ 审计报告(终端)
                                                 └→(可选)回 proj-shape 与人补 intent → proj-plan
```

**角色分工**（对齐体系 `INV-01` 精神 + PMBOK 8「AI augment, human accountable」）：

| 谁 | 职责 |
|----|------|
| **AI** | 全自动采集真相源、生成现状基线、给出分支建议；**不需要人工整理** |
| **人** | 在 **GATE-S** 审批分支判定（走 plan / 走 audit）；**只读** baseline 摘要（≤5 项），不读全量 |

> **「自动」= 生成全自动 + 人仅在分支处拍板**（ORD-26）。人不整理，只审批。

## 立场声明（借鉴 / 自创）

> 让用户与 agent 逐条判断「这是借鉴 / 本 skill 自创」。未声明的术语不应被当作行业标准。

### 借鉴

| 来源 | 用于 |
|------|------|
| **proj-shape 三分离**（已查证事实 / 推理 / 待验证假设）| 现状基线每条 finding 的认知学标注（ORD-24）|
| **proj-plan human-read-manifest（≤5）精神** | GATE-S 人只读 baseline 摘要，不读全量 |
| **Brownfield / legacy takeover 通念** | 「读既有系统重建 as-is」的一般工程实践（本 skill 不主张某一特定标准）|

### 本 skill 自创术语（**非**行业标准）

| 术语 | 含义 | 出处 |
|------|------|------|
| **现状基线（as-is baseline）** | 三分离标注的既有系统快照（已完成范围 / 未完成 / 质量观察 / 待验证）| `09-…md` ORD-23 |
| **意图重建评估** | 从真相源重建 to-be 的可信度评估，决定分支 | `09-…md` ORD-24；判据待 EXP-06 |
| **GATE-S** | 分支判定的人工审批节点（编号沿用 proj-plan GATE-N 体系）| `09-…md` ORD-26 |
| **真相源优先级** | 测试 > 代码 > git/issue > docs > 用户口述 | `09-…md` ORD-24 |

## 与上下游的职责边界

| | **proj-survey（本 skill）** | proj-shape | proj-plan | proj-run |
|---|------------------------------|-----------|-----------|----------|
| 起点 | **既有系统** | 人的模糊想法 | DECISIONS | plan.md |
| 问题 | 现在是什么？已完成什么？能否规划？ | 想清楚做什么 | 怎么分解规划 | 谁/怎么执行 |
| 产出 | `docs/survey/`（基线 + handoff 或 审计报告）| `docs/discuss/` | `docs/pmo/` | `acceptance.md` |
| 边界 | **不写**新 INV/ORD；**不**规划；**不**执行 | — | — | — |

## 真相源优先级（ORD-24）

采集既有系统信息时按**可信度降序**，冲突时高优先级胜：

1. **测试 / 可执行校验**（实跑结果 = 最强事实，如 `pytest`、lint、CI）
2. **代码结构**（实际实现、依赖、入口）
3. **git log / issue / PR**（演进与未决项）
4. **docs / README / CHANGELOG**（声称，常陈旧 → 多落「待验证」）
5. **用户口述**（补充，非可机验）

> **关键纪律**：文档说的不等于代码做的。docs 单独声称、代码未证实 → 标 **[待验证]**，不进 **[事实]**。

## 三分离标注（ORD-24）

| 档 | 定义 | 进入条件 |
|----|------|----------|
| **[事实]** | 直接读出 / 实跑可证 | 有可复现依据（命令输出、文件内容、git）|
| **[推理]** | 从结构/命名/状态推断 | 必附依据；不得当事实 |
| **[待验证]** | docs 声称但未机验 / 需运行时 | 注明为何未验 |

## 不可违背

| ID | 要点 |
|----|------|
| S-1 | **baseline 自动生成**，但**分支判定必经 GATE-S 人审批**（对齐 `INV-01`：人=关键决策）|
| S-2 | 审计分支产出 = **findings + 置信度**；**禁止**断言「无缺失 / 无 bug」（无 intent 无法证完整，无 oracle 无法证正确）|
| S-3 | **不写新 INV/ORD**（决定归 proj-shape）；**不**做规划（归 proj-plan）；**不**执行 |
| S-4 | [事实] 档须可复现取证；docs 单方声称入 [待验证] |

## 工作流

### 0. 前置

- 确认目标项目根 + `docs/survey/` 可写。
- 大型 repo：先 §6 分层策略框定范围。

### 1. 真相源采集（按 ORD-24 优先级）

- 先取 **repo map**：目录结构、入口、依赖清单、git 概况（log/status/分支/文件数）。
- 识别测试/校验入口与 docs 清单。

### 2. 实跑测试 / 校验（最高优先级事实）

- 能跑就跑（test / lint / build / 项目自带校验脚本），记录退出码与输出 → 进 [事实]。
- 跑不动 → 标 [待验证] 并注明原因（缺环境/超范围）。

### 3. 生成现状基线（三分离）

按 [baseline-template](assets/baseline-template.md) 写 `docs/survey/<日期>-baseline.md`：
- 一句话现状 · 已完成范围 · 未完成/进行中 · 质量/一致性观察 · 待验证
- 每条带档位标注 + 依据；**[事实] 条目编号**（供误报率核对）。

### 4. 意图(to-be)重建评估 → 分支判定 ⚠️ EXP-06 难端待验

按 §「分支判据」4 维打分（0/1/2）+ 组合规则 R1/R2/R3 → 给**分支建议**（可 plan / 仅 audit / 人审）+ 理由。

**意图重建走碰撞，不走「谁更可信」（ORD-56）**：

| 步 | 谁 | 做什么 |
|----|----|--------|
| 1 | **AI** | **保持** §真相源优先级（测试 > 代码 > git > docs）推出**候选意图**结论 |
| 2 | **人** | **独立**校对——先给自己的版本再看 AI 的，比先读 AI 再点头更能发现问题 |
| 3 | 双方 | **不一致处 = 讨论点 / 修改点**，不预设谁对 |

**为什么不是「把优先级倒过来」**：真相源优先级排的是**事实**的可信度，而「当初想做成什么」不是事实、是**意图**（optative）——它没有真相源，只有**认可**。从代码与测试恢复出来的是**实现**，无法区分「意图本是 X 但实现有 bug」和「意图本就是 X′」。所以顺序**保留**给「产出候选」，**认可**由人的校对承担；不一致恰恰是「bug 还是原意」这个分岔的显影剂。

**与 GATE-S 的关系**：不新增流程——这是给 GATE-S 加一个具体的比对动作。重建结论只能标 `待认可` / `已认可`，**不得标 `已查证`**。

### 5. GATE-S（人审批）

- 人**只读** baseline 摘要（≤5 项）+ 分支建议 → 确认走向。
- 不确定 → 默认走**更保守的审计分支** + 人确认（EXP-06 中止路径 B）。

### 6. 分支产出

| 分支 | 条件 | 产出 | 下游 |
|------|------|------|------|
| **A · 可 plan** | intent 可信重建 | [survey-handoff](assets/survey-handoff-template.md)：已完成范围（既成约束）+ 未完成工作（WBS 三态种子）| → `proj-plan`（brownfield 入口）|
| **B · 仅 audit** | intent 不可重建 | [audit-report](assets/audit-report-template.md)：内部一致性 findings + 置信度（**不作保证**）| 终端；可选回 `proj-shape` 补 intent |

> **存量量化适用规则（ORD-45）**：接管/存量项目——行为与规范类机制（ORD-42/44 + 维度表可选段）**自动生效**；数据类（ORD-41 挣得记账）**向前生效**（新 phase 自动带 PV 列 / 在飞 phase 可选补列 / 已结束 phase 不回填）；baseline 后首个决策点（GATE-S / GATE-0）可选跑一次维度表 pass 探测遗留未决/冲突。量化是仪表不是档案。

## 分支判据（EXP-06 · 算子化 · 仍 provisional）

> **provisional**：4 维由 EXP-05 dogfood（易端）初定；EXP-06 已将其**算子化**并验证「可操作 + 可复现 + 区分力」（易端→plan 复现 EXP-05、合成难例→audit 正确分开），但**难端「与独立人判一致」仍待真实 repo 压测**。用前仍以 GATE-S 兜底。详见 `docs/pmo/proj-06-spike/`。

意图可重建度按 4 维打分（**0=低 / 1=中 / 2=高**），可观测信号：

| 维度 | 可观测信号（D1/D2 可机判 · D3/D4 半机判）| 0（低）| 2（高）|
|------|------|--------|--------|
| **D1 来源丰富度** | 命中源种类数（测试·代码·doc）| 0–1 种 | ≥3 种 |
| **D2 来源新鲜度** | README 声称入口/命令在代码里是否存在 + git 活跃 | 入口缺失/漂移严重 | 存在且一致 |
| **D3 缺口可识别度** | TODO/issue/缺失 stub 能否定位 | 说不清差什么 | 明确可定位 |
| **D4 矛盾程度**（高=矛盾少）| 测试↔README↔代码方向是否冲突 | 互相矛盾 | 无方向冲突 |

**组合规则**（total = D1+D2+D3+D4，0–8）：

- **R1** 任一维 = 0 → **AUDIT**（保「任一低→audit」纪律）
- **R2** 全维 ≥1 且 total ≥ 6 → **PLAN**
- **R3** 其余 → **GATE-S 人审，默认 AUDIT**（保守兜底 · 中止路径 B）

> 阈值 6/8 为可调超参，待真实难例校准（EXP-06）。算子只产**建议**，分支仍必经 GATE-S（S-1）。

## 大型 repo 可扩展性（EXP-05 降级路径 B）

- 默认**分层读取**：repo map → 依赖图 → 按需深入热点目录，不一次性通读。
- 超出可读范围 → **请人指认重点目录/模块**，AI 做局部基线 + 标注「未覆盖范围」。

## 失败模式

- 把 docs 声称当 [事实]（违反 S-4）
- 审计分支给「无 bug」结论（违反 S-2）
- 跳过 GATE-S 直接分支（违反 S-1）
- WBS 把已完成的当新工作（handoff 未标三态）
- 大 repo 硬通读导致漏读/超长
- 在本 skill 内写新 ORD 或直接规划/执行（违反 S-3）

## 触发词

proj-survey · 现状勘测 · 现状基线 · 历史项目接管 · 接管 · 遗留 · legacy · brownfield · 逆向盘点 · 完整性评审 · 审计报告 · as-is · 意图重建 · takeover

## 不触发本 skill

- 新项目从想法开始 → `proj-shape`
- 已有 DECISIONS 且就绪 → 直接 `proj-plan`
- 只要一次性改代码 → 直接执行

## 模板索引

| 文档 | 模板 |
|------|------|
| 现状基线 | [assets/baseline-template.md](assets/baseline-template.md) |
| 审计报告（分支 B）| [assets/audit-report-template.md](assets/audit-report-template.md) |
| 规划交接（分支 A → proj-plan）| [assets/survey-handoff-template.md](assets/survey-handoff-template.md) |
