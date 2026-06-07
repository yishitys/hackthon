# Hackathon Product Requirements And GPT Pro Prompt

更新时间：2026-06-07

本文件把当前工作区中所有与产品设计相关的要求集中整理，来源包括：

- `README.md`
- `guidance_steps.md`
- `data/hackathon_requirements.md`
- `data/vibe_forward_competition_info.md`
- `data/hackathon_slides_ocr.md`
- `data_rescue_use_case_1.md`
- `cognee_memory_governance_summary.md`

---

# 1. 项目背景

## 1.1 黑客松信息

- 比赛名称：M-AGENTS / vibeFORWARD
- 日期：2026-06-07
- 地点：Fordham Lincoln Center, NYC
- 背景：NYC Tech Week / a16z
- 形式：1 天黑客松 build sprint
- 团队规模：4-6 人
- 核心挑战：

```text
You are given a real business crisis.
Build a multi-agent system that addresses it,
then ideate and design your own product that puts the solution
in the hands of someone who needs it.
```

## 1.2 当前建议选择的 Track

Track 01：Data Rescue

原始问题：

```text
A manufacturer's data is corrupted four days before a regulatory audit:
duplicates, unit conflicts, numbers that contradict each other.

Build any product that helps an organization find, fix, and explain broken data.
```

目标用户：

```text
Compliance officer who has never opened a database.
```

推荐产品方向：

```text
Data Rescue Copilot / Audit Copilot
```

一句话定位：

```text
用 Cognee GraphRAG 构建一个面向合规官的数据救援助手，
把损坏的制造数据转化为可追踪、可修复、可解释的审计证据图谱。
```

---

# 2. 硬性比赛要求

## 2.1 必须满足的规则

| ID | 要求 |
| --- | --- |
| R01 | 至少 4 个 agent，必须有真实 handoff，不能只是一个 LLM call 循环。 |
| R02 | Cognee 必须作为 memory layer；每个 agent 都要读 Cognee，也要写 Cognee。 |
| R03 | Trupeer 5 分钟 demo 视频是必交项；没有视频会被取消资格。 |
| R04 | Geodo research 是必做项，由 Domain Expert 在 Geodo web platform 上完成，不能写代码替代。 |
| R05 | Step 0 Product Brief 必须先写、必须提交，并且评委会按照 brief 判断产品是否完成。 |
| R06 | 数据必须是真实数据；可以自带数据，也可以用 Kaggle benchmark。使用 Kaggle benchmark 有额外可信度加分。 |
| R07 | 每个 agent 决策必须有可见理由；不能写 “the model said so”。 |
| R08 | Agent 4 的 summary 必须能从产品中下载。 |
| R09 | 团队 4-6 人，至少 1 个 Builder 和 1 个其他角色；不能 solo submission。 |
| R10 | 5:00 PM 前提交 Devpost；没有延期。 |

## 2.2 必交材料

Devpost 提交必须包含：

- Product Brief PDF
- GitHub repo link
- Trupeer video URL
- Track selection
- Written product description

Partial submissions are not accepted.

## 2.3 时间要求

- 11:00 AM：Build sprint begins，先做 Step 0 Product Brief
- 4:00 PM - 5:00 PM：Science fair，评委现场走查
- 5:00 PM：Devpost submission closes
- 5:25 PM - 6:00 PM：Top 3 live demos

产品必须在 4:00 PM 前可以让评委冷启动操作，5:00 PM 前完成提交。

---

# 3. 评分要求

总分 25 分，5 个问题，每项 5 分。

| 评分项 | 要求 |
| --- | --- |
| Agents that work | agents 必须跑在真实数据上，输出不能 hardcode。 |
| Real collaboration | Agent N+1 必须通过 Cognee 使用 Agent N 的输出。 |
| Matches your brief | 产品必须符合 Step 0 Product Brief 中自己定义的成功标准。 |
| Your end user can use it | 评委应该能在无人讲解代码的情况下冷启动使用。 |
| Explainable | 每个 decision、ranking、fix、summary 都要有证据和理由。 |

