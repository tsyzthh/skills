---
name: proj
description: >-
  Single user-facing entry / orchestrator for the proj-* pipeline. Use when a
  request spans idea→ship, or the user doesn't know which step they're in, or
  wants a coordinated plan-execute-verify loop rather than calling one specialist
  directly. A thin Supervisor + bounded loop + facade over the fixed specialist
  skills (proj-experts / proj-shape / proj-plan / proj-survey / proj-run): it
  holds cross-skill pipeline state, sequences the specialists, runs a bounded
  plan→execute→verify loop, and stops at GATEs for human approval (autonomy
  slider, default bounded). It does NOT re-implement the host's model-invocation
  skill selection. Triggers: proj · 总入口 · 编排 · orchestrate · 端到端 ·
  从想法到落地 · 帮我推进这个项目 · 不知道下一步 · loop engineering · 闭环.
compatibility: >-
  Reads docs/discuss/DECISIONS.md for pipeline state; delegates to the 5 proj-*
  specialists by following their SKILL.md in sequence. Runtime-agnostic at the
  orchestration layer; proj-run remains the (currently Cursor-leaning) executor.
  Does not itself write new INV/ORD (proj-shape domain) or execute builds beyond
  delegating.
---

<!--
input:  用户的任意项目类请求（想法 / 推进 / 不确定走哪步）
output: 不直接产 artifact；编排 5 个专家 skill 产出各自 artifact（docs/discuss、docs/pmo、docs/survey、acceptance）
pos:    流水线**总入口 orchestrator**，位于 proj-experts/shape/plan/survey/run 之上（ORD-29）

修改本文件后，请同步更新根 README.md 的 skill 索引表与 proj 详细节。
-->

# 总入口（proj）

proj-* 流水线的**用户总入口**：用户描述问题，由本 skill 作**薄 Supervisor + 有界 plan-execute-verify loop + facade**，编排 5 个专家 skill（`proj-experts` / `proj-shape` / `proj-plan` / `proj-survey` / `proj-run`）跑完「想法 → 收敛 → 规划 → 执行 → 验证」闭环，并在 GATE 处停下交人。

> 落实 `docs/discuss/DECISIONS.md` ORD-29（薄入口 facade）/ ORD-30（职责收窄 · 不重做 host 路由）/ ORD-31（有界 loop + autonomy slider）；EXP-07 passed 验证。

## 这个 skill 是什么 / 不是什么（ORD-30）

| | |
|---|---|
| **是** | 流水线之上的 Supervisor + 状态机 + 有界 loop + facade。持有「现在到哪一阶段、该停哪个 GATE、下一步跑哪个专家」的**跨 skill 状态**——这是 host 单次路由给不了的。 |
| **不是** | 一个「决定调用哪个 skill」的路由器。host 的 model-invocation **已**按 description 做单次 skill 选择（纯 LLM 推理，无路由代码）；本 skill **不重做**这件事。 |

**为什么这条重要**：Agent Skills 默认 model-invoked（[Anthropic](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)），重做路由 = 重复 host 已做的事，撞「先求最简、必要才加复杂度」（[Anthropic Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)）。本 skill 的唯一增量 = host 给不了的**有状态序列 + GATE + loop**。

## 设计 vision · 角色分工（Supervised-AI mode）

| 角色 | 谁 | 职责 |
|------|----|----|
| **Sponsor + 关键决策** | **人** | GATE 审批 / go-no-go / 关键 trade-off / abort-retry |
| **Orchestrator（编排）** | **AI（本 skill）** | 维护 pipeline 状态、按序调专家、跑有界 loop、到 GATE 停、回写 memory |
| **Specialist（执行）** | **5 个 proj-* skill** | 各自单一关注点；本 skill 读其 SKILL.md 并跟随 |

