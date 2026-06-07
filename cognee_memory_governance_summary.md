# Cognee Memory Governance Layer 调研总结

## 一句话结论

这个 hackathon 项目不应该只做“把 Cognee 接进 Claude/Agent”的集成 demo，而应该做一个 **Memory Governance Layer**：Cognee 负责提供 agent memory engine，项目里的 LINT 层负责判断什么值得被记住、什么时候召回、什么时候遗忘、发生冲突时如何治理。

核心卖点可以概括为：

> Cognee gives agents memory; our LINT layer decides what deserves to become memory.

## 项目判断

文本认为，真正有价值的方向是让 Agent 拥有可治理的长期记忆，而不是把所有聊天记录或工具结果直接写入向量库。

Cognee 适合作为底层 memory engine，因为它支持跨 session 的 durable memory、实体关系抽取、provenance、graph/vector/relational store 结合，以及 Claude Code、LangGraph、OpenClaw、MCP 等生态集成。

但 Cognee 本身不应该直接决定所有信息都永久沉淀。项目应在 Cognee 之上加入：

- 记忆准入
- 召回路由
- 冲突治理
- 版本控制
- provenance 与 evidence 管理
- 过期、遗忘和反馈机制

## 调研关键结论

Cognee v1.0 的主要接口包括：

- `remember`：写入永久 graph memory，或带 `session_id` 写入 session memory
- `recall`：做 session-aware retrieval，并自动选择 retrieval strategy
- `improve`：enrich graph、应用 feedback、把 session memory bridge 到永久 graph
- `forget`：删除 item、dataset，或进行 memory-only reset

OpenClaw 和 Claude Code 的 Cognee 集成给出的启发是：项目文档和 wiki 应该是 **file-backed、hash-based、可 diff** 的，而不是只存在数据库里的黑盒 memory。

文本也指出一个工程风险：Cognee GitHub issue 中有人报告 `remember(session_id=...)` 通过 HTTP/MCP 路径时可能返回 `session_stored`，但实际没有写入 Redis/session records。因此 hackathon demo 中建议：

- session 写入优先使用 Python SDK
- 如果使用 MCP/HTTP，需要先做 smoke test，验证 session 写入后确实能被召回

## 顶层架构

推荐把 Cognee 定位为记忆引擎，把 LINT 定位为记忆治理层。

```text
Sources / Runtime Events
        ↓
Raw Trace Store
        ↓
Session Memory: fast, temporary, scoped by session_id
        ↓
Memory Candidate Extractor
        ↓
LINT: provenance / value / conflict / freshness / privacy / scope
        ↓
Permanent Cognee Graph Memory
        ↓
Recall Router: session → project → user → agent → org/global
        ↓
Answer with cited memory + feedback
        ↓
Improve / reweight / supersede / forget
```

关键原则是：**不要让 Agent 直接把所有输出写进长期记忆**。

普通 runtime 信息应先进入 session memory 或 raw event log，再经过 LINT 生成候选记忆。只有通过规则检查的高价值内容，才进入 permanent graph memory。

## 什么应该被记住

文本建议把 memory 分为 8 类，并为不同类型设置不同的准入门槛：

| 记忆类型 | 示例 | 推荐处理 |
| --- | --- | --- |
| 项目源事实 | README、架构文档、API docs、ADR、issue、repo 文件 | 可直接 hash-based ingest |
| 关键决策 | 技术选型、架构取舍、可靠性判断 | 需要 LINT 或用户确认 |
| 用户/团队偏好 | 回答语言、输出格式、工程偏好 | 明确表达才写入 |
| 工具调用结果摘要 | 测试结果、命令报错、API 返回结构 | 默认只进 session trace |
| 成功案例 | bug 修复步骤、有效 query strategy | LINT 后写入 |
| 失败/反例 | 当前环境下会失败的命令或策略 | 存成 failure case，不当作永久事实 |
| final answer 摘要 | 用户问题、最终结论、sources、是否被接受 | 只作为 episode trace |
| 召回反馈 | 用户纠错、点赞、命中情况 | 用于 reweight，不直接变成事实 |

最重要的一点是：**final answer 不是事实源**。它只能作为 episode trace；其中稳定的结论、决策、偏好、成功模式，需要单独抽取并带上 source、evidence、confidence、scope 后，才能成为长期记忆。

## 候选记忆 Schema

建议每条候选记忆采用统一 schema：

```json
{
  "memory_id": "...",
  "type": "project_fact | decision | preference | tool_case | failure_case | episode_summary | skill_rule",
  "scope": "session | user | project | agent | team | org",
  "claim": "要沉淀的最小原子事实或规则",
  "source": {
    "kind": "file | user_statement | tool_result | final_answer | external_doc",
    "uri": "...",
    "content_hash": "...",
    "created_at": "...",
    "observed_at": "..."
  },
  "evidence": ["source_id_or_chunk_id"],
  "confidence": 0.0,
  "status": "candidate | active | rejected | superseded | expired | conflict",
  "valid_from": "...",
  "valid_until": null,
  "supersedes": [],
  "conflicts_with": [],
  "ttl_policy": "none | verify_before_use | expire_after_7d",
  "privacy_level": "public | project | user_private | secret_blocked"
}
```