最低 15 分才有 finalist qualification。

---

# 4. 角色要求

团队至少需要 Builder + 另一个角色。推荐四类角色：

## 4.1 Builder

- 让 agents 跑起来
- 接入 Cognee
- 把 agent outputs 接到产品界面
- 保证每个 agent 读写 Cognee
- 保证真实 handoff 可见

## 4.2 Designer

- 负责 Product Brief
- 负责用户看到的一切
- 负责 Step 0 和 Step 5
- 产品必须为非技术合规官设计，而不是为工程师设计

## 4.3 Domain Expert

- 验证 agent outputs
- 写 Agent 4 narrative
- 使用 Geodo 做真实客户、公司、市场研究
- 不通过代码做 Geodo 的替代实现

## 4.4 Presenter

- 负责 demo script
- 负责 Trupeer recording
- 负责 finalist stage presentation

---

# 5. Five-Step Pipeline 要求

## Step 00 - Define

必须先写一页 Product Brief。

必须回答：

- Who is it for?
- What does it do in one sentence?
- What does success look like?
- What will the team not build?

## Step 01 - Find It

Agent 1 读取数据并发现坏数据：

- duplicates
- anomalies
- suspicious patterns
- broken records
- contradictory records

## Step 02 - Rank It

Agent 2 对 Agent 1 的发现排序：

- worst first
- 每个 ranking decision 都要有理由
- 必须从 Cognee 读取 Agent 1 的发现
- 必须把排名结果写回 Cognee

## Step 03 - Act On It

Agent 3 对问题采取动作：

- fix
- flag
- escalate

每个 action 必须有 logged reason。

## Step 04 - Explain It

Agent 4 写 human-readable summary：

- 合规官能读
- 审计员能理解
- 人类可以签字
- 必须可下载
- Domain Expert owns this step

## Step 05 - Show It

根据 Step 0 brief 做产品。

演示时必须以 end user 视角操作，不要以工程师解释代码的方式演示。

---

# 6. Mandatory Tool Stack

## 6.1 Cognee

状态：Mandatory

用途：

- 四个 agents 之间的 memory layer
- 每个 agent read/write
- 支持 graph-backed context
- 支持 handoff evidence
- 保存 findings、rankings、actions、summaries

核心要求：

```text
Memory connects everything.
Each agent recalls previous agents' work through Cognee.
```

## 6.2 Trupeer

状态：Mandatory

用途：

- 录制 5 分钟 demo video
- 视频 URL 必须提交 Devpost

## 6.3 Geodo

状态：Mandatory

用途：

- Domain Expert 做 web platform research
- 研究真实世界客户、公司、市场实体
- 只能用 Geodo web platform，不写代码替代

## 6.4 Kaggle

状态：Optional but recommended

用途：

- 使用 Track 01 Kaggle benchmark dataset
- 评委会用 hidden answer key 验证结果
- 使用 benchmark 有 bonus credibility

Track 01 Dataset:

```text
https://www.kaggle.com/datasets/quantologist/track01-vibeforward-m-agents
```

## 6.5 PyMC / PyMC Labs

状态：Optional special prize

用途：

- 让 agent outputs 带 probabilistic confidence
- 推荐输出 “94% probability” 而不是简单 “yes/no”
- 可用于风险评分、置信度、uncertainty explanation

---

# 7. 产品核心要求

## 7.1 目标用户

目标用户是：

```text
监管审计前的制造企业合规官。
```

用户特征：

- 从未打开过数据库
- 不会 SQL
- 不理解复杂表关系
- 时间紧，四天后就要审计
- 需要知道什么最危险
- 需要知道为什么危险
- 需要知道先修什么
- 需要生成审计员能读的解释

## 7.2 产品不能是什么

产品不应该只是：