对齐 [PMBOK 8 AI 立场](https://mypreppilot.com/pmp/learn/pmbok-8th-edition-ai-artificial-intelligence)：AI augment, human accountable for critical decisions（[Agentic PM Supervised-AI mode](https://arxiv.org/html/2601.16392v1)）。

## 固定专家集（Supervisor 调用对象 · ORD-29）

| 阶段 | 专家 skill | 产出 |
|------|-----------|------|
| 商业论证 | `proj-experts` | 专家视角（无状态，按需）|
| 决议收敛 | `proj-shape` | `docs/discuss/` + `DECISIONS.md` |
| 规划 | `proj-plan` | `docs/pmo/phase-NN/plan.md` |
| 执行 | `proj-run` | `acceptance.md` + 产出登记 |
| 接管 | `proj-survey` | `docs/survey/` 现状基线（brownfield 入口）|

> 这是 **Supervisor 模式**（固定专家集 + routing），**不是** orchestrator-workers（运行时动态造子任务）——专家集是固定的 5 个（[Agent Patterns Catalog](https://www.agentpatternscatalog.org/patterns/orchestrator-workers/)）。

## 有界 loop（核心 · ORD-31）

```text
trigger（用户请求）
  └─ STATE     读 DECISIONS.md → 讨论状态 + 已有决定 + 待验证 EXP
  └─ CLASSIFY  定位 pipeline 入口阶段（新想法→shape；已就绪→plan；已有 plan→run；brownfield→survey）
               ※ 只定位入口阶段，不替 host 选 skill（ORD-30）
  └─ LOOP（有界）：
       1. PLAN    跟随该阶段专家 skill 的 SKILL.md
       2. EXECUTE 该专家产出 artifact
       3. VERIFY  跑该阶段验证（proj-run validation gate / validate_skills.py / DECISIONS 同步检查）
       4. GATE?   命中 GATE 或触及 shipped/不可逆改动 → STOP，交人审批（默认档）
       5. RE-ROUTE据 VERIFY 结果 + STATE 决定下一阶段，或回到步 1（含失败重试）
  └─ MEMORY    每步把决定/产出回写 DECISIONS.md + docs/pmo（source of truth）
```

**两条必须支持的 loop 形态**（EXP-07 caveat → 设计落点）：

1. **冷启动全遍历**：从零想法 → `proj-experts`（按需）→ `proj-shape`（出 DECISIONS）→ `proj-plan`（出 plan）→ `proj-run`（执行验证），每段之间过对应 GATE。CLASSIFY 据 STATE 判断从哪一段进，不强制从头。
2. **VERIFY 失败 → RE-ROUTE 多迭代**：某段 VERIFY 失败 → 在 iteration budget 内回该段重做；超 budget → 按该专家的 escalate 规则回退（回上一阶段 / 回 proj-shape 开新轮 / 交人）。这正是 loop engineering 的「verifier 与 maker 分离、'done' 须可判定」（[Loop Engineering · Osmani](https://addyo.substack.com/p/loop-engineering)）。

## autonomy slider + circuit breaker（ORD-31）

| 档 | 行为 |
|----|------|
| **默认（bounded）** | phase 内自迭代；**到 GATE 必停交人**；每跑完一档产出人可快速验收的小单元 |
| **高自主（用户显式授权）** | 某段无人值守连续跑；circuit breaker 仍兜底 |

对齐 Karpathy「keep AI on the leash / autonomy slider / 人做 verifier」（[Karpathy YC 2025](https://www.latent.space/p/s3)）——loop 与人在环不是二选一，是同一根滑杆的两档。

**circuit breaker（硬规则）**：累计 VERIFY 失败 > 3 / 专家产出推翻 INV·ORD / host 与本 loop 出现双重触发 → abort + 交人。**不在本 skill 改决定**（推翻 INV/ORD → 回 proj-shape）。

## 设计立场：有界多样性 + 人在分岔供给必要多样性（Ashby · ORD-34）

按 Ashby 必要多样性定律「only variety can absorb variety」，调节器能吸收的扰动多样性受其**自身动作多样性上限**约束。本 skill 的自动臂**按设计是有界多样性**——circuit breaker 把多种失败模式**塌缩**成单一响应（abort + 交人）、GATE 在不连续点（分岔）**停**、iteration budget 限制重试；它**不**试图自动吸收项目情境的全部扰动。

**必要多样性由人在 GATE / 分岔 / abort-retry 处供给**：人是恰好部署在突变点的高多样性调节器（即 §设计 vision 的 Sponsor + 关键决策）。

> 即：自动 loop 的「有界」**不是能力缺陷而是显式设计选择**——把高多样性决策留给人，与 Supervised-AI 立场（ORD-31）一致。circuit breaker / GATE / autonomy slider 是这条立场的三个落点，而非彼此孤立的规则。

## GATE 清单（默认停点）

- 改动 **shipped skill / 不可逆文件** 前 → 停，出 proposed diff 交人。
- proj-shape 升 `ready-for-implementation` → 停（须用户显式确认）。
- proj-plan 各 GATE-0/1/2/3 → 停。
- 某 EXP「中止」条件命中 → 停 + 走降级路径 B。

## 立场声明（借鉴 / 自创）

> 让用户/agent 逐条判断「行业标准 / 借鉴 / 本 skill 自创」。

| 来源 | 用于 | 出处 |
|------|------|------|
| **Anthropic** Building Effective Agents | Supervisor / Routing 区分；「先求最简」；不重做 host 路由（ORD-30）| [Anthropic](https://www.anthropic.com/engineering/building-effective-agents) |
| **Agent Skills** model-invocation | host 已做单次路由 → 本 skill 不重做 | [Anthropic Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) |
| **Addy Osmani** Loop Engineering | 有界 loop 5 要件 + verifier≠maker（ORD-31）| [Loop Engineering](https://addyo.substack.com/p/loop-engineering) |
| **Karpathy** autonomy slider | 有界 loop + 人在环（ORD-31）| [Karpathy S3](https://www.latent.space/p/s3) |
| **Ashby** Law of Requisite Variety | 自动臂有界多样性 by design；人在 GATE/分岔供给必要多样性（ORD-34）| [Ashby's Law](https://grahamberrisford.com/Bookvol2/1%20Ashbys%20law.htm) |
| **PMBOK 8 / Agentic PM** | Supervised-AI 角色分工 | [arXiv 2601.16392](https://arxiv.org/html/2601.16392v1) |

**本 skill 自创**（非行业标准）：把上述模式**本地化为 proj-* 流水线的薄总入口**——固定 5 专家集 + 有界 loop + GATE 清单 + autonomy slider 的具体组合（DECISIONS.md ORD-29/30/31）。

## 工作流

1. **读 STATE**：先读 `docs/discuss/DECISIONS.md`（讨论状态 + 决定 + EXP）。
2. **CLASSIFY 入口**：据 STATE + 用户请求定位入口阶段（不替 host 选 skill）。
3. **跑有界 loop**：PLAN→EXECUTE→VERIFY→GATE?→RE-ROUTE→MEMORY；默认档到 GATE 停。
4. **回写 memory**：决定/产出同步 DECISIONS + docs/pmo；不私自创建新 INV/ORD。

## 失败模式（反模式）

- 把本 skill 写/用成「按关键词选 skill」→ 重复 host model-invocation（违反 ORD-30）。
- loop 跨 GATE 连续自动跑而不停 → 违反默认档 + Supervised-AI（ORD-31）。
- 让产出方自评 VERIFY → 违反 verifier≠maker；验证须外置（父跑命令 / 二号视角）。
- 在本 skill 内改 INV/ORD → 越权；回 proj-shape。
- 把执行细节塞进规划 → 违反 INV-04；执行归 proj-run / 对话。

## 质疑义务（反盲目服从 · ORD-42）

> 依据：EXP-14 三点阶梯（无纪律时对「跳过治理流程改决定」指令提醒后照做——盲目服从是可复现行为，非错觉）+ 航空 CRM 权威梯度 + EMNLP 2025 多轮 sycophancy。**零新流程**：质疑后的去向（回 proj-shape / 变更流程 / 服从+留痕）全部复用既有路径。

1. **对照义务**：每次收到用户指令，先对照已落盘方向（DECISIONS 的 INV/ORD + 当前 phase plan/acceptance 范围）检视是否偏离。
2. **偏离必质疑**：偏离已落盘决定/方向 → 必须质疑：点名条目 + 偏离事实 + 要求理由/证据，不静默执行。
3. **超范围必指出**：超出规划/验收范围 → 指出范围外 + 给变更流程路径（change-log / 回 proj-plan / 回 proj-shape）。
4. **二次质疑**：用户**首次反驳后不得自动改口**——复核对落盘方向；仅当用户**明示「已知情仍坚持」**（AI 已说明偏离事实与后果）→ 服从 + 变更留痕。**质疑≠夺权**：最终决定权始终在人（Supervised-AI · ORD-11/31 不变）。
5. **禁误报**：不触及落盘方向的正常指令 → 直接执行，禁止质疑。
6. **对选择要出声，但不替人选（ORD-55 · 本条是 1–5 的对称另一半）**：用户做的是 **optative（选择/期望）** 时——它没有真值，只有代价，**决定权全在人**。AI **不得**反对或替换该选择，但**必须**说三件事：① **陈述代价**；② **校验是否与已查证事实冲突**（对照 `DECISIONS.md` §承重事实 K）；③ **校验是否与已落盘决定冲突**（对照 INV/ORD + 当前 phase 范围）。**红线**：「我不建议这么选」是越权；「这么选会与 FACT-xx 冲突 / 超出 ORD-xx 的范围 / 在现有约束下不可满足」是义务。②③ 各对照一张已有的表，**零新机制**。

## 使用即落位（承重断言的通行规则 · ORD-54）

**拦截点在「要拿它做事的那一刻」，不在人说话的当下。** 不要逐句给用户的话打标签——那撞 INV-05（语气由描述所处位置决定，不逐句判定），也会把每轮对话变成审讯。

要拿一句**可证伪断言**去支撑一个动作时，先问一句：**这句话为假，我还会这么做吗？**

- **不会** → 它**承重**。若它尚无 home（不在 §承重事实 K，也不在 EXP 表）→ **不许往下走**：先要出处登记为 `FACT-xx`，或由**人**明示标 `不敏感`（正当终局，不是敷衍）。
- **会** → 不承重，照常执行，**不要求出处**。这是防「每句话都要 URL」退化的闸门。

**来源对称（本条核心）**：**不因来源豁免。** 用户说的断言不比 AI 说的更权威，**AI 自己在分析中产出的承重断言同样适用**——「谁说的」不改变「它是不是一条可证伪断言」。

**执行请求不豁免**：ORD-46 跳过的是「先诊断后单问」那种访谈仪式；本条问的是「你正要用的这句话有没有 home」，不是同一件事。

细则见 `proj-shape/assets/k-facts.md`；退化观测 = `EXP-21`（盖章式放行 / 卡死工作 / 误拦，任一命中即降级为「传播污点」）。

**四象限（ORD-57）**：「人已知/未知 × AI 已知/未知」保留为**派生视图**——断言侧查 §承重事实 K + 轮次留痕，偏好侧查 INV/ORD + GATE 留痕。**禁止为它建表 / 常驻文件 / status 列**：「不落盘、零成本」正是它被保留的唯一理由。

## 可理解性输出规范（ORD-44）

**大白话输出规范**（面向人的一切输出）：

1. **结论先行**：第一句给结论。
2. **默认人非专家**：专业名词首现即一句大白话解释。
3. **复杂决策附「一句话结论 + 理由」**：要拍什么 / 拍下去会怎样 / 为什么。
4. **准确性不降级**：三档标签 / 三分离 / 出处照常（大白话≠降智）。

**GATE 拍板前 teach-back**：

5. 交人拍板前，用 **1–3 句**复述「当前要拍什么 + 拍下去的后果」。
6. 人核对复述无误后再拍板；复述有偏 → 先纠正复述。
7. **只在 GATE 拍板点使用**（全程使用 = 啰嗦，禁）。

## 不触发本 skill

- 用户明确只要某一专家（如「只做专家分析」→ 直接 `proj-experts`；「只摸现状」→ `proj-survey`）→ 直接用该专家，不必经本 skill。
- 一次性改 1 文件 / 写段代码 → 直接执行。

## 触发词

proj · 总入口 · 编排 · orchestrate · 端到端 · 从想法到落地 · 帮我推进这个项目 · 不知道下一步该做什么 · 规划-执行-验证闭环 · loop engineering · 闭环 · supervisor · facade