## 什么时候写入记忆

文本强调：**不是每次回答后都直接写长期记忆**。应区分实时记录和延迟沉淀。

| 时机 | 动作 | 写入位置 |
| --- | --- | --- |
| `SessionStart` | 建 session skeleton，记录 repo、branch、commit、用户、项目，扫描 docs hash 变化 | raw trace / source dataset |
| `UserPromptSubmit` | 记录用户请求，抽取显式偏好，触发 recall routing | session memory |
| `PreToolUse` | 召回工具规则、危险命令、项目约束 | audit trace 或不写 |
| `PostToolUse` | 记录工具调用摘要、exit status、关键输出、测试结果 | session trace |
| `Stop` | 生成 answer summary、candidate memories、decision candidates、failure cases | candidate queue |
| `PreCompact` | flush 当前任务状态、未完成事项、关键上下文 | session summary |
| `SessionEnd` | 运行 LINT，promote approved memories，调用 Cognee improve，生成 memory diff report | permanent graph |

长期记忆准入可用 scoring gate：

```text
promotion_score =
  reuse_value
+ stability
+ evidence_strength
+ user_explicitness
+ project_relevance
- volatility
- sensitivity
- contradiction_risk
- duplication_penalty
```

建议阈值：

| 分数 | 动作 |
| ---: | --- |
| ≥ 0.75 | promote 到 permanent graph |
| 0.45-0.75 | 留在 candidate，需要更多 evidence 或用户确认 |
| < 0.45 | 只保留 session trace，TTL 过期 |
| 有 conflict | 进入 conflict group，不自动覆盖旧记忆 |
| 有 secret/PII 风险 | block 或 redact，不进入 Cognee |

## 什么时候召回记忆

结论是：**每个 prompt 都可以做轻量 recall decision，但不要每次全量召回**。

推荐策略：

1. `SessionStart` 只加载极小的 project card：项目目标、当前 repo、最近决策、未完成任务。
2. `UserPromptSubmit` 做 query classification，判断是否需要项目记忆、用户偏好、工具规则、历史失败案例。
3. 简单问答或闲聊不召回。
4. 涉及“继续、刚才、项目、代码、文档、工具、bug、决策、偏好”时召回。
5. 复杂任务分层召回：session → project → user → agent skills → team/org。
6. 每个 scope 取 `top_k=3-5`，总注入上下文控制在模型窗口的 15%-25%。
7. 注入给 agent 的 memory context 必须包含 source、scope、confidence、status、是否 conflict、是否 stale。

推荐 recall scope 顺序：

```text
current_session
  → current_project
  → current_user_preferences
  → current_agent_skills
  → team/org shared memory
  → external docs / web only if needed
```

## 如何避免记忆污染

文本将记忆污染分为五类：

| 污染来源 | 风险 | 处理方式 |
| --- | --- | --- |
| 错误答案 | Agent hallucination 被长期化 | final answer 只作为 episode，不直接变事实 |
| 过时信息 | 老版本 API、旧 branch、旧需求 | memory 带 `valid_from`、`valid_until`、`source_hash` |
| 临时猜测 | “可能是因为...” 被当作事实 | speculative memory 默认 rejected 或 TTL |
| 用户后来推翻 | 旧偏好/旧决策仍被召回 | 新 memory supersedes 旧 memory |
| 工具失败结果 | “命令失败” 被理解成“永远不能用” | 存成 environment-specific failure case |

LINT pipeline 包括：

1. Normalize：把 session summary 拆成最小 claim、relation、rule。
2. Source Check：每条 claim 必须有 source。
3. Value Check：判断未来复用价值、稳定性和作用域。
4. Conflict Check：召回相同 subject/entity/relation，识别 contradiction 或 supersede。
5. Freshness Check：动态信息加 TTL，过期信息召回时标记 verify_before_use。
6. Privacy Check：API key、token、个人敏感信息和 secret 直接 block/redact。
7. Promote / Reject / Quarantine：只把 active memory 写入 permanent graph。
8. Feedback Update：用户纠错时降低相关 memory 权重，必要时 supersede 或 forget。

## 冲突和版本处理

文本建议采用 **append-only event log + active view**，不要简单覆盖旧记忆。

```text
new memory candidate
  ↓
same entity/relation/scope?
  ↓
yes → compare source authority, recency, evidence, status
  ↓
if compatible → merge/elevate confidence
if conflicting → create conflict_group
if clearly newer/authoritative → mark old as superseded
if uncertain → keep both, recall 时提示 conflict
```

推荐 source authority 优先级：