- 数据清洗脚本
- 给工程师看的 SQL dashboard
- 静态报告生成器
- 单个 LLM prompt
- 只展示错误行的表格
- 没有证据链的 AI 建议

## 7.3 产品应该是什么

产品应该是：

```text
面向合规官的 Data Rescue Copilot，
把坏数据变成可解释的审计 findings，
并通过 Cognee 记住每个 agent 的证据、判断、修复建议和最终 summary。
```

核心能力：

- 上传或加载制造业审计数据
- 自动识别坏数据
- 生成 Finding 节点
- 按审计风险排序
- 提供证据链
- 给出修复、标记或升级建议
- 显示每个决定的理由
- 支持自然语言问答
- 生成可下载的审计 summary
- 展示 agent handoff 和 Cognee memory 使用

---

# 8. Data Rescue 需要检测的问题类型

必须优先覆盖至少 3 类问题，推荐覆盖更多。

## 8.1 Duplicates

例子：

- 完全重复行
- 同一批次重复导入
- 同一供应商多个名称
- 同一产品多个 ID
- 同一检查记录重复出现

## 8.2 Unit Conflicts

例子：

- kg vs lb
- Celsius vs Fahrenheit
- liters vs gallons
- mm vs inches
- ppm vs percentage

## 8.3 Contradictory Numbers

例子：

- 同一批次数量不同
- 库存数量小于已发货数量
- 发货数量大于生产数量
- 产量大于工厂产能
- 检测结果与合格状态矛盾

## 8.4 Impossible Dates

例子：

- 发货早于生产
- 检查早于批次创建
- 供应商批准晚于采购
- 产品过期后仍被标记为合格

## 8.5 Missing Evidence

例子：

- 批次缺少检查记录
- 供应商缺少批准状态
- 产品缺少规格
- 发货缺少接收确认
- 测量值缺少单位

## 8.6 Referential Integrity Issues

例子：

- shipment 引用了不存在的 batch_id
- inspection 引用了不存在的 product_id
- supplier_id 在供应商主数据中找不到

## 8.7 Status Conflicts

例子：

- 供应商同时是 approved 和 suspended
- 批次同时是 passed 和 failed
- 产品同时是 active 和 discontinued

## 8.8 Outliers

例子：

- 重量极端偏离历史范围
- 温度极端异常
- 产量远超工厂能力
- 批次数量远超产品平均值

---

# 9. Finding 对象要求

每个坏数据问题都必须变成一个可解释的 Finding，而不是只输出一条错误日志。

## 9.1 Finding 必须回答

- 哪里坏了？
- 为什么坏？
- 影响哪个实体？
- 证据来自哪里？
- 严重程度是多少？
- 是否会影响审计？
- 建议怎么修？
- 修复建议有多可信？
- 是否已经处理？

## 9.2 Finding 推荐字段

```json
{
  "finding_id": "F-001",
  "type": "Unit conflict",
  "severity": "High",
  "audit_risk": "Could fail regulatory audit",
  "affected_entities": ["Batch 1042"],
  "evidence": [
    {
      "source_file": "inventory.csv",
      "row_number": 82,
      "statement": "Batch 1042 weight = 500 kg"
    },
    {
      "source_file": "shipping.csv",
      "row_number": 19,
      "statement": "Batch 1042 weight = 500 lb"
    }
  ],
  "why_it_is_broken": "The same batch has two incompatible weight measurements with different units.",
  "suggested_fix": "Normalize weights to kg and reconcile against the shipping manifest.",
  "confidence": 0.91,
  "status": "Open"
}
```

## 9.3 Severity 要求

推荐等级：

- Critical
- High
- Medium
- Low
- Informational

评分依据：

- 是否影响监管审计
- 是否影响关键批次
- 是否涉及安全、质量、合规字段
- 是否存在多个冲突来源
- 是否缺失关键证据
- 是否无法自动修复
- 是否影响多个实体

