---
name: proj-run
description: >-
  PMP Executing skill 承接 proj-plan 的 phase-NN/plan.md（必含 Sub-agent
  dispatch manifest · ORD-21 5 字段闭环），负责 sub-agent 调度、model-tier
  选择、validation gate（structural/lint/behavioral · ORD-22）、失败 escalate 回
  phase-NN/acceptance.md。承接 PMP 6 Executing 中 Direct & Manage Project Work
  + Manage Quality + Manage Project Knowledge 3 项（ORD-18），其余 7 项刻意外置。
  与 proj-plan 接口契约 = phase-NN/plan.md（artifact-level 文件契约）。
  Dispatch 层 runtime 无关（ORD-28 · EXP-08 passed）：core 经 DispatchCapability
  接口 spawn/collect，由 adapter 落地（Cursor 3 Mode α/β/γ / conversation-fallback
  通用兜底 / Claude Code 骨架）。
compatibility: >-
  Reads docs/pmo/phase-NN/plan.md (from proj-plan). Writes docs/pmo/phase-NN/
  acceptance.md back. Core (dispatch decision tree / manifest / validation gate /
  budget / escalate) is runtime-agnostic; only the spawn mechanism is per-adapter.
  Cursor adapter optionally generates .cursor/agents/*.md (Mode α) or .apm/bus/
  (Mode β placeholder); model_selectable=true on Cursor 3.3+ (legacy plan without
  Max Mode still forces Composer; see ORD-16 revised).
  conversation-fallback adapter works on any runtime (no context isolation).
---

<!--
input:  docs/pmo/phase-NN/plan.md（由 proj-plan 产出；必含 ## Sub-agent dispatch manifest 段 · ORD-21 5 字段闭环）
output: docs/pmo/phase-NN/acceptance.md（含 validation 结果 + token cost + escalate 标记）
        + .cursor/agents/*.md（Mode α 时；usage-based plan）
        + .apm/bus/ 目录（Mode β 时；占位无 runtime）
        + docs/pmo/artifact-index.md 追加（sub-agent 产出登记）
        + docs/pmo/model-tier.yaml（可选；覆盖 skill 默认 planning/execution）
pos:    PMP Executing Process Group；与 proj-plan 串联在 PMP Planning 之后

修改本文件后，请同步更新根 README.md 的 4 skill 索引表与 proj-run 详细节（skills/README.md 已于 1.2.0 合并至根 README）。
-->

# 执行调度（proj-run）

承接 proj-plan 的 **`docs/pmo/phase-NN/plan.md`**（必含 `## Sub-agent dispatch manifest` 段 · ORD-21 5 字段闭环），负责 **PMP Executing Process Group** 的 sub-agent 调度、model-tier 选择、validation gate、失败 escalate。

**执行归本 skill；规划与商业论证不归本 skill**（规划 → `proj-plan`；商业论证 → `proj-experts` + `proj-shape`）。

## 设计 vision

proj-run 是 **PMP Executing Process Group** 的承载者，与 `proj-experts`（商业论证）→ `proj-shape`（决议收敛）→ `proj-plan`（Initiating + Planning + 规划侧 M&C + 阶段 Close）构成完整 proj-* 流水线（对应 PMP 4 大 Process Group）。

**角色分工对应 [Agentic PM 框架 Supervised-AI mode](https://arxiv.org/html/2601.16392v1)**：

| 角色 | 谁担任 | 职责 |
|------|--------|------|
| **Sponsor + PM 关键决策权** | **人** | execute 过程中的 GATE 审批 / validation 反复失败时 abort/retry 决策 / 关键 trade-off |
| **PM 执行 + sub-agent 调度** | **AI**（父 agent） | 按 model-tier 策略调度 sub-agent / 评审 sub-agent 输出 / 跑 validation / 维护 acceptance.md + artifact-index.md |
| **Specialist 执行** | **Sub-agent**（角色由 dispatch manifest 指定）| 单一 task 起草 / 评审 / 审计；fire-and-forget；不得越权改其它文件 |

与 [PMBOK 8 AI Appendix](https://mypreppilot.com/pmp/learn/pmbok-8th-edition-ai-artificial-intelligence) 立场对齐：**AI augment, human accountable for critical decisions**（特别是 validation 反复失败时的 escalate）。

**继承 proj-plan 的 JIT 规划原则（ORD-27）**：proj-run 只执行**当前阶段**那份「恰好足够」的 rolling-wave plan，**不**把未来阶段的细节提前拉进来执行。执行侧的「恰好足够」已落在两处既有机制，无需新增：**§Sub-agent dispatch 决策树**（不为了用而用——只在该 dispatch 时 dispatch）+ **iteration budget**（不过度迭代）。

## 与 `proj` 入口的关系（ORD-29）

用户通常经 **`proj`**（流水线总入口 orchestrator）间接到达本 skill：`proj` 负责跨 skill 状态机 + 有界 loop + GATE 编排（ORD-30/31），本 skill 仍**专管 PMP Executing**（ORD-17/18 不变）。直接调用本 skill 亦可——`proj` 不改变本 skill 的职责边界。

## 立场声明（借鉴 / 自创）

> 让用户与 agent 能逐条判断"这是行业标准 / 借鉴 / 本 skill 自创"。**未在此声明的术语不应被当作 PMI 行业标准。**

### 基准版本（借鉴的真实标准）

| 来源 | 用于 | 出处 |
|------|------|------|
| **PMBOK 6** Executing Process Group（10 过程）| 覆盖范围基准；承接 3 项 + 刻意外置 7 项（ORD-18） | PMBOK Guide 6th Edition (PMI, 2017) |
| **PMBOK 7** Tailoring 原则 | "deliberate choice" 边界裁剪 | [PMI Tailoring PDF](https://www.pmi.org/-/media/pmi/documents/public/pdf/pmbok-standards/pmi-tailoring.pdf) |
| **PMBOK 8** AI Appendix | 人 / AI 责任分工原则（延续 proj-plan ORD-11）| [AI in PMBOK 8](https://mypreppilot.com/pmp/learn/pmbok-8th-edition-ai-artificial-intelligence) |
| **Aider architect/editor 模式** | model-tier 编排原理（强推理模型规划 + 便宜模型执行）；5 字段闭环 dispatch manifest 设计灵感（ORD-21）| [Aider blog 2024-09-26](https://aider.chat/2024/09/26/architect.html) |
| **Anthropic Claude Code subagents** | Supervisor + Specialists 模式（96.3% 成功率）；blast radius containment 原则；sub-agent dispatch 决策树（ORD-20）| [Claude Code agents docs](https://code.claude.com/docs/en/agents.md) |
| **Cursor `.cursor/agents/*.md`** | Mode α 实际 dispatch 实现方式 | [Cursor Subagents 完整指南](https://medium.com/@codeandbird/cursor-subagents-complete-guide-5853e8d39176) |
| **APM 框架** | Mode β Message Bus 跨 sub-agent 通信备选（占位 · 无 runtime）| [APM Getting Started](https://github.com/sdi2200262/apm-website/blob/main/docs/Getting_Started.md) + [APM-Auto fork](http://github.com/sdi2200262/apm-auto) |

### 本 skill 自创术语（**不是** PMI 标准）

| 术语 | 含义 | discuss 出处 |
|------|------|------|
| **3 Mode 表（α / β / γ）** | proj-run 的 3 个执行模式（按用户 plan 类型 + 跨 session 需求选择）；ORD-28 后降为 **Cursor adapter 内部策略** | `docs/discuss/07-…md` §F1；DECISIONS.md ORD-19 |
| **DispatchCapability 接口 + adapters** | runtime 无关的 `spawn`/`collect` 接口 + Cursor / conversation-fallback / Claude Code adapter；把 Cursor 专属机制隔离出 core | `12-…md` §EXP-08；`docs/pmo/proj-run-generic-spike/`；DECISIONS.md ORD-28 |
| **Dispatch manifest 5 字段闭环** | manifest 段每条 task 必含 objective / specialist / validation criteria / iteration budget / escalate 5 字段 | `docs/discuss/08-…md` §视角 B；DECISIONS.md ORD-21 |
| **Validation gate 3 类** | structural / lint / behavioral 3 类 validation 分类 | `docs/discuss/08-…md` §视角 B 延伸；DECISIONS.md ORD-22 |
| **Sub-agent dispatch 决策树** | "task 输出是否需要被父 agent 持续回溯"作为第一判据；不按 cost | `docs/discuss/08-…md` §视角 C；DECISIONS.md ORD-20 |
| **PMP 6 Executing 边界声明** | 承接 3 项 + 刻意外置 7 项的边界（与 proj-plan ORD-10 同构纪律）| `docs/discuss/08-…md` §视角 A；DECISIONS.md ORD-18 |

### ORD-16 · Cursor adapter 约束披露（`model_selectable` = 3.3+ 条件可选 · 2026-07-07 修订）

> 这是 **Cursor adapter 的属性声明**（非 core 限制 · ORD-28）。用户/agent 必须知晓的当前 Cursor 实现状态：

【已查证 + 实测】**Cursor 3.3+（2026-05 起）sub-agent model 可选**：Task tool `model` 参数接受具体 model slug 并被尊重；`.cursor/agents/*.md` frontmatter 显式 `model:` 同样被尊重（staff 确认「always respect the selected model」，pin 特定版本需写作 `model: [composer-2.5]` 防 silent 解析为 fast）。本仓库 EXP-12 步1 三路差分实测通过（fast / 跨 vendor 高档 / inherit 对照 + 负断言无 silent fallback），见 `docs/pmo/exp-12-spike/exp-12-result.md`。依据 [Cursor Docs Subagents](https://cursor.com/docs/subagents)、[Forum #159981](https://forum.cursor.com/t/prohibition-of-composer-2-for-sub-agents/159981)。

**仍成立的条件约束**：**legacy request-based plan 无 Max Mode 时**，内置 subagent 一律强制 Composer（by design）；team admin 屏蔽 / plan 不含该模型时配置被覆盖。历史约束（`model` enum 仅 `fast` · [Forum #156736](https://forum.cursor.com/t/task-tool-model-parameter-only-accepts-fast-cannot-specify-model-ids-for-subagents/156736)）已随 3.3 失效——EXP-04（2026-05-27）的 cost 测算即在该旧约束下做出，其经济性结论待 EXP-12 步2 复测（外部前提 · ORD-39）。

Dispatch 接口 + adapter 选择见下一节。

## PMP 6 Executing 边界声明（ORD-18 · 与 proj-plan ORD-10 同构）

> 按 [PMBOK 7 tailoring](https://www.pmi.org/-/media/pmi/documents/public/pdf/pmbok-standards/pmi-tailoring.pdf) 的 "deliberate choice" 原则做 just-enough process。

**承接**（3 项；与 sub-agent dispatch + validation 强相关）：

| PMBOK 6 Executing 过程 | proj-run 落实方式 |
|----------------------|-------------------|
| **Direct & Manage Project Work** | sub-agent dispatch（按 dispatch manifest 执行 plan.md 任务）|
| **Manage Quality** | validation gate（3 类：structural / lint / behavioral · ORD-22）|
| **Manage Project Knowledge** | sub-agent 产出登记到 artifact-index.md（避免 source of truth 分裂；INV-03 精神）|

**刻意外置**（7 项；由对话 / proj-plan handoff / 人工分配承接）：

| PMBOK 6 Executing 过程 | 外置原因 | 替代承接 |
|----------------------|---------|----------|
| Acquire Resources | 个人/小团队场景无资源采购 | proj-plan handoff 字段 + 人工 |
| Develop Team | 同上 | 人工 |
| Manage Team | 同上 | 人工 |
| Manage Communications | sub-agent 间沟通仅通过 manifest + artifact-index | proj-plan integration-plan |
| Implement Risk Responses | 由 proj-plan circuit breaker 触发 | proj-plan |
| Conduct Procurements | 项目级采购属 proj-plan ORD-10 已声明不含 | proj-plan / 对话 |
| Manage Stakeholder Engagement | 同 Manage Communications | proj-plan |

## Dispatch capability 接口 + adapters（ORD-28 · EXP-08 passed · runtime 无关化）

> core 只依赖 **DispatchCapability 接口**（`spawn`/`collect`）；「怎么真正生出 worker」由 adapter 落地。core 7 组件中 5 个（dispatch 决策树 / manifest / validation gate / iteration budget / escalate）本就 runtime 无关，**不经 adapter**。完整推导见 `docs/pmo/proj-run-generic-spike/`。

### 接口契约（runtime 无关）

```text
DispatchCapability:
  spawn(specialist_role, self_contained_prompt, refs) -> handle
      启动一个 worker 执行该 task（self-contained · APM 原则）
  collect(handle) -> artifact_path
      取回 worker 产出（落到 artifact-index 登记的路径）
  属性（adapter 各自声明）：context_isolation / model_selectable / cross_session
```

core 拿到 artifact 后**自己**跑 validation gate（ORD-22）+ iteration budget 重试 + 超 budget escalate——**不经 adapter**，故 runtime 无关。

### Adapter 选择（取代旧「先选 Mode」的上位概念）

```text
1. 检测 runtime → 选 adapter（cursor / claude-code / conversation-fallback）
2. adapter 内部按其能力选策略（如 cursor adapter 选 Mode α/β/γ）
3. 首选 adapter 不可用 → 降级 conversation-fallback（永远可用 · context_isolation=false）
```

| adapter | isolation | model_selectable | cross_session | 实跑状态 |
|---------|-----------|------------------|---------------|----------|
| cursor | ✓ | ✓（3.3+ 条件可选 · ORD-16 修订；legacy 无 Max Mode 除外）| ✓ | EXP-04 + EXP-12 步1 验证 |
| conversation-fallback | ✗ | ✗ | ✗ | EXP-08 实跑 |
| claude-code | ✓ | ✓ | ? | 骨架 |

### Cursor adapter = 3 Mode 表（ORD-19 · 自创术语 · 降为 adapter 内部策略）

> Mode 选择按 **plan 类型 + 是否跨 session** 决定，**不**按 cost（视角 C 关切：cost 是 by-product 不是判据）。

| Mode | 触发条件 | 实现方式 | 适用 plan 类型 | 模板引用 |
|------|---------|----------|----------------|---------|
| **α**（自动 dispatch）| usage-based plan + 同一 IDE session 内 | `.cursor/agents/<name>.md` + 父 agent 用 Task tool 直接调用 sub-agent | usage-based | [`assets/cursor-agents-template.md`](assets/cursor-agents-template.md) |
| **β**（message bus）| 跨 IDE session / 跨设备 / 单一 sub-agent 输出 > 父 context 承载 / 多 sub-agent 并行协作 | `.apm/bus/` 文件级通信；每个 sub-agent 一个独立 chat session；用户 cp/mv shuttle 消息（APM 原版）或 APM-Auto fork 自动化 | 任意 | [`assets/message-bus-template.md`](assets/message-bus-template.md)（**占位 · 无 runtime**）|
| **γ**（手动模型切换）| legacy request-based plan + 同一 IDE session | 按 §Model-tier 配置：执行段用 `execution`、规划/评审用 `planning`；**不**依赖 sub-agent dispatch | legacy request-based | — |

#### Mode 选择决策树（Cursor adapter 内部）

```text
1. 用户当前 plan 是 usage-based 还是 legacy？
   ├─ usage-based →
   │   ├─ 单一 sub-agent 输出预期 > 父 context（>50K tokens）?
   │   │   ├─ 是 → Mode β（message bus；占位 + 用户人工 shuttle）
   │   │   └─ 否 → Mode α（自动 dispatch；推荐）
   │   └─ 需跨 IDE session 工作?
   │       ├─ 是 → Mode β
   │       └─ 否 → Mode α
   └─ legacy → Mode γ（手动切换；sub-agent 自动 dispatch 受限）
2. 任何 plan 类型下，多 sub-agent 并行协作场景 → 升 Mode β
```

**实操默认**（EXP-04 试跑验证）：legacy plan 用户走 Mode γ；usage-based 用户走 Mode α；β 仅在前述特定触发条件时启用。

### conversation-fallback adapter（通用兜底 · EXP-08 实跑）

任何 runtime 可用。`spawn` = 父 agent 在**明确分隔的 scratch 文件**内按 self-contained prompt 扮演 specialist 完成 task；`collect` = 读该文件作为 artifact。**无 context 隔离 → 仅适合小 task**（与 §Sub-agent dispatch 决策树一致：context 密集 / 需父持续回溯的 task 本就该父直写，故 false 隔离不构成新风险）。EXP-08 已实跑通过（spawn→collect→validate 全 PASS，含 5 字段闭环 + cursor-token=0 负断言）。

### Claude Code adapter（骨架 · 待真实环境补验）

`spawn` = native subagents（`.claude/agents/` 或等效 Task tool）；`model_selectable=true`（无 plan 形态条件约束——比 Cursor adapter 的「3.3+ 条件可选」更干净；model-tier 经济性仍是 by-product 非判据 · ORD-20）。待真实 Claude Code 环境补全 + 实跑（EXP-08b · 非阻断）。

## Model-tier 配置（planning / execution · 可覆盖）

> model 仍归 **execute 层**（ORD-15：manifest **禁止**写具体 model 名）。配置只决定「用哪两档」，不改变 Mode α/β/γ 选择判据。

**解析顺序**（高优先覆盖低优先）：

1. 项目 `docs/pmo/model-tier.yaml`（若存在）
2. skill 默认 [`assets/model-tier.yaml`](assets/model-tier.yaml)

**默认值**（skill 内置）：

| 键 | 默认 slug | 用途 |
|----|-----------|------|
| `planning` | `claude-opus-4-8-thinking-high` | 父 agent 规划 / 评审 / analyze / escalate 接手 |
| `execution` | `cursor-grok-4.5-high-fast` | Mode α：`.cursor/agents/*.md` 的 `model:` + Task `model`；Mode γ：执行段切换目标 |

**落点**：

- Mode α：生成/更新 `.cursor/agents/*.md` 时写入 `model: <execution>`；Task tool `spawn` 传同一 slug
- Mode γ：提示用户执行段切到 `execution`、规划/评审切到 `planning`
- acceptance.md §token cost 回填实际使用的 slug
- 项目覆盖示例：复制 `assets/model-tier.yaml` → `docs/pmo/model-tier.yaml` 后改 slug

## Sub-agent dispatch 决策树（ORD-20 · 自创术语）

> 决定一个 task **是否该交给 sub-agent**（不是"该交给哪个 model"——那是 §Model-tier 配置 + Mode 落点问题）。

**第一判据 = task 输出是否需要被父 agent 持续回溯**（依据 [Claude Code agents docs](https://code.claude.com/docs/en/agents.md) "side task" 定义）：

| 判据 | 是 | 否 |
|------|----|----|
| task 输出是否需要被父 agent 持续回溯（多次引用 / 跨章节一致性 / 持续修订）| **✗ 不该 sub-agent**（父 agent 直写）| ✓ 候选 sub-agent |
| task 是否 fire-and-forget（一次完成归档，父引用结果即可）| ✓ 候选 sub-agent | ✗ 不该 sub-agent |
| task 内部是否 context 密集（多文件/多章节相互依赖）| ✗ 不该 sub-agent | ✓ 候选 sub-agent |

**「context 密集」= 结构耦合**（原文括号：多文件/多章节相互依赖），**不是输入体量**。单 artifact 只读、输出短清单、不改文件 → 第三判据为否，可过。

**判据**：**3 条都倾向 ✓ → sub-agent**；**任一 ✗ → 父 agent 直写**。

### 反模式（明确不该 sub-agent）

- **SKILL.md / 主文档跨章节一致性写作** → 父 agent 直写（章节引用密集；validation 难一行命令判定整体一致性）
- **跨多文件同步更新**（如 DECISIONS.md + 多个 artifact 一起改）→ 父 agent 直写
- **决策性内容**（如选择哪个 ORD 修订）→ 父 agent + 人审

**cost 是 by-product 不是判据**：如果用 cost 决定 dispatch（"贵的活给便宜 model"），会出现"Composer 写出来的 SKILL.md 与 plan.md 冲突，父 agent 已无法回看 sub-agent context 修复"→ 重新交付循环反而比父直写贵。

## Dispatch manifest（ORD-21 5 字段闭环 · 强制）

> 完整 schema + 字段说明 + 完整示例 + 使用规则见 [`assets/dispatch-manifest-template.md`](assets/dispatch-manifest-template.md)。

**5 字段闭环**（缺任一项 → proj-run 回退 proj-plan 补齐，不自行补全）：

| 字段 | 含义 |
|------|------|
| **objective** | task ID + 一句话目标 |
| **specialist** | sub-agent 角色 slug（`subagent:coder` / `subagent:reviewer` / `subagent:auditor` / `subagent:explorer`）|
| **validation criteria** | **可由父 agent 一行 shell/grep 命令判定**的判据列表（如 `test -f` / `grep -c "…" ≥ N` / `wc -l ≤ N`）|
| **iteration budget** | 重试次数上限（典型 2；auditor 1）|
| **escalate** | 超出 budget 时的回退路径（回父 / 回 proj-plan / 回 proj-shape）|

**与 ORD-15 的关系**：proj-plan 的 plan-template.md 中 `## Sub-agent dispatch manifest` 段是承诺字段（v0 可选；EXP-04 passed 后升级为强制按本 5 字段闭环）。proj-plan 只规划 specialist 类型与 validation；**model 选择由 proj-run 按 §Model-tier 配置 + 3 Mode 落点决定，manifest 内禁止指定具体 model 名**。

## Validation gate（ORD-22 三类 · 强制）

> 完整定义 + 示例命令 + 失败 escalate 流程见 [`assets/validation-gate-template.md`](assets/validation-gate-template.md)。

| Gate 类 | 含义 | 典型命令示例 |
|--------|------|--------------|
| **structural** | 文件存在 / 字段齐 / 行数上限 | `test -f path`、`wc -l file ≤ N`、`grep -c "字段" file ≥ N` |
| **lint** | validate_skills.py / markdown 结构 / YAML frontmatter | `uv run scripts/validate_skills.py`、YAML parse |
| **behavioral** | 关键字 grep（正向断言）/ 负向断言（确认无违规出现）| `grep -c "需求关键字" file ≥ 1`、`grep -c "禁用关键字" file = 0` |

**失败处理流程**（与 ORD-21 iteration budget 联动）：

```text
sub-agent 产出 → 父跑 validation
  ├─ 全部 pass → 归档到 artifact-index + 进下一 task
  └─ 任一 fail → 检查 iteration budget
       ├─ 仍有 budget → 父给失败原因 + 修订要点 → 重 dispatch sub-agent
       └─ budget 用尽 → 按 dispatch manifest §escalate 字段执行：
            ├─ 回父 agent 接手改写（最常见）
            ├─ 回 proj-plan 改 plan / dispatch manifest（如 validation 标准不合理）
            └─ 回 proj-shape 开新轮（如发现需新 INV/ORD/EXP）
```

### 0/100 挣得记账（ORD-41）

- plan.md 主任务表每行有 **PV**（计划权重，默认 1，可选 1–3 加权）；任务 **EV = ✓×PV**——勾 ✓ 的唯一判据 = 该任务 validation criteria **全部 pass**，任一 fail → EV=0。**禁 %complete 自报**。
- 阶段进度口径 = **EV% = Σ已✓PV / ΣPV**（在 `acceptance.md` §1 挣得进度表回填）；EV=0 的任务走上方失败处理流程（iteration budget → escalate → circuit breaker，**无新流程**）。
- 记账只作**偏差仪表**（报警 → escalate），不作考核/奖励口径（Goldratt：指标入激励即被博弈）。

## 工作流

### 0. 前置

- proj-plan 已交付 `docs/pmo/phase-NN/plan.md`（含 `## Sub-agent dispatch manifest` 段 · 5 字段闭环）
- GATE-3 已通过（用户审过 plan + dispatch manifest）
- 父 agent 已选定 dispatch adapter + 其内部策略（§Adapter 选择 → 如 Cursor adapter 的 Mode α/β/γ）
- 已 resolve §Model-tier（`docs/pmo/model-tier.yaml` → 否则 skill `assets/model-tier.yaml`）

### 1. Dispatch 准备

- 读 plan.md `## 任务` 表 + `## Sub-agent dispatch manifest` 段
- 对每条 sub-agent task 跑 §Sub-agent dispatch 决策树确认确实该 sub-agent（防止"为了用而用"）
- 准备 dispatch prompt：必须 self-contained（APM 原则：含 objective、context、reference 文件路径、validation 自检命令）
- Mode α：确保 `.cursor/agents/*.md` 的 `model:` = resolved `execution`

### 2. Dispatch 与 validation 循环

按 plan.md `## 活动依赖` 节顺序（典型串行；视场景可并行）逐 task 执行：

1. **Dispatch**：经选定 adapter `spawn` worker（接口层）
   - Cursor adapter — Mode α：父用 Task tool 调 `.cursor/agents/<name>.md`；`model` = resolved `execution`
   - Cursor adapter — Mode β：父写 task 到 `.apm/bus/tasks/<task-id>.md`；通知用户开新 chat session 接手
   - Cursor adapter — Mode γ：执行段切到 `execution`、规划/评审切到 `planning`；任务对话内完成
   - conversation-fallback：父在分隔 scratch 文件内扮演 specialist；claude-code：native subagents
2. **Validation**（core · 不经 adapter）：`collect` 产出后，父跑 §Validation gate 3 类
3. **Iteration**：失败 → 按 ORD-21 iteration budget 重试；用尽 → escalate
4. **归档**：通过 → 登记到 `docs/pmo/artifact-index.md` sub-agent 产出段 + 更新 `acceptance.md` §Sub-agent dispatch log 与 §token cost 段

### 3. acceptance.md 回写

按 [`assets/acceptance-template.md`](assets/acceptance-template.md) 维护：

- §validation 结果（structural / lint / behavioral 三类分类）
- §token cost（每个 dispatch 的 input/output token 估算 + 累计 cost）
- §escalate 标记（若有触发 escalate 的 task）
- §GATE 联动（acceptance 通过 → GATE-N 解锁 / 失败 → circuit breaker）

### 4. Phase 收尾

- acceptance 全 checkbox 通过 → 触发 proj-plan `review.md` 流程
- 全部 sub-agent 产出登记到 artifact-index.md（含路径 / 时间 / iteration 次数 / 通过 validation 项）
- 试跑 / 验证类 phase（含 EXP-xx）：把试跑数据回写到 `docs/discuss/DECISIONS.md` EXP-xx 状态行

## Circuit breaker（硬规则）

> 借鉴 proj-plan §Circuit breaker；本 skill 的失败模式直接触发以下硬规则。

| 事件 | 动作 |
|------|------|
| 单 task validation 失败 > iteration budget | 按 dispatch manifest §escalate 字段执行 |
| 全 phase sub-agent 累计失败 > 3 次 | abort 本 phase + 通知 GATE + 回 proj-plan 改 plan / 回 proj-shape 开新轮分析 |
| sub-agent 输出严重偏离 dispatch prompt（即"Opus plan 无法被 Composer 解读"）| 立即 abort + 回 proj-plan 改 dispatch manifest §validation criteria 更明确 |
| Cursor sub-agent 关键 feature 阻塞（如 Task tool 不可用 / model 字段全失效）| 切换 Mode γ 手动；记 change-log；通知 GATE |
| sub-agent 产出推翻 INV/ORD/EXP（如发现需新决定）| 立即 abort task + 回 proj-shape；**不在 execute 层改决定**（INV-04 精神延续）|
| acceptance 不通过 | proj-plan **不得**创建下一 `phase-NN/plan` |

## 失败模式（明示反模式 · 含 EXP-04 试跑发现）

- **F1**（EXP-04 试跑发现 · 前提已部分过时）：把 sub-agent 主要当 cost 优化工具用 — plan 阶段父 agent 用高档模型的固定成本在小项目中可能占 baseline >1/3，吃掉 model-tier 算术天花板（这条算术洞察与 runtime 无关，持续成立）。**注**：EXP-04 时代「只能调度 Composer Fast」的约束已随 Cursor 3.3 失效（ORD-16 修订 · EXP-12 步1 实测），执行层可 pin 任意可用档位；但经济性阈值待 EXP-12 步2 复测。**对策**：把 sub-agent 用法定位为 context 隔离（视角 C），cost 节省是 by-product；小项目不强求 model-tier；大项目（多 phase / 大 execute）才能稀释 plan 成本
- **F2**：把所有 task 都塞给 sub-agent 追求 cost 节省 — 违反 §Sub-agent dispatch 决策树；会出现"sub-agent 输出与父 plan 冲突，父无法回看 sub-agent context 修复"→ 重新交付循环反而比父直写贵
- **F3**：validation criteria 写成"质量好""结构完整"等模糊判据 — sub-agent 会"自我宣告完成"；**对策**：validation 必须可由父 agent 一行 shell/grep 命令判定（ORD-22 三类标准）
- **F4**：iteration budget 设过大（如 5+）— sub-agent 反复失败时浪费 cost；典型 budget = 2（coder）/ 1（auditor）；失败超 budget 立即 escalate
- **F5**：跳过 §Sub-agent dispatch 决策树直接 dispatch — 会把"该父直写"的 task（如 SKILL.md / 跨多文件同步）误派给 sub-agent；**对策**：每 dispatch 前 3 判据自检
- **F6**：依赖 `model:` 字段在 legacy plan 自动 dispatch — silently fallback 到父 model；**对策**：检测 plan 类型；legacy → Mode γ；usage-based → Mode α
- **F7**：用 sub-agent 写新决定（INV/ORD/EXP）— 违反 INV-04 精神（execute 层不写新决定）；**对策**：sub-agent 发现需新决定立即 abort + 回 proj-shape
- **F8**：sub-agent 产出未登记到 artifact-index.md — source of truth 分裂；后续 phase 找不到产出归属；**对策**：每次 validation 通过后立即追加登记
- **F9**：grep validation 命令在父 agent shell 中因 `grep -c` 返回非零退出而被 `set -e` 中断 — 实际 0 命中是"pass"但 shell 看成 fail；**对策**：validation 命令统一用 `$(grep -c "pattern" file 2>/dev/null || echo 0)` 兜底
- **F10**：dispatch prompt 不 self-contained — sub-agent 不知道你不知道的上下文；按 APM 原则，prompt 必须含 objective + 完整 context + reference 文件路径 + validation 自检命令
- **F11**：盲目服从——收到偏离已落盘方向/范围的指令不质疑、或用户一反驳就改口（EMNLP 2025 实证：多轮 rebuttal 诱屈服）；**对策**：按 `proj` §质疑义务（ORD-42）执行——对照 DECISIONS/plan → 偏离必质疑 / 超范围必指出 → 仅用户明示「已知情仍坚持」才服从+变更留痕；正常指令禁质疑。**对称的另一半（ORD-55）**：用户做的是**选择**（optative，无真值）时，不得反对或替换，但**必须**陈述代价 + 校验是否与 §承重事实 K 冲突 + 是否与已落盘决定/phase 范围冲突。「我不建议这么选」是越权，「这么选与 FACT-xx 冲突 / 不可满足」是义务
- **F12**：拿一句**没有出处的断言**当 dispatch 前提就往下跑（ORD-54 · r36 修订为两道闸）——sub-agent 的 prompt 里塞进「业界都是这么做的」「X 做不到 Y」而无 `FACT-xx` 支撑，错误会被 self-contained prompt **原样放大到每个 worker**，且父 agent 事后无从追溯它从哪来。**对策分两道**：**① 提出闸（严）**——父 agent **写进 dispatch prompt 之前**必须已查证该断言（「我没查」不是出口；唯一放松是结论可为 `无法判定`，但那须留痕查了什么、落 `待查证·阻塞`、**不构成放行**，只交人处置）；写进 prompt 就是**记录**，而记录本身即一次使用。**② 使用闸**——问「它为假我还会这么派吗」：不会且无 home → **停**，先要出处或由人标 `不敏感`。**来源对称**：父 agent 自己推出来的断言同样适用。**约定**：prompt 里不带出处的事实陈述一律视为未查证
- **F13**：条目区非空却跳过输出前隔离评审，或只把条目区（不搭草稿全文）交给 sub-agent（ORD-58）——漏摘正好落在父 agent 没摘进条目的那些句子上。**对策**：条目区非空即 dispatch；输入必须含草稿全文

## 触发词

proj-run · 执行调度 · sub-agent · 子代理 · subagent dispatch · model-tier · 模型分层 · model-tier.yaml · Opus 规划 · Grok 执行 · Cursor Grok · phase 执行 · dispatch manifest · validation gate · dispatch adapter · DispatchCapability · conversation-fallback · runtime 无关 · Mode α · Mode β · Mode γ · cursor agents · `.cursor/agents/` · message bus · `.apm/bus/` · APM · iteration budget · escalate · runway

## 不触发本 skill

- proj-plan 尚未输出 phase-NN/plan.md / 缺少 `## Sub-agent dispatch manifest` 段 → 回 proj-plan 先补齐
- DECISIONS / proj-shape 阶段还在进行 → 回 proj-shape
- 用户只要一次性写代码 / 改 1 文件 → 直接执行，不必走本 skill 流程
- 单 task 输出需要被父持续回溯（决策树 ✗）→ 父 agent 直写

## 模板索引

| 文档 | 模板 |
|------|------|
| Model-tier（planning / execution 默认 + 项目覆盖）| [`assets/model-tier.yaml`](assets/model-tier.yaml) |
| Dispatch manifest（5 字段闭环 · ORD-21）| [`assets/dispatch-manifest-template.md`](assets/dispatch-manifest-template.md) |
| Acceptance（validation 结果 + token cost + escalate · ORD-15 输出契约）| [`assets/acceptance-template.md`](assets/acceptance-template.md) |
| Cursor agents（Mode α · YAML frontmatter + legacy warning · ORD-19）| [`assets/cursor-agents-template.md`](assets/cursor-agents-template.md) |
| Message bus（Mode β 占位 · `.apm/bus/` · ORD-19）| [`assets/message-bus-template.md`](assets/message-bus-template.md) |
| Validation gate（3 类 · structural / lint / behavioral · ORD-22）| [`assets/validation-gate-template.md`](assets/validation-gate-template.md) |