```text
用户明确纠正
> 项目 ADR / repo 当前代码 / 测试结果
> 官方项目文档 / issue tracker
> 工具调用结果
> agent final answer
> agent 推测
```

Memory 状态机：

```text
candidate
  → active
  → superseded
  → expired
  → rejected
  → conflict
```

`forget()` 适合删除 dataset、data item、graph/vector memory 或做 memory-only reset，但不应作为唯一的版本管理方式。冲突治理更适合保留旧 memory，并标记为 `superseded` 或 `conflict`。

## 当前项目建议用法

推荐 datasets：

```text
project:{project_id}:source          # 原始项目文档、repo docs、slides、README、ADR
project:{project_id}:decisions       # 通过 LINT 的关键决策
project:{project_id}:cases           # 成功/失败案例、debug pattern
user:{user_id}:preferences           # 用户偏好
agent:{agent_id}:skills              # agent 自我改进出的技能、工具规则
session:{session_id}                 # 短期 session memory，不直接长期化
org:{org_id}:shared                  # 可选，团队共享知识
```

推荐写入方式：

```python
# 项目源文档：可以直接写 permanent，但要带 source hash / path / commit metadata
await cognee.remember(
    data=project_doc_text_or_path,
    dataset_name=f"project:{project_id}:source",
    self_improvement=False
)

# session runtime：只写 session，不自动 bridge
await cognee.remember(
    data=session_note,
    dataset_name=f"project:{project_id}:session",
    session_id=session_id,
    self_improvement=False
)

# LINT 通过后的候选记忆：写 permanent
await cognee.remember(
    data=approved_memory_text,
    dataset_name=f"project:{project_id}:decisions",
    self_improvement=True
)

# 定期 enrich 已批准的 graph
await cognee.improve(
    dataset=f"project:{project_id}:decisions"
)
```

推荐召回方式：

```python
session_context = await cognee.recall(
    query_text=user_prompt,
    session_id=session_id,
    top_k=3
)

project_context = await cognee.recall(
    query_text=user_prompt,
    datasets=[f"project:{project_id}:source", f"project:{project_id}:decisions"],
    top_k=5
)

prefs = await cognee.recall(
    query_text="relevant user preferences for this task",
    datasets=[f"user:{user_id}:preferences"],
    top_k=3
)
```

## Hackathon MVP 展示场景

文本建议 demo 不要只展示“记住一句话”，而要展示四个治理场景：

1. **项目文档记忆**  
   上传或扫描项目 docs。Agent 回答架构问题时能说明模块关系，并给出来源。

2. **用户偏好记忆**  
   用户说“之后回答都用中文并给出工程化方案”。新 session 中仍能召回，但只在相关任务注入，不污染所有 prompt。

3. **失败案例记忆**  
   某工具调用失败后，不把失败当成永久事实，而是存成当前环境/版本/命令下的 anti-pattern。

4. **冲突与版本 LINT**  
   旧方案是“用 MCP 写 session”，后续 issue 或测试发现 HTTP/MCP session 写入不可靠。系统不删除旧记忆，而是生成 conflict group：旧方案 superseded，新方案 active，并解释依据。

这四个场景分别对应 slides 中的 **Ingest、Query + Self Improve、Lint**，也能体现 Cognee 的 graph、vector、provenance、feedback 和 version/lint 价值。

## 最重要的设计决策

1. 长期记忆只存 LINT 后的高价值内容。
2. Session memory 是工作区，不是长期知识库。
3. Tool results 和 final answer 只作为 evidence/episode，不直接作为 truth。
4. Cognee 的 `improve()` 用于 enrichment 和 feedback weighting，不代替治理。
5. 所有 memory 必须带 source、scope、time、confidence、status。
6. 冲突不覆盖，先进入 conflict group，再生成 supersede/active view。
7. 召回按 scope 和任务路由，不做每轮全量注入。
8. 项目 wiki 应该 file-backed、hash-based、可 diff，并由 Cognee 提供 graph recall。

## 原文引用来源

- Cognee: https://www.cognee.ai/
- Cognee Overview: https://docs.cognee.ai/core-concepts/overview
- OpenClaw Integration: https://docs.cognee.ai/integrations/openclaw-integration
- Claude Code Integration: https://docs.cognee.ai/cognee-mcp/integrations/claude-code
- Cognee GitHub Issue 2888: https://github.com/topoteretes/cognee/issues/2888
- Cognee Remember: https://docs.cognee.ai/core-concepts/main-operations/remember
- Claude Code Hooks: https://code.claude.com/docs/en/hooks
- Cognee Recall: https://docs.cognee.ai/core-concepts/main-operations/recall
- Cognee Search: https://docs.cognee.ai/core-concepts/main-operations/legacy-operations/search
- Cognee Improve: https://docs.cognee.ai/core-concepts/main-operations/improve
- Cognee Forget: https://docs.cognee.ai/core-concepts/main-operations/forget
- Cognee MCP Tools: https://docs.cognee.ai/cognee-mcp/mcp-tools