## 9.4 Confidence 要求

每个 recommendation 应该带 confidence。

置信度来源：

- 来源系统可信度
- 是否有多个来源支持
- 是否符合业务规则
- 是否符合历史范围
- 是否只是格式问题
- 是否需要人工确认

---

# 10. Cognee GraphRAG 要求

## 10.1 Cognee 的定位

Cognee 不应只是普通数据库或简单向量搜索。

它应被定位为：

```text
AI memory + GraphRAG reasoning layer.
```

它负责：

- 记住每个事实是什么
- 记住每个事实来自哪里
- 识别哪些记录指向同一个实体
- 识别哪些事实互相矛盾
- 保存每个问题的证据链
- 支持自然语言审计问答
- 生成合规官能读懂的解释
- 连接所有 agents 的 handoff

## 10.2 推荐图谱节点

- RawRecord
- SourceFile
- Batch
- Product
- Supplier
- Facility
- Measurement
- Shipment
- Inspection
- Regulation
- Finding
- FixRecommendation
- AuditReport

## 10.3 推荐图谱关系

- Batch -> produced_at -> Facility
- Batch -> has_product -> Product
- Batch -> supplied_by -> Supplier
- Batch -> has_measurement -> Measurement
- Batch -> has_shipment -> Shipment
- Batch -> inspected_by -> Inspection
- Measurement -> came_from -> SourceFile
- Measurement -> has_unit -> Unit
- Measurement -> conflicts_with -> Measurement
- Record -> came_from -> SourceFile
- Finding -> affects -> Batch
- Finding -> supported_by -> Record
- Finding -> recommends -> FixRecommendation
- FixRecommendation -> justified_by -> Evidence
- AuditReport -> includes -> Finding

## 10.4 Agent handoff memory 要求

每个 agent 必须：

1. 从 Cognee 读取前序上下文。
2. 执行自己的任务。
3. 把输出写回 Cognee。
4. 输出内容必须包含 evidence/reason。
5. UI 或 demo 中要能看出 Agent N+1 使用了 Agent N 的结果。

---

# 11. 推荐 4-Agent 架构

为了符合比赛规则，产品至少要有 4 个清晰 agent。可以内部有更多 submodules，但对评委展示时必须清楚地展示这 4 个角色。

## Agent 1 - Data Detective / Find It Agent

职责：

- 读取真实数据
- 解析原始记录
- 识别 duplicates、unit conflicts、contradictions、missing evidence 等问题
- 生成初始 findings
- 写入 Cognee

输出：

- RawRecord memory
- SourceFile memory
- Initial Finding candidates
- Evidence links

## Agent 2 - Risk Prioritizer / Rank It Agent

职责：

- 从 Cognee 读取 Agent 1 的 findings
- 按审计风险排序
- 解释 ranking reasons
- 给出 severity 和 confidence
- 写回 Cognee

输出：

- Ranked Findings
- Severity
- Audit impact
- Ranking rationale

## Agent 3 - Remediation Planner / Act On It Agent

职责：

- 从 Cognee 读取 ranked findings
- 决定 fix、flag 或 escalate
- 区分 safe auto-fix、suggested fix、manual review
- 给出 action reason
- 写回 Cognee

输出：

- Remediation actions
- Fix suggestions
- Manual review queue
- Before/after preview
- Action rationale

## Agent 4 - Audit Narrator / Explain It Agent

职责：

- 从 Cognee 读取 findings、rankings、actions 和 evidence
- 生成合规官和审计员可读 summary
- 生成可下载报告
- 保证每个结论都有证据链
- 写回 Cognee

输出：

- Human-readable audit summary
- Downloadable report
- Executive summary
- Evidence-backed explanations

---

# 12. Memory Governance / LINT 要求

当前项目还整理了一个 Memory Governance Layer 方向，可作为产品差异化或架构亮点。

一句话：

