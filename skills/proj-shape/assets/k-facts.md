# 承重事实（K）与语气二分 — 操作细则

> `INV-05` / `ORD-53` 的完整说明。SKILL.md 只留摘要，细则在此。
> **出处（借鉴，非自创）**：需求工程的 **indicative / optative** 二分与公式 `S ∧ K ⊢ R`——Zave & Jackson, [Four Dark Corners of Requirements Engineering](https://doi.org/10.1145/237432.237434)（TOSEM 1997）；[The World and the Machine](https://doi.org/10.1145/225014.225041)（ICSE'95）；决策论侧对应 Savage 把 belief 与 desire 分离（[SEP Decision Theory](https://plato.stanford.edu/entries/decision-theory/)）。落地讨论见 `docs/discuss/34-认知同步-断言与偏好二分.md`。

## 两类陈述，处置路径完全不同且不可互换

| | **indicative（断言）** | **optative（偏好）** |
|---|---|---|
| 说的是 | 世界是怎样的 | 我们要什么 |
| 有无真值 | 有，可证伪 | 无，只有代价与后果 |
| 验证方式 | **验证为真**（查证 + 出处） | **验证为被认可**（人拍板） |
| 谁说的重要吗 | **不重要**——用户说的断言不比 AI 说的更权威 | **只有人说的算**——AI 无权替人选 |
| 载体 | `DECISIONS.md` §承重事实（K）+ §待验证尝试（EXP = 未验证的 K）| `DECISIONS.md` §原则性不变量 + §普通决定 |

这条区分同时给出了「AI 什么时候该说话」的判据：**对断言有义务发言，对偏好只能陈述代价**。盲从与过度质疑不是一根滑杆的两端，而是没做这个区分之后的两种崩溃形态。

## INV-05 的实际操作方式：位置定语气，不逐句判定

作者本人**否决**了逐句内容判定：

> "A better approach is to **avoid grammatical distinctions of mood within a single description**, and to indicate the mood of a description **by its place in the whole development structure**."
> — [The World and the Machine](https://doi.org/10.1145/225014.225041)

理由之一是 **optative 部署后会变成 indicative**（"The domain properties that are optative when the software is under development become indicative when the software is deployed … turns our wishes into facts"），逐句判定会要求届时重写描述本身。

所以本 skill **不要求分析每句话的语气**，只要求一件事：

> **承重陈述必须落进一个容器；禁止停留在无容器的散文里。**
> 承重判据 = **它出现在某条 INV/ORD/EXP 的论证前提里**（若为假 → 该条决定失去支撑）。

## 反向驱动（不要从事实侧问「登记全了吗」）

从事实侧问「该登记的都登记了吗」**不可判定且自指**——判断一条事实是否承重，要先知道它支撑哪条决定，而支撑关系恰恰是这张表才记录的东西。

正确方向是把域取为**已落盘决定集合**（有限可枚举）：在**每条新增/修订决定**的轮次文档「本轮决定」节写明 `前提(K)`，可显式 `none`；承重的那些登记进 `DECISIONS.md` §承重事实（K）并回填 `FACT-xx`。

**向前生效，历史条目不回填**（同既有的量化向前生效手法，零回溯成本）。

## 字段规则

| 字段 | 规则 |
|------|------|
| `ID` | `FACT-\d+`，不重用已废止编号 |
| `断言` | 一句可证伪的陈述。**不是**「某某很重要」这类无真值表述 |
| `证据` | `已查证` 行必须是可打开的链接。**宁可标 `待查证·阻塞` 也不要贴一个凑数的链接** |
| `查证日期` | `YYYY-MM-DD`。**随查随登**——批量补录会被 EXP-19 的中位差信号抓到 |
| `supports` | 指向它撑着的 INV/ORD/EXP。**为空 = 不承重 → 不该进本表**，留在轮次文档「已查证事实」节 |
| `接地依据` | **三值**：`世界固有` / `项目已交付` / `外部系统`。记「凭什么它**现在**是事实」——这决定**什么事件**会让它失效。只记查证日期不够，日期不告诉你失效条件 |
| `状态` | **三态**：`已查证` / `待查证·阻塞` / `不敏感`。三态而非两态是硬要求 |
| `复查触发` | 写**外部可判定的条件**（「启用 X 前」「证据早于 N 个月」），**不要写**「当我觉得可疑时」——新颖区的主观信号是反向的（[Metcalfe 1986](https://doi.org/10.1037/0278-7393.12.4.623)：「快想通了」预示错误）|

### 为什么状态必须是三态

Parnas 的原文分了三类缺失，且要求结构可分：

> "it is important to distinguish: • I don't know, but must find out • I don't know, and the case will not arise • I don't care"
> "Design can begin with incomplete knowledge, **if we know what it is that we don't know**."
> — [A Rational Design Process: How and Why to Fake It](https://www.cs.tufts.edu/comp/40-2011f/readings/fake-it.pdf)

**本仓库的实例**：一条外部 runtime 事实过期后六周无人发现，正因为「我没查」与「我不在乎」在结构上同形——没有任何字段能区分「这条待办」和「这条已不适用」。

## 状态传播

某条 FACT 被推翻 → `supports` 列引用它的决定**即刻置「待复议」**，按正常轮次流程回写，**不得静默沿用**。

没有状态传播，这张表就只是坟场：事实更新了，压在它上面的决定却不知道。

## 机检 C8（`scripts/validate_skills.py`）

纯结构、零语义、零误报，落在「只自动化低误报检查」的既有边界内：

- ID 格式与去重
- `已查证` 行须有链接证据 + `YYYY-MM-DD` 日期
- `待查证·阻塞` 行须有非空 `复查触发`
- `supports` 非空，且其中的 INV/ORD/EXP 编号须存在于 `DECISIONS.md`
- `接地依据` / `状态` 两列取值须在枚举内

**「这条断言是不是真的」永远不进机检**——那是语义判断，留给人。机器只检查槽位是否良构（对应 Parnas：「Checking these properties shows completeness and feasibility, **not correctness**」）。

## 动因：两起同形事故

1. 一条外部 runtime 事实过期，**六周无人发现**，其间一条 ORD 一直悬在上面。
2. 用户在另一项目中把「code graph 由 LLM 生成」当背景事实使用（业界实为 tree-sitter 抽 AST 的纯程序步骤），据此做架构决策，走了冤枉路。**那条断言从未落进任何容器**，因此既没人要它带 URL，也没进任何复查视野。

两起都不是「查证能力不足」，是**陈述没有 home**。

## 已知未闭合风险（诚实披露）

「表会被填成终态、然后没人复查」这条反对**在 round 34 未被驳倒**——开源 ADR 实测约 **63% 创建时状态即 accepted**（[DOI 10.1109/ACCESS.2023.3287654](https://doi.org/10.1109/ACCESS.2023.3287654)），且 Wikipedia 在最强可核查规范加百万编辑者下引用覆盖率天花板仍只有六成。

故本机制**带观测与退出条件**：

| EXP | 观测什么 | 中止 → 降级路径 B |
|-----|----------|------------------|
| **EXP-19** | 6 个月内 FACT 条目数 / `前提(K): none` 占比 / 入表与查证日期的中位差 | ≤12 条、或 `none` >50%、或普遍批量补录 → **撤销 K 表与 C8**，退回一句纪律：*有人把「业界都是这么做的」当背景事实说出来时，当场要一个 URL* |
| **EXP-20** | 闸门处人手写「这条决定依赖的因果链是___」是否非同义反复、是否引出新前提 | 连续 2 次写不出 → 改为 AI 出题、人只答「确认/未确认/不敏感」的闸门问卷 |
