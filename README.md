# Agent Skills：想法 → 收敛 → 规划 → 执行（proj-* 流水线）

个人沉淀的 [Agent Skills](https://agentskills.io) 集合，可在 Cursor、Claude Code 等支持 Skills 的 Agent 中使用。

本仓库包含 **1 个总入口 orchestrator `proj`** + **4 个正向 skill**（对应 PMP 4 大 Process Group，覆盖从模糊想法到执行落地的完整链路）**+ 1 个 brownfield 接管入口 `proj-survey`**（共 6 skill）：

| Skill | 中文名 | PMP 对应 | 一句话 | 主要产出 |
|-------|--------|---------|--------|----------|
| [proj](./skills/proj/) | 总入口 | 流水线之上（orchestrator）| 用户唯一入口：薄 Supervisor + 有界规划-执行-验证 loop + GATE 编排，按序调下面 5 个专家；**不重做** host 路由 | 不直接产 artifact（编排各专家产出）|
| [proj-experts](./skills/proj-experts/) | 专家研判 | Initiating · Business Case | 先查证，再模拟最懂的人怎么说（含选用理由 + 三档真实性标签）| 对话中的专家视角分析 |
| [proj-shape](./skills/proj-shape/) | 想法收敛 | Initiating · 多轮决议 | 以实现为导向的多轮讨论留痕 + 决定汇总 + 可验证尝试 | `docs/discuss/` |
| [proj-plan](./skills/proj-plan/) | 项目蓝图 | Initiate(charter) + Planning + 规划侧 M&C + Closing | 承接决定，做 PMP 分层规划 + GATE + analyze + dispatch manifest 承诺字段 | `docs/pmo/` |
| [proj-run](./skills/proj-run/) | 执行调度 | Executing | 承接 plan + dispatch manifest，调度 sub-agent + validation gate + escalate | `phase-NN/acceptance.md` + `.cursor/agents/*.md` |
| [proj-survey](./skills/proj-survey/) | 现状勘测 | 接管入口（brownfield）| 读既有系统 → 三分离现状基线 → GATE-S 分支：可 plan → proj-plan / 仅 audit → 审计报告 | `docs/survey/` |

> **总入口**：用户通常只跟 **`proj`** 交互，由它编排下面 5 个专家并在 GATE 处交人；也可直接调用某个专家（如只要专家分析 → `proj-experts`）。
>
> **双入口**：新项目走 `proj-shape → proj-plan → proj-run`；**接管历史项目走 `proj-survey`**，它判定能否直接规划（→ proj-plan）还是只能做完整性审计。

```
模糊想法
    │
    ▼
┌─────────────────┐     ┌──────────────────────┐
│  proj-shape     │────▶│  docs/discuss/       │
│  （想法收敛）    │     │  DECISIONS.md + 轮次  │
└────────┬────────┘     └──────────────────────┘
         │ 分析层默认配合
         ▼
┌─────────────────┐
│  proj-experts   │  查证 + 专家视角 + 三档真实性标签
│  （专家研判）    │  （原话 / 已公开立场 / 模拟推理）
└─────────────────┘
         │ ready-for-implementation
         ▼
┌─────────────────┐     ┌──────────────────────┐
│  proj-plan      │────▶│  docs/pmo/           │
│  （项目蓝图）    │     │  WBS + 阶段 + GATE   │
└────────┬────────┘     │  + dispatch manifest │
         │              └──────────────────────┘
         │ GATE-3 通过 · phase-NN/plan.md（含 manifest）
         ▼
┌─────────────────┐     ┌──────────────────────┐
│  proj-run       │────▶│  acceptance.md       │
│  （执行调度）    │     │  + sub-agent 产出    │
└─────────────────┘     │  + .cursor/agents/   │
                        └──────────────────────┘
```

---

## 安装

将需要的 skill 目录链接或复制到 Agent 的 skills 路径：

```bash
# Cursor 示例（在本仓库根目录执行）
ln -s "$(pwd)/skills/proj"         ~/.cursor/skills/proj
ln -s "$(pwd)/skills/proj-experts" ~/.cursor/skills/proj-experts
ln -s "$(pwd)/skills/proj-shape"   ~/.cursor/skills/proj-shape
ln -s "$(pwd)/skills/proj-plan"    ~/.cursor/skills/proj-plan
ln -s "$(pwd)/skills/proj-run"     ~/.cursor/skills/proj-run
```

也可在对话中 `@` 引用仓库内的 `SKILL.md`，或直接说出触发词（见各 skill 下方）。

---

## proj（总入口 · orchestrator）

**做什么**：proj-* 流水线的**用户唯一入口**。用户描述问题，由 `proj` 作**薄 Supervisor + 有界 plan-execute-verify loop + facade**，按序编排下面 5 个专家 skill 跑「想法 → 收敛 → 规划 → 执行 → 验证」闭环，并在 GATE 处停下交人。

**关键纪律（ORD-30）**：`proj` **不重做** host 的 model-invocation 路由（host 已按 description 做单次 skill 选择）；它的增量 = host 给不了的**跨 skill 有状态序列 + GATE + loop**。

**有界 loop（ORD-31）**：`STATE → CLASSIFY → PLAN → EXECUTE → VERIFY → GATE? → RE-ROUTE → MEMORY`；默认档 = phase 内自迭代、**到 GATE 必停交人**（autonomy slider，高自主档需用户显式授权）；circuit breaker 兜底。

**设计立场（ORD-34 · Ashby）**：自动臂**有界多样性 by design**（circuit breaker 塌缩失败 / GATE 在分岔停 / budget 限重试）；**必要多样性由人在 GATE/分岔供给**——「有界」是显式设计选择而非能力缺陷，与 Supervised-AI 一致。

**调用对象（固定专家集 · Supervisor 模式）**：`proj-experts` / `proj-shape` / `proj-plan` / `proj-survey` / `proj-run`。

**立场**：Supervisor/Routing 与「先求最简」借鉴 [Anthropic Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)；有界 loop 借鉴 [Addy Osmani Loop Engineering](https://addyo.substack.com/p/loop-engineering)；autonomy slider 借鉴 [Karpathy](https://www.latent.space/p/s3)；本地化组合为本 skill 自创（DECISIONS ORD-29/30/31；EXP-07 passed）。

**何时不用**：只要某一专家（只做专家分析 / 只摸现状）→ 直接调该专家；一次性改 1 文件 → 直接执行。

**触发词示例**：proj · 总入口 · 编排 · orchestrate · 端到端 · 从想法到落地 · 帮我推进这个项目 · 不知道下一步 · loop engineering · 闭环

**详细说明**：[skills/proj/SKILL.md](./skills/proj/SKILL.md)

---

## proj-experts（专家研判 · Initiating · Business Case）

**做什么**：Grounded 模拟器思维——先查证事实，再模拟「谁最懂这个问题的人」会怎么说；输出按 **三档真实性标签**（【原话】/【已公开立场】/【模拟推理】）分级，**绝不**把模拟推理伪装成原话。

**适用场景**：

- 架构 / 技术选型 / 策略决策，且涉及具体产品、项目或命名概念
- 想听「顶级专家会怎么看」，或指定某人视角（如「以 Karpathy 视角分析」）
- 问题没有工业界 playbook，需要基于专家已记录的原则做发散

**核心流程**：

1. 轻量框定：列出 TA 会先确认的 3–5 个事实问题
2. 定向 WebSearch（官方 docs / repo / issue / RFC）
3. 识别或锁定专家（用户指定优先）
4. 输出：每位 TA 先写 **选用理由**，再用三档标签产出观点

**引用真实性核验（ORD-48 · 经 ORD-49 修订）**：带 **arXiv ID / DOI** 的引用写入前须**反查 ID ↔ 标题+日期**，不通过则不得写入。机检**只判「ID 是否解析到真实文献」**（零误报），「是不是你想引的那篇」由人看返回标题判定（自动关键词比对实测误报 30%，不用）；语义级「该文献是否真支持论断」留人 / GATE。**防误杀**：单条失败须重试；**整体失败率 >50% 先判客户端/环境故障**，换客户端复核后才下结论（实测 urllib 曾 34/35 系统性失败）。动因：搜索层会返回带完整统计数字的**伪造文献**（见 `docs/discuss/30-…md` 实截获样本）。

**去同质化（ORD-49）**：依据 EXP-15 实测（跨视角显式反驳 **0 → 4**）。① 输出骨架**松绑为缺省建议**，各视角可按该专家自然的论证形状改写，唯一硬要求 = 选用理由 + 三档标签；② `#### 分歧` 节与「收敛」**并列必填**（多专家时 · ≥2 行 · 不得调和 · 点名双方）；③ 争议轮指派**红队**并走 **commit-then-reveal 两步**（先在不见他人时把立场写死冻结，再揭示反驳、必须点名反对 ≥1 条），红队**豁免**「建设性优于否定」；④ 多专家争议轮**各 TA 独立检索**（强制 · 成本约 3x · 防止「多视角」退化成同一批证据的不同切片）。

**触发词示例**：最强大脑 · 谁最懂这个 · 以 X 视角 · 模拟 Y · 指定专家 · 没有现成方案 · proj-experts

**单独使用**：可直接用于纯分析问答，不必开启讨论文档。

**详细说明**：[skills/proj-experts/SKILL.md](./skills/proj-experts/SKILL.md)

---

## proj-shape（想法收敛 · Initiating · 多轮决议）

**做什么**：以实现为终点的多轮想法讨论框架。把模糊想法磨清楚，留痕到 `docs/discuss/`，汇总已确定决定到 `DECISIONS.md`；对前沿 / 无现成解法的问题，产出可验证尝试（`EXP-xx`）及继续 / 中止标准。

**不负责**：MVP 细则、里程碑排期、写代码（这些交给 proj-plan 或执行阶段）。

**三段式入口**（首次使用本 skill）：

| 阶段 | 产出 | 主导 | 退出 → 下一阶段 |
|------|------|------|----------------|
| **0. BRAINSTORM** | `docs/discuss/BRAINSTORM.md` | 用户低负担自留草稿（5 个开放问句 + 自由叙述区） | 答 3/5 问句 + 自由叙述非空 |
| **1. 苏格拉底澄清轮** | `01-苏格拉底澄清.md`（`discussion_method: socratic-grounded`）| AI 提问、用户答；六问类别 inline 在 SKILL.md | 提炼出 ≥1 条可被外部专家评判的命题 |
| **2+. 专家讨论轮** | `02-….md`、`03-….md`（默认 `discussion_method: proj-experts`）| AI 调用方法 skill 攻防 | 满足「讨论就绪」硬条件 |

苏格拉底**可跳过**——用户在 BRAINSTORM「给 AI 的话」节明示「想法够清楚」，则 round 01 直接走 proj-experts；BRAINSTORM 进入 round 02 后冻结。

**讨论线 WIP 与中断留痕（ORD-52）**：`pipeline-state.threads` 中 `state ∈ {open, blocked}` 的条数**上限 3**（**C7 机检**）；`paused`/`closed` 不计入——它们是「明确放下」的决定，所以开第 4 条线会**强制你回答「那前面哪条放下」**。例外条款 = 允许中断但**必须留痕**（显式置 `paused` + 填 `blocked_on` ≤30 字符），**禁止静默搁置**。validator 每次运行打印各线**停滞轮数**（派生不存储）——实测曾有一条线静默停滞 15 轮而系统内无任何记录。

**承重事实（K）与语气二分（INV-05 / ORD-53）**：把进入系统的陈述按需求工程的 **indicative / optative** 二分（Jackson & Zave, [Four Dark Corners](https://doi.org/10.1145/237432.237434)，公式 `S ∧ K ⊢ R`）分开对待——**断言**关于世界、可证伪、**求真**（谁说的不重要，用户说的断言不比 AI 说的更权威）；**偏好**关于选择、无真值、**求认可**（只有人说的算，AI 无权替人选）。此前 `DECISIONS.md` 存了 R（INV/ORD）与未验证的 K（EXP），**唯独没有已验证 K 的载体**，导致一条外部事实过期六周无人发现。现新增 §承重事实（K）表并**吸收原「外部前提登记」表**（净减一条独立纪律）。关键设计：**语气由描述所处位置决定、不由句子内容逐句判定**（作者原文否决逐句判定，因为部署会把 optative 变成 indicative）；**反向驱动**——每条新增/修订决定写 `前提(K)`（可显式 `none`），承重的才登记，向前生效不回填；`状态` **三态**（已查证 / 待查证·阻塞 / 不敏感，因为「我没查」与「我不在乎」必须结构可分）+ `接地依据` **三值**（世界固有 / 项目已交付 / 外部系统，决定什么事件会让它失效）；机检 **C8** 纯结构零语义。**诚实披露**：「表会被填成终态、无人复查」这条反对未被驳倒（开源 ADR 实测约 63% 创建即 accepted · 出处见 `FACT-08`）→ 带 **EXP-19/EXP-20** 观测与明确撤表降级路径。

**事实纪律 · 两道闸（ORD-54）**：立场是「人不专业、不稳定，AI 会幻觉，**事实是降低这两种弱点的共同基础——基础不稳，上面建什么都白搭**」。先立**全局约定：事实陈述不带出处 = 未查证**（否则只标一部分会让没标的被读成已核实——implied truth effect 实测未标假信息转发意愿反升 29.8%→36.2%）。**第一道 · 提出即查证（严 · 不论来源）**：以事实语气说出或写下一条可证伪命题**之前必须先查证**，「我没查」**不是合法出口**；触发判据是作者侧的「我要不要把它当事实给出去」，**不筛承重**（说出口那刻不知它将被怎么用）；**唯一的放松在结论**——可为 `无法判定`（**已经查了**但没找到），但那是防死循环的兜底、须留痕「查了什么」、落 `待查证·阻塞`、**不构成放行**，只把球交给人。**来源对称的正确形态（r37 纠错）**：用户说的断言同样受这道闸约束，触发点是「**AI 采信 / 记录 / 沿用之前**」，而**查证义务永远在 AI 身上**——问用户要出处才是审讯，AI 自己去查不是；查不出才落 `无法判定` 并问人。**第二道 · 使用时**：承重且无 home → **不许往下走**，先要出处或由人标 `不敏感`。**第三层 · 复核**：`接地依据 = 外部系统` 的按复查触发核时效。**来源对称**：不因来源豁免。**执行请求不豁免**。为什么拦在提出而非使用——**未查证断言被记录下来就已进入人的认知，那是一次 AI 观测不到的使用**，而事后纠正只能部分回收且时间差越大越无效（32 研究元分析）。退化观测 = `EXP-21`（盖章放行 / 卡死工作 / 误拦 / `无法判定` 占比 >20%）。同批还有 **designation**（INV-05 修订）：承重陈述引入的新术语须指向可观察物——真实事故里的「code graph」正是因为没有指称（AST 符号引用边？语义摘要图？）才无从判真假。

**四象限保持派生视图（ORD-57）**：「人已知/未知 × AI 已知/未知」保留，但**禁止建表 / 常驻文件 / status 列**——它是从 K 表、轮次留痕、INV/ORD、GATE 留痕里**查出来**的，不是维护出来的；「不落盘、零成本」正是它被保留的唯一理由。

**输出侧三层防线（ORD-58）**：提出闸拦「说之前查没查」，拦不住「自己抓不到漏了什么」。含事实断言的输出，正文保持散文，末尾附 **§本轮事实依据**；条目区非空则输出前起 sub-agent，输入必须是**草稿全文 + 条目区**（只给条目审不到漏摘）。轮次「已查证事实」不得裸奔（纪律，无机检）。观测 = `EXP-22`。

**覆盖提问（ORD-50）**：防遗漏机制，**不产生任何 artifact**。AI 只在两个 pause point（**苏格拉底轮之后的下一个工作段开始时** / 就绪评估前）各问一次「把这个想法讲给完全不懂的人听，哪一段你自己讲不下去」，回答按普通散文进当轮文档。第 1 个 pause point **不在澄清轮末尾立刻问**（延迟自评准确度 G=+.90 vs 即时 G=+.38）。**禁止 AI 预生成「技术/商业/营销」式维度大纲**（EXP-15 六视角独立否决：给出类别会收窄探索广度而不减少产出量）；措辞须结构性（「我没在前面看到 X」）非语义性（「X 讨论得不够」）。问法本身待 **EXP-17** 验证，连续 2 次零新增即停用。

**产出目录**（在项目根目录）：

```text
docs/discuss/
├── BRAINSTORM.md         # 用户自留：初始想法草稿（首次使用时自动建空模板）
├── DECISIONS.md          # 已确定决定 + EXP 表 + 讨论状态（优先读此文件）
├── 01-苏格拉底澄清.md     # 默认 round 01：六问提炼候选命题
├── 02-技术选型争议.md
└── ...
```

**与 proj-experts 的分工**：

| 层 | skill | 产出 |
|----|-------|------|
| 分析层（方法可替换）| proj-experts（默认 round 02+）/ socratic-grounded（默认 round 01，inline 六问）/ pre-mortem / ... | 查证、专家视角、三档标签（完整执行）|
| 讨论层（框架）| proj-shape | 轮次文档 + DECISIONS 汇总 + 就绪判断 + BRAINSTORM 入口 |

每轮讨论调用所选方法 skill 做分析，由 proj-shape 重组写入文档；用户可显式切换。

**对 proj-plan 的承诺字段**：当讨论状态变为 `ready-for-implementation` 时，DECISIONS 必须为 proj-plan 准备好 INV/ORD 区分、成功标准、范围边界、EXP 降级路径、来源追溯。

**典型用法**：

```text
用户：我想做一个 XXX，但不确定技术路线，帮我讨论一下
→ Agent 启用 proj-shape，自动建 docs/discuss/BRAINSTORM.md 让用户填
→ 用户填完最低门槛 → round 01 苏格拉底六问追问 → 提炼候选命题
→ round 02+ 调 proj-experts 攻防；同步更新 DECISIONS.md

用户：讨论够了吗？能不能开始做？
→ 对照「讨论就绪」硬条件 + 盲点双问（AI 最没把握 / 用户最大遗漏，单次执行、每条答案落点三选一：决定覆盖/EXP/明示接受），更新 DECISIONS 状态为 ready-for-implementation（须用户确认）
```

**讨论状态**：`exploring` → `deciding` → `ready-for-implementation` / `blocked`

**触发词示例**：想法讨论 · proj-shape · 前沿方案 · 无现成解法 · 可验证尝试 · 讨论够了没 · EXP · DECISIONS · 切换讨论方法 · brainstorm · 苏格拉底澄清 · 三段式入口

**详细说明**：[skills/proj-shape/SKILL.md](./skills/proj-shape/SKILL.md)

---

## proj-plan（项目蓝图 · Initiate + Planning + 规划侧 M&C + Closing）

**做什么**：承接 `docs/discuss/DECISIONS.md`，用 PMP 计划分层 + SDD gate/analyze 纪律生成 `docs/pmo/` 规划产物。AI 维护完整 artifact 集；人类**只读** `human-read-manifest.md`（≤5 项）。

**前置条件**：`DECISIONS.md` 讨论状态为 `ready-for-implementation`，或用户显式授权开工。

**不负责**：写新 INV/ORD（属 proj-shape）、执行代码、启动 sub-agent（执行归 proj-run；本 skill 只在 `phase-NN/plan.md` 末尾写 `## Sub-agent dispatch manifest` 承诺字段）。

**产出目录**（在项目根目录）：

```text
docs/pmo/
├── human-read-manifest.md   # 人类必读（≤5 项）+ GATE 状态
├── charter.md / wbs.md / phase-roadmap.md
├── integration-plan.md / change-log.md
├── artifact-index.md        # AI · SDD truth source
├── phase-01/plan.md         # 细任务仅在此（含 ## Sub-agent dispatch manifest 段）
└── ...
```

**工作流概要**：

| 阶段 | 内容 | 人类确认 |
|------|------|----------|
| Round A · Initiate | 项目上下文、裁剪决策、启动章程草案 | GATE-0 |
| Round B · Plan | 章程定稿、WBS、阶段路线图、整合计划、变更日志、artifact 索引（+ analyze） | GATE-1 → GATE-2 |
| Rolling · 阶段 | 进入某阶段时写 `phase-NN/plan.md`（含 dispatch manifest） + 验收 | GATE-3 |

**模式**：Coach hybrid 裁剪——**T**（精简）或 **F**（全量子计划），由用户在 GATE-0 确认。

**规划原则 · JIT（ORD-27）**：恰好足够、在对的时间规划——细节推迟到 Last Responsible Moment 才展开（行业出处 = PMBOK rolling wave / progressive elaboration + Lean LRM；JIT 编译为借用类比）。边界：可推迟的是*细节深度+可逆决策*，范围/阶段骨架与授权（charter / WBS L1–L2 / phase-roadmap）**故意提前**；推迟≠省略 artifact。与模式 T/F 正交（T/F=广度轴，JIT=时间/深度轴）。

**立场声明**：SKILL.md 含 vision + 借鉴/自创术语标注 + 基准版本声明（PMBOK 6/7/8 + GitHub Spec Kit 机制借鉴 + 学术 Agentic PM）+ Sub-agent dispatch manifest 段（ORD-15 对 proj-run 的承诺字段）。

**案例库 / 跨项目学习闭环（ORD-36）**：proj-* 的慢/外层双环学习反馈——集中库 [`docs/cases/`](./docs/cases/)（PMBOK Lessons Learned Register）。捕获=阶段 Close 时 AI 从本项目 DECISIONS+change-log+review 派生案例草稿+人审；消费=新项目 Round A 查阅相似案例带入 charter。**价值系于闭环消费**（写而不用=头号失败模式）；每案例必填「治理变量检视」（Argyris 双环）。**不新增 skill**；全自动总结/CBR 检索暂不做（YAGNI）。

**与 proj-shape / proj-run 的衔接**：

- 讨论未就绪 → 回 proj-shape
- 阶段验收失败 / EXP failed → 回 proj-shape 修订决定
- 推翻 ORD/INV → change-log + 回 proj-shape
- GATE-3 通过 → 把 `phase-NN/plan.md` 交给 proj-run 执行

**触发词示例**：proj-plan · 项目章程 · WBS · phase-roadmap · integration-plan · change-log · analyze · GATE · tailoring · sub-agent

**在飞工作量控制（ORD-52 · 执行侧）**：WIP 单位 = 同时「进行中」的 phase 数，**默认 1**，写在 `wbs.md` 表头（**写在使用点上**）；中断协议 = 允许插队但被中断项须显式置「暂停」+ `change-log.md` 记一行，**禁止静默搁置**。**证据强度**：依据 Kanban Guide + 用户自述症状，**无本项目实测数据**，故为**纪律级不进 validator**（对比讨论侧有实测且已机检）。

**详细说明**：[skills/proj-plan/SKILL.md](./skills/proj-plan/SKILL.md)

---

## proj-run（执行调度 · Executing）

**做什么**：承接 proj-plan 的 `phase-NN/plan.md`（必含 `## Sub-agent dispatch manifest` 段），负责 sub-agent 调度、model-tier 选择、validation gate、失败 escalate。对应 **PMP 6 Executing Process Group**；承接 3 项核心过程（Direct & Manage Project Work + Manage Quality + Manage Project Knowledge），其余 7 项刻意外置。

**前置条件**：proj-plan 已交付 plan.md 含 `## Sub-agent dispatch manifest` 段（5 字段闭环：objective / specialist / validation criteria / iteration budget / escalate）；GATE-3 已通过。

**Dispatch 层 runtime 无关**（ORD-28 · EXP-08 passed）：core 经 **DispatchCapability 接口**（`spawn`/`collect`）调度，由 adapter 落地；core（决策树 / manifest / validation gate / budget / escalate）不含 runtime 专属硬编码。

| adapter | context 隔离 | model 可选 | 实跑状态 |
|---------|-------------|-----------|----------|
| **cursor**（含 3 Mode α/β/γ）| ✓ | ✓（3.3+ 条件可选 · ORD-16 修订）| EXP-04 + EXP-12 步1 验证 |
| **conversation-fallback**（通用兜底）| ✗ | ✗ | EXP-08 实跑 |
| **claude-code**（骨架）| ✓ | ✓ | 待补验 |

**Cursor adapter 的 3 Mode 表**（按 plan 类型 + 是否跨 session 选择，**不**按 cost）：

| Mode | 触发条件 | 实现方式 |
|------|---------|----------|
| **α**（自动 dispatch）| usage-based plan + 同一 IDE session | `.cursor/agents/<name>.md` + Task tool 直接调用 |
| **β**（message bus）| 跨 IDE session / 单 sub-agent 输出 > 父 context | `.apm/bus/` 文件级通信（占位 · 无 runtime）|
| **γ**（手动模型切换）| legacy request-based plan | 按 model-tier：执行用 `execution`、规划/评审用 `planning` |

**Model-tier 配置**：`docs/pmo/model-tier.yaml`（可选）覆盖 skill 默认 [`assets/model-tier.yaml`](./skills/proj-run/assets/model-tier.yaml)。默认 `planning: claude-opus-4-8-thinking-high` / `execution: cursor-grok-4.5-high-fast`。manifest 仍禁止写具体 model 名。

**Validation gate 3 类**：structural（文件存在/字段齐/行数上限）/ lint（validate_skills.py / YAML frontmatter）/ behavioral（关键字 grep / 负向断言）。

**Sub-agent dispatch 决策树**：第一判据 = "task 输出是否需要被父持续回溯"；需回溯 → 不该 sub-agent；fire-and-forget → 候选 sub-agent。

**产出**：

```text
docs/pmo/phase-NN/
├── acceptance.md          # validation 结果 + token cost + escalate 标记 + GATE 联动
└── （回写 artifact-index.md）

docs/pmo/model-tier.yaml   # 可选；覆盖 skill 默认 planning/execution
.cursor/agents/<name>.md   # 仅 Mode α 时
.apm/bus/                  # 仅 Mode β 时（用户人工 shuttle）
```

**Cursor adapter 约束**（ORD-16 · 2026-07-07 修订为「3.3+ 条件可选」）：Cursor 3.3+ 起 sub-agent model pin 被尊重（Task tool `model` 参数 / `.cursor/agents/*.md` frontmatter；本仓库 EXP-12 步1 三路差分实测通过，见 `docs/pmo/exp-12-spike/`）。仍成立的条件：**legacy request-based plan 无 Max Mode 时强制 Composer**（此时降级 Mode γ）；team admin 屏蔽 / plan 不含该模型时配置被覆盖。历史「enum 仅 fast」约束（[Cursor Forum #156736](https://forum.cursor.com/t/task-tool-model-parameter-only-accepts-fast-cannot-specify-model-ids-for-subagents/156736)）已失效；EXP-04 经济性结论待 EXP-12 步2 复测。

**触发词示例**：proj-run · 执行调度 · sub-agent · dispatch manifest · validation gate · dispatch adapter · DispatchCapability · runtime 无关 · Mode α/β/γ · `.cursor/agents/` · message bus · `.apm/bus/` · model-tier · model-tier.yaml

**详细说明**：[skills/proj-run/SKILL.md](./skills/proj-run/SKILL.md)

---

## proj-survey（现状勘测 · 接管入口 / brownfield）

**做什么**：接管**已有代码/文档的历史项目**时，AI **自动**读既有系统（按 测试 > 代码 > git/issue > docs > 口述 优先级采集真相源），产出**三分离现状基线**（已查证事实 / 推理 / 待验证），做意图(to-be)重建评估，经 **GATE-S** 人审批后分支。

**为什么独立**：正向 4 skill 都从「人的想法」出发，没有任何一个读既有系统；接管历史项目是独立关注点，故单独成 skill（与 proj-shape 并列为第二入口）。

**两个分支**：

| 分支 | 条件 | 产出 | 下游 |
|------|------|------|------|
| **A · 可 plan** | intent 可信重建 | 规划交接（已完成范围=既成约束 + 未完成工作=WBS 三态种子）| → proj-plan（brownfield 入口）|
| **B · 仅 audit** | intent 不可重建 | 完整性审计报告（findings + 置信度，**不**作「无缺失/无 bug」保证）| 终端；可选回 proj-shape 补 intent |

**关键纪律**：文档说的 ≠ 代码做的（docs 单方声称入「待验证」）；「自动」= baseline 生成全自动 + 人仅在 GATE-S 拍板（人只读 ≤5 项摘要）；审计分支无 intent 时只评内部一致性，不作正确性保证。

**意图重建走碰撞（ORD-56）**：AI **保持**真相源优先级推出**候选意图** → 人**独立**校对 → **不一致处 = 讨论点/修改点**，不预设谁对。为什么不是「把优先级倒过来」：那个排序排的是**事实**的可信度，而「当初想做成什么」不是事实、是**意图**——它没有真相源，只有**认可**；从代码恢复出来的是**实现**，分不清「意图是 X 但有 bug」和「意图本就是 X′」。所以顺序留给产出候选，认可由人的校对承担；不一致恰恰是那个分岔的显影剂。重建结论只能标 `待认可`/`已认可`，**不得标 `已查证`**。

**产出目录**：`docs/survey/`（基线 + handoff 或 审计报告）。

**触发词示例**：proj-survey · 现状勘测 · 历史项目接管 · 遗留 · legacy · brownfield · 逆向盘点 · 完整性评审 · as-is · takeover

**详细说明**：[skills/proj-survey/SKILL.md](./skills/proj-survey/SKILL.md)

---

## 推荐组合用法

### 完整链路（新项目）

1. **讨论**：「帮我讨论一下 XXX 想法」→ `proj-shape` 自动建 `BRAINSTORM.md`（用户低负担填初稿）→ round 01 苏格拉底六问追问澄清 → round 02+ 调 `proj-experts` 攻防
2. **就绪**：多轮后确认 `DECISIONS.md` 为 `ready-for-implementation`
3. **规划**：「按 DECISIONS 做项目规划」→ `proj-plan`（Round A → Round B → 按需进阶段，含 dispatch manifest）
4. **执行**：「按 plan + manifest dispatch sub-agent」→ `proj-run`（按 3 Mode 选择 → validation → escalate → acceptance）

### 只要专家分析

「谁最懂 RAG 评估？请以 Andrej Karpathy 视角分析」→ 单独用 `proj-experts`

### 已有决定，直接规划

若项目已有 `docs/discuss/DECISIONS.md` 且状态就绪 → 直接用 `proj-plan`

### 已有 plan + dispatch manifest，直接执行

若项目已有 `phase-NN/plan.md` 含 `## Sub-agent dispatch manifest` 段 → 直接用 `proj-run`

### 接管历史项目（brownfield）

「帮我接管这个已有项目 / 摸清现状」→ `proj-survey` 自动生成 `docs/survey/` 现状基线 → GATE-S 人审批分支：
- intent 可信重建 → 交 `proj-plan` 规划未完成工作
- intent 不可重建 → 完整性审计报告（findings + 置信度）；如需继续 → 回 `proj-shape` 补 intent

---

## 设计理念

- **角色分工**：人 = Sponsor + PM 关键决策权（GATE 审批 / abort/retry / 关键 trade-off）；AI = PM 执行 + sub-agent 调度 + artifact 维护；对应 [Agentic PM Supervised-AI mode](https://arxiv.org/html/2601.16392v1)
- **人类只读 manifest（≤5 项）**：避免人类被全量 PM artifact 树淹没；AI 维护完整 artifact 集
- **借鉴 vs 自创术语显式标注**：每个 SKILL.md 都含「立场声明」节，区分 PMBOK 6/7/8 借鉴 / GitHub Spec Kit 机制借鉴 / 本 skill 自创术语（Coach hybrid / 模式 T-F / GATE-N / 3 Mode 表 / 5 字段闭环 manifest 等）
- **决定单一真源 DECISIONS.md**：其它 skill / 用户在落地前只需读 DECISIONS.md，无需通读全部讨论轮次

---

## 开发与贡献

```bash
# 校验所有 skill（YAML frontmatter + 命名 + 长度上限 600 行）
uv run scripts/validate_skills.py

# 从模板新建 skill
cp -r template skills/my-new-skill
```

详见 [CONTRIBUTING.md](./CONTRIBUTING.md)；本文件即 6 skill 索引（不再单独维护 `skills/README.md`）。

变更历史见 [CHANGELOG.md](./CHANGELOG.md)。

## License

MIT — 见 [LICENSE](./LICENSE)。