```text
Cognee gives agents memory; our LINT layer decides what deserves to become memory.
```

推荐原则：

- 不要把所有 agent 输出直接写入长期记忆。
- runtime trace 先进入 session memory 或 raw trace。
- 只有通过 LINT 的高价值内容才进入 permanent graph memory。
- final answer 不是事实源，只能作为 episode trace。
- 每条长期记忆必须有 source、scope、time、confidence、status。
- 冲突不直接覆盖旧记忆；应该标记 superseded 或 conflict group。

LINT 检查项：

- provenance
- value
- conflict
- freshness
- privacy
- scope
- evidence strength
- contradiction risk

推荐 memory 状态：

- candidate
- active
- rejected
- superseded
- expired
- conflict

如果时间不足，LINT 可以作为 demo 中的解释层，而不是完整实现。

---

# 13. UI / UX 要求

## 13.1 设计原则

目标用户不是工程师，所以 UI 必须：

- 不要求 SQL
- 不暴露复杂数据库概念
- 第一屏就显示审计风险
- 能让评委冷启动操作
- 每个建议都有原因
- 每个 finding 都能展开证据链
- 报告能下载

## 13.2 推荐页面

### Audit Risk Dashboard

第一屏显示：

- Overall Audit Risk
- Total Findings
- Critical / High / Medium / Low counts
- Top 5 urgent issues
- Agent pipeline status
- Report download button

### Findings List

字段：

- Finding ID
- Severity
- Type
- Affected Entity
- Audit Impact
- Confidence
- Status
- Recommended Action

### Evidence View

点击 Finding 后展示：

- Problem
- Why it matters
- Evidence source rows
- Conflicting records
- Suggested fix
- Confidence
- Agent handoff trace

### Natural Language Chat

合规官可以问：

- Which issues could fail the audit?
- Why is Batch 1042 risky?
- What should I fix first?
- Which issues require manual confirmation?
- Generate an explanation for the auditor.

### Audit Report Generator

必须支持下载 Agent 4 summary。

报告内容：

- audit risk overview
- high-risk findings
- evidence
- recommended fixes
- open risks
- resolved risks
- human-readable auditor explanation

## 13.3 UI 不应该做什么

- 不要把产品做成工程师调试台
- 不要让用户读 raw logs
- 不要要求用户理解 Cognee 内部实现
- 不要只展示 JSON
- 不要只做聊天界面而没有 dashboard 和 downloadable summary

---

# 14. 修复策略要求

产品不能盲目改审计数据。修复必须分级。

## 14.1 Safe Auto-Fix

可以自动处理：

- 大小写不一致
- 空格问题
- 日期格式统一
- 单位标准写法统一
- 明显重复导入

## 14.2 Suggested Fix

系统建议，人类确认：

- 单位换算
- 数值冲突
- 供应商状态冲突
- 缺失检查记录

## 14.3 Manual Review Required

必须人工处理：

- 发货早于生产
- 检查记录缺失
- 供应商暂停但仍关联活跃批次
- 多个来源互相矛盾
- 没有足够证据判断正确值

---

# 15. MVP 范围

如果时间有限，MVP 应优先做：

1. 使用 Track 01 Kaggle 数据或其他真实制造数据。
2. 至少 4 个 agents。
3. Agent 1 检测 3 类问题：
   - duplicates
   - unit conflicts
   - contradictory numbers
4. Agent 2 排序并解释 severity。
5. Agent 3 给出 fix/flag/escalate。
6. Agent 4 生成可下载 summary。
7. 每个 agent 读写 Cognee。
8. UI 显示 dashboard、findings、evidence、report download。
9. 每个 decision 都有 visible reason。
10. Demo 中展示 Agent N+1 使用 Agent N 的 Cognee memory。

---

# 16. Stretch Goals

有余力可以加：

- Graph visualization
- Natural language audit Q&A
- Fix simulation
- PDF / Markdown / CSV / Excel export
- PyMC confidence modeling
- Geodo market/company research summary integrated into product brief
- Memory Governance / LINT conflict view
- Historical audit memory across multiple cycles

---

# 17. 推荐 Demo Story

```text
四天后就是监管审计。
制造商发现多个系统中的批次数据互相矛盾。

合规官不会写 SQL，也没有时间手动检查所有表。

她打开 Data Rescue Copilot，上传 Track 01 制造数据。

Agent 1 读取真实数据，发现重复记录、单位冲突、缺失检查记录和日期矛盾，并把 findings 写入 Cognee。

Agent 2 从 Cognee 读取 findings，按审计风险排序，解释为什么 missing inspection records 和 impossible dates 排在最前。

Agent 3 从 Cognee 读取 ranked findings，决定哪些可以安全修复，哪些需要人工确认，哪些必须升级处理。

Agent 4 从 Cognee 读取完整证据链，生成一份合规官和审计员都能读的 audit summary。

合规官点击最高风险问题，看到来源文件、行号、冲突值、原因、建议动作和置信度。

最后，她点击 Download Report，导出 Agent 4 的审计准备报告。
```

---

# 18. GPT Pro 产品设计提示词

下面这段可以直接复制给 GPT Pro：

```text
你是一个顶级 AI 产品设计负责人、黑客松导师和 B2B SaaS 产品架构师。请基于下面的约束，为我们设计一个可以在 1 天黑客松中完成、但看起来像完整产品的 multi-agent 产品。

比赛背景：
- 比赛是 M-AGENTS / vibeFORWARD，2026-06-07，1 天黑客松。
- 核心挑战：给定真实 business crisis，构建一个 multi-agent system 解决问题，并设计一个真实 end user 能使用的产品。
- 我们选择 Track 01：Data Rescue。
- Track 01 问题：制造商在监管审计前四天发现数据损坏，包括 duplicates、unit conflicts、numbers that contradict each other。需要构建一个产品帮助组织 find, fix, and explain broken data。
- 目标用户：从未打开过数据库的 compliance officer。

硬性规则：
- 至少 4 个 agents，必须有真实 handoffs，不能只是一个 LLM call 循环。
- Cognee 必须作为 memory layer；每个 agent 都要从 Cognee 读取，也要写入 Cognee。
- Agent N+1 必须通过 Cognee 使用 Agent N 的输出。
- 每个 agent decision、ranking、fix、summary 都必须有 visible reason 和 evidence，不能说 “the model said so”。
- Agent 4 的 summary 必须能从产品中下载。
- 必须做 Step 0 Product Brief，并且评委会按照 brief 判断产品是否完成。
- 产品必须跑在真实数据上；可以使用 Kaggle Track 01 benchmark dataset，使用 benchmark 有 bonus credibility。
- 必须有 Trupeer 5 分钟 demo video。
- 必须有 Geodo research，由 Domain Expert 在 Geodo web platform 上完成，用于真实客户、公司、市场研究。
- Devpost 5:00 PM 前提交，包含 Product Brief PDF、GitHub repo、Trupeer URL、track selection、written product description。

评分标准：
- Agents that work：agents 跑在真实数据上，输出不能 hardcode。
- Real collaboration：Agent N+1 通过 Cognee 使用 Agent N 的发现。
- Matches your brief：产品符合 Step 0 brief 中定义的成功标准。
- End user can use it：评委可以 cold operate 产品。
- Explainable：每个决定都有可见理由和证据。

我们希望设计的产品方向：
- 产品名可以是 Data Rescue Copilot / Audit Copilot，也可以重新命名。
- 面向制造业合规官，在审计前帮助其发现、排序、处理、解释坏数据。
- 不要做成工程师数据清洗工具；要做成非技术合规官可以使用的审计风险产品。
- 核心价值：把错误行变成可解释、可追踪、可处理的 audit findings。

必须设计 4 个 agents：
1. Agent 1 - Find It / Data Detective：读取真实数据，发现 duplicates、unit conflicts、contradictory numbers、missing evidence 等问题，输出 initial findings 和 evidence，写入 Cognee。
2. Agent 2 - Rank It / Risk Prioritizer：从 Cognee 读取 Agent 1 findings，按 audit risk 排序，给出 severity、confidence、ranking reasons，写入 Cognee。
3. Agent 3 - Act On It / Remediation Planner：从 Cognee 读取 ranked findings，决定 fix、flag、escalate，区分 safe auto-fix、suggested fix、manual review，给出 action rationale，写入 Cognee。
4. Agent 4 - Explain It / Audit Narrator：从 Cognee 读取 findings、rankings、actions、evidence，生成 human-readable audit summary，必须可下载，写入 Cognee。

产品需要检测的问题类型：
- duplicate records
- unit conflicts，比如 kg vs lb、Celsius vs Fahrenheit
- contradictory numbers，比如 shipped quantity > produced quantity
- impossible dates，比如 shipped_at < produced_at
- missing evidence，比如 regulated batch 缺少 inspection record
- referential integrity issues，比如 shipment 引用不存在的 batch_id
- status conflicts，比如 supplier 同时 approved 和 suspended
- outliers，比如重量极端偏离历史范围

每个 Finding 应包含：
- finding_id
- type
- severity
- audit_risk
- affected_entities
- evidence，包括 source_file、row_number、statement
- why_it_is_broken
- recommended_action 或 suggested_fix
- confidence
- status
- agent handoff trace

Cognee GraphRAG 应体现：
- RawRecord、SourceFile、Batch、Product、Supplier、Facility、Measurement、Shipment、Inspection、Finding、FixRecommendation、AuditReport 等节点。
- Finding -> supported_by -> Record。
- Finding -> affects -> Batch/Supplier/Product。
- Finding -> recommends -> FixRecommendation。
- AuditReport -> includes -> Finding。
- 每个 agent 的输出都成为后续 agent 的可召回 memory。

UI 要求：
- 第一屏是 Audit Risk Dashboard，不是 landing page。
- 必须让合规官一眼看到 overall risk、critical/high/medium/low findings、top urgent issues。
- 有 Findings List，可以按 severity、type、status、confidence 过滤或排序。
- 有 Evidence View，展示为什么某个 finding 被标记、来源文件/行号/冲突值、为什么重要、建议怎么处理。
- 有 Agent Handoff / Memory Trace，让评委看到 Agent 2/3/4 如何使用 Cognee 中 Agent 1/2/3 的输出。
- 有 Natural Language Q&A，支持问 “What should I fix first?”、“Why is Batch 1042 risky?”、“Generate an explanation for the auditor.”
- 有 Report Generator 和 Download Report 按钮，导出 Agent 4 summary。
- UI 面向非技术用户，不展示 SQL，不要求理解数据库，不把重点放在 JSON/logs 上。

请你输出：
1. 产品名称和一句话定位。
2. Step 0 Product Brief，一页以内，包括 who is it for、one-sentence product、success criteria、what we will not build。
3. 核心用户流程，从上传数据到下载报告。
4. 4-agent system design，说明每个 agent 的 input、task、Cognee read、Cognee write、output、visible reason。
5. Cognee memory / graph design，说明节点、关系、handoff 方式。
6. MVP 功能清单，按必须做、应该做、可选增强分级。
7. UI 信息架构，包含主要页面、每页关键组件、第一屏布局建议。
8. 一套 5 分钟 Trupeer demo script，按分钟拆分，突出评分标准。
9. Devpost written product description 草稿。
10. 评委可能问的问题和回答。
11. 如果时间只有 3 小时，应该砍掉什么、保留什么。

请非常具体，输出可以直接给 Builder、Designer、Domain Expert、Presenter 分工执行。不要只讲概念，要给出可以实现和演示的产品设计。
```

