下面是 **Use Case 1：DATA RESCUE 数据救援** 的完整整理，基于前面对话，把业务背景、用户、数据、Cognee GraphRAG 的角色、建图方式、检测逻辑、产品形态、技术架构和黑客松实现路径全部串起来。

---

# Use Case 1：DATA RESCUE 数据救援

## 1. 场景定义

### 原始挑战描述

制造商在监管审计前四天发现数据出了严重问题：

```text
A manufacturer's data is corrupted four days before a regulatory audit —
duplicates, unit conflicts, numbers that contradict each other.
Build any product that helps an organization find, fix, and explain broken data.
```

也就是说，这不是一个普通的数据清洗任务，而是一个**审计前紧急数据救援场景**。

企业面对的问题包括：

```text
数据重复
单位冲突
数值矛盾
来源不一致
字段缺失
记录无法解释
审计证据链断裂
```

黑客松参赛者需要构建一个产品，帮助组织：

```text
find broken data     找出坏数据
fix broken data      修复坏数据
explain broken data  解释坏数据为什么坏、为什么这样修
```

---

# 2. 目标用户画像

## End User Archetype

Use Case 1 的最终用户是：

```text
合规官 / Compliance Officer
```

关键特征：

```text
从未打开过数据库
不会写 SQL
不懂数据表之间的关系
面对审计压力极大
需要快速知道哪些数据会导致审计失败
需要能向审计员解释数据问题和修复过程
```

所以这个产品不能只是一个给数据工程师看的数据质量工具。

它必须服务于一个非技术用户，让对方可以用自然语言问：

```text
哪些问题最可能导致审计失败？
这个批次为什么有风险？
这条数据为什么被修改？
这个修复建议的证据是什么？
能不能生成一份给审计员看的解释？
```

---

# 3. 核心产品目标

Use Case 1 的产品目标可以总结为一句话：

> 把混乱、重复、冲突的制造数据，转化为合规官能理解、能修复、能向审计员解释的审计证据图谱。

这个产品不只是做数据清洗，而是做：

```text
数据理解
实体识别
冲突检测
证据追踪
修复建议
审计解释
自然语言问答
```

---

# 4. Kaggle 数据集定位

前面对话中提到的 Use Case 1 数据集是：

```text
Track 01：Data Rescue
Kaggle dataset: track01-vibeforward-m-agents
```

这个数据集应该被看作是：

```text
broken evidence corpus
```

也就是一组“有问题的证据数据”。

在 Cognee 中，不应该只是把它当作 CSV 表格来查询，而应该把它变成一个可以推理的 GraphRAG 记忆系统。

需要注意的是：我们前面对话没有逐列检查 Kaggle 数据集的真实字段，因此下面的字段设计是**适配方案**，实际实现时需要根据下载后的 CSV / JSON / 表格字段做映射。

---

# 5. Cognee 在 Use Case 1 中的核心角色

Cognee 在这个场景里不应该被定位为：

```text
普通数据库
简单搜索工具
单纯向量数据库
普通 BI 仪表盘
```

而应该被定位为：

```text
AI memory + GraphRAG reasoning layer
```

也就是：

> Cognee 是一个记忆和推理层，负责把分散的数据事实连接起来，发现冲突，保存证据来源，并生成可解释的结论。

它的核心价值是：

```text
记住每个事实是什么
记住每个事实来自哪里
识别哪些记录指向同一个实体
识别哪些事实互相矛盾
保存每个问题的证据链
支持自然语言审计问答
生成合规官能读懂的解释
```

---

# 6. 为什么 Use Case 1 适合 GraphRAG

传统数据库适合回答：

```text
Batch 1042 的重量是多少？
```

但 Data Rescue 真正的问题是：

```text
为什么 Batch 1042 有三个不同重量？
哪个重量更可信？
这些重量分别来自哪些系统？
它们是否单位不同？
是否有一个值是重复导入造成的？
这会不会影响审计？
我应该怎么解释给审计员？
```

这些问题不是单表查询，而是**跨数据源、跨实体、跨证据链的推理问题**。

GraphRAG 适合这个场景，因为它可以同时利用：

```text
Graph：实体和关系
RAG：原始文本 / 表格 / 记录检索
Memory：历史发现、修复建议、审计解释
LLM：自然语言总结和推理
```

---

# 7. Use Case 1 的核心数据对象

在 Cognee 中，建议把 Kaggle 数据拆成多种节点。

## 7.1 原始记录节点

每一行 CSV / JSON / 表格数据都应该先作为一个原始记录进入 Cognee。

建议字段：

```text
record_id
source_file
source_table
row_number
column_name
raw_value
normalized_value
unit
timestamp
import_time
entity_type
entity_id_candidate
confidence
```

示例：

```json
{
  "record_id": "inventory_csv_row_82_weight",
  "source_file": "inventory.csv",
  "row_number": 82,
  "entity_type": "Batch",
  "entity_id_candidate": "Batch 1042",
  "field_name": "weight",
  "raw_value": "500 kg",
  "normalized_value": 500,
  "unit": "kg"
}
```

---

## 7.2 业务实体节点

根据制造业数据场景，可以建立这些实体：

```text
Batch              批次
Product            产品
Supplier           供应商
Facility           工厂 / 生产设施
Shipment           发货记录
Measurement        测量值
Inspection         检查记录
Regulation         法规 / 合规要求
Audit Finding      审计发现
Source File        数据来源文件
System             源系统
User               操作用户
Timestamp          时间点
```

---

# 8. 推荐知识图谱结构

## 8.1 核心节点

```text
Batch
Product
Supplier
Facility
Measurement
Shipment
Inspection
Regulation
Finding
Source
FixRecommendation
AuditReport
```

---

## 8.2 核心关系

建议在 Cognee GraphRAG 中建立以下关系：

```text
Batch -> produced_at -> Facility
Batch -> has_product -> Product
Batch -> supplied_by -> Supplier
Batch -> has_measurement -> Measurement
Batch -> has_shipment -> Shipment
Batch -> inspected_by -> Inspection
Measurement -> came_from -> Source File
Measurement -> has_unit -> Unit
Measurement -> measured_at -> Timestamp
Measurement -> conflicts_with -> Measurement
Record -> came_from -> Source File
Finding -> affects -> Batch
Finding -> supported_by -> Record
Finding -> recommends -> FixRecommendation
FixRecommendation -> justified_by -> Evidence
AuditReport -> includes -> Finding
```

---

## 8.3 简化图谱示例

假设数据中出现了这样的情况：

```text
inventory.csv: Batch A weight = 500 kg
shipping.csv: Batch A weight = 500 lb
sensor_log.csv: Batch A weight = 498 kg
```

在 Cognee 中可以表示为：

```text
Batch A
  -> has_measurement -> Measurement 1
  -> has_measurement -> Measurement 2
  -> has_measurement -> Measurement 3

Measurement 1
  -> value -> 500
  -> unit -> kg
  -> came_from -> inventory.csv row 82

Measurement 2
  -> value -> 500
  -> unit -> lb
  -> came_from -> shipping.csv row 19

Measurement 3
  -> value -> 498
  -> unit -> kg
  -> came_from -> sensor_log.csv row 44

Measurement 1
  -> conflicts_with -> Measurement 2

Finding 001
  -> type -> Unit conflict
  -> affects -> Batch A
  -> supported_by -> Measurement 1
  -> supported_by -> Measurement 2
  -> recommends -> Convert and reconcile units
```

---

# 9. 需要检测的数据问题类型

Use Case 1 重点是“坏数据”。建议把坏数据分成以下类别。

---

## 9.1 重复数据 Duplicates

### 问题形式

```text
完全重复行
同一批次重复导入
同一供应商有多个名称
同一产品有多个 ID
同一检查记录出现两次
```

### 示例

```text
Supplier ABC Inc.
ABC Incorporated
A.B.C. Inc
```

它们可能都是同一个供应商。

### Cognee 的作用

Cognee 可以通过实体解析建立：

```text
Supplier ABC Inc.
  -> same_as -> ABC Incorporated
  -> same_as -> A.B.C. Inc
```

然后生成发现：

```text
Finding:
  type: Duplicate supplier
  severity: Medium
  affected_entity: Supplier ABC
  evidence:
    - supplier_master.csv row 12
    - procurement.csv row 48
    - inspection.csv row 103
  suggested_fix:
    - Merge supplier aliases into canonical supplier record
```

---

## 9.2 单位冲突 Unit Conflicts

### 问题形式

```text
kg 和 lb 混用
Celsius 和 Fahrenheit 混用
liters 和 gallons 混用
mm 和 inches 混用
ppm 和 percentage 混用
```

### 示例

```text
Batch 1042 weight = 500 kg
Batch 1042 weight = 500 lb
```

两个值表面都是 500，但含义完全不同。

### Cognee 的作用

Cognee 可以：

```text
识别 measurement 类型
识别 unit
做单位标准化
把原始值和标准值都保存
检测转换后是否仍冲突
保留来源证据
```

示例 Finding：

```json
{
  "finding_id": "F-UNIT-001",
  "type": "Unit conflict",
  "severity": "High",
  "affected_entity": "Batch 1042",
  "evidence": [
    "inventory.csv row 82 says 500 kg",
    "shipping.csv row 19 says 500 lb"
  ],
  "suggested_fix": "Convert all weight measurements to kg and reconcile with shipping manifest.",
  "confidence": 0.91
}
```

---

## 9.3 数字互相矛盾 Contradictory Numbers

### 问题形式

```text
同一批次数量不同
同一产品规格不同
同一发货重量不同
库存数量小于已发货数量
产量大于工厂产能
检测结果与合格状态矛盾
```

### 示例

```text
Batch 2045 production_quantity = 10,000 units
Shipment records show 12,500 units shipped
```

这说明：

```text
发货数量 > 生产数量
```

这是审计风险。

### Cognee 的作用

Cognee 可以把这类问题转成图谱关系：

```text
Batch 2045
  -> produced_quantity -> 10000
  -> shipped_quantity -> 12500

Finding
  -> type -> Quantity contradiction
  -> affects -> Batch 2045
```

---

## 9.4 不可能的时间顺序 Impossible Dates

### 问题形式

```text
发货时间早于生产时间
检查时间早于批次创建时间
供应商批准时间晚于采购时间
审计签收时间早于报告生成时间
过期产品仍被标记为合格
```

### 示例

```text
Batch A produced_at = 2026-05-10
Batch A shipped_at = 2026-05-08
```

### Cognee 检测逻辑

```text
if shipped_at < produced_at:
    create Finding(type="Impossible date sequence")
```

### 合规官解释

```text
Batch A 的发货日期早于生产日期。该记录不符合基本业务流程，可能是日期录入错误或批次 ID 匹配错误。建议核对 shipping.csv 与 production.csv 中的原始记录。
```

---

## 9.5 缺失值 Missing Evidence

### 问题形式

```text
批次缺少检查记录
供应商缺少批准状态
产品缺少规格记录
发货缺少接收确认
测量值缺少单位
关键字段为空
```

### 示例

```text
Batch 1099 has no inspection record
```

### Cognee 的作用

GraphRAG 可以直接发现关系缺失：

```text
Batch 1099
  -> has_no -> Inspection
```

或者通过规则生成 Finding：

```text
Every regulated batch must have at least one inspection record.
Batch 1099 has no linked inspection.
```

---

## 9.6 参考完整性问题 Referential Integrity Issues

### 问题形式

```text
shipment 中引用了不存在的 batch_id
inspection 中引用了不存在的 product_id
supplier_id 在供应商主数据中找不到
facility_id 在工厂表中不存在
```

### 示例

```text
shipment.csv row 55 references Batch 8888
but Batch 8888 does not exist in production.csv
```

### Finding 示例

```json
{
  "type": "Missing referenced entity",
  "severity": "High",
  "affected_record": "shipment.csv row 55",
  "evidence": [
    "shipment.csv references Batch 8888",
    "production.csv has no Batch 8888"
  ],
  "recommendation": "Verify whether Batch 8888 is a typo, missing import, or invalid shipment record."
}
```

---

## 9.7 状态冲突 Status Conflicts

### 问题形式

```text
供应商同时是 approved 和 suspended
批次同时是 passed 和 failed
产品同时是 active 和 discontinued
检查记录显示 failed，但最终状态是 released
```

### 示例

```text
Supplier S12 status = Approved
Supplier S12 status = Suspended
```

### Cognee 表示

```text
Supplier S12
  -> has_status -> Approved
  -> has_status -> Suspended

Finding
  -> type -> Status contradiction
  -> affects -> Supplier S12
```

---

## 9.8 异常值 Outliers

### 问题形式

```text
重量极端偏离历史范围
温度极端异常
产量远超工厂能力
批次数量远超产品平均值
```

### 示例

```text
Typical batch weight: 490–510 kg
Current record: 5,000 kg
```

### Cognee 的作用

Cognee 可以把异常值与历史上下文连接起来：

```text
Batch 5520
  -> has_measurement -> 5000 kg
  -> deviates_from -> Historical range 490–510 kg
```

---

# 10. Finding 节点设计

Use Case 1 最重要的设计之一是：**每一个问题都要变成一个 Finding 节点**。

不要只是返回一条错误日志，而是生成一个可解释对象。

## 10.1 Finding 基础结构

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

---

## 10.2 Finding 应该回答的问题

每个 Finding 应该能回答：

```text
哪里坏了？
为什么坏？
影响哪个实体？
证据来自哪里？
严重程度是多少？
是否会影响审计？
建议怎么修？
这个修复建议有多可信？
是否已经处理？
```

---

# 11. 严重程度评分设计

建议给每个问题一个 severity。

## 11.1 Severity 维度

```text
High
Medium
Low
```

或者更细：

```text
Critical
High
Medium
Low
Informational
```

## 11.2 评分依据

可以根据以下因素计算：

```text
是否影响监管审计
是否影响关键批次
是否涉及安全 / 质量 / 合规字段
是否存在多个冲突来源
是否缺失关键证据
是否无法自动修复
是否影响多个实体
```

## 11.3 示例规则

```text
单位冲突 + 涉及批次重量 + 出现在审计必填字段 = High
供应商名称轻微重复 + 不影响审计 = Low / Medium
发货日期早于生产日期 = High
缺少检查记录 = Critical
```

---

# 12. 置信度设计

每个修复建议应该有 confidence。

## 12.1 置信度来源

```text
来源系统可信度
是否有多个来源支持
是否符合业务规则
是否符合历史范围
是否只是格式问题
是否需要人工确认
```

## 12.2 示例

```text
同一批次 3 个来源中 2 个都显示 498 kg，另一个显示 1098 lb。
1098 lb 转换后约为 498 kg。
因此修复建议置信度较高。
```

输出：

```text
Suggested fix:
Use 498 kg as normalized batch weight.

Confidence:
94%

Reason:
1098 lb converts to approximately 498 kg and matches the sensor log.
```

---

# 13. Cognee GraphRAG 处理流程

整体流程可以分成 8 步。

---

## Step 1：数据导入

输入：

```text
CSV
JSON
Excel
日志文件
审计文件
系统导出表
```

每一行作为 raw memory object 存入 Cognee。

保存内容：

```text
原始字段
原始值
文件名
行号
表名
导入时间
数据来源
```

---

## Step 2：字段标准化

对字段名做统一映射。

例如：

```text
batch_id
batch_number
lot_id
lot_number
manufacturing_batch
```

都可能映射为：

```text
Batch
```

单位字段也要标准化：

```text
kg
kilogram
kilograms
kgs
```

都映射为：

```text
kg
```

---

## Step 3：实体解析 Entity Resolution

识别哪些记录实际上指向同一个实体。

例如：

```text
Batch 1042
B-1042
Lot 1042
batch_1042
```

可能都是同一个批次。

Cognee 图谱中可以建立：

```text
B-1042 -> same_as -> Batch 1042
Lot 1042 -> same_as -> Batch 1042
```

---

## Step 4：构建知识图谱

把标准化后的对象变成节点和关系。

例如：

```text
Batch 1042
  -> produced_at -> Facility 2
  -> supplied_by -> Supplier S12
  -> has_measurement -> Weight Measurement 001
  -> has_inspection -> Inspection 881
```

---

## Step 5：冲突检测

检测不同类型的问题：

```text
重复
单位冲突
数值矛盾
日期矛盾
状态矛盾
缺失证据
引用不存在
异常值
```

---

## Step 6：生成 Finding 节点

每个问题都保存为 Finding。

```text
Finding -> affects -> Batch
Finding -> supported_by -> Source Row
Finding -> recommends -> Fix
Finding -> has_status -> Open
```

---

## Step 7：GraphRAG 问答

合规官可以用自然语言问问题。

例如：

```text
Show me all issues that could fail the audit.
Why was Batch 1042 flagged?
Which records conflict with the shipping manifest?
What should I fix first?
Generate an auditor explanation for all high-risk findings.
```

系统通过 Cognee 检索相关图谱节点、原始记录和 Finding，然后生成解释。

---

## Step 8：生成审计报告

输出给合规官：

```text
审计风险总览
高风险问题清单
每个问题的证据链
建议修复动作
修复前后对比
仍需人工确认的问题
给审计员的解释文本
```

---

# 14. 推荐产品形态

## 产品名称 1：Data Rescue Copilot

定位：

```text
面向合规官的数据救援助手
```

核心能力：

```text
上传数据
自动建图
发现坏数据
解释坏数据
建议修复
生成审计说明
自然语言问答
```

---

## 产品名称 2：Audit Copilot

定位：

```text
审计前数据风险助手
```

核心能力：

```text
审计风险排序
批次级别证据追踪
高风险问题解释
一键生成审计报告
```

---

# 15. 合规官 UI 设计

因为最终用户不懂数据库，UI 不应该展示 SQL、复杂表关系或大段日志。

建议 UI 分为 5 个页面。

---

## 15.1 Audit Risk Dashboard

首页展示：

```text
Audit Risk: High

Top Issues:
1. 12 conflicting batch weights
2. 8 duplicate supplier records
3. 4 products missing inspection evidence
4. 3 shipments with impossible dates
5. 2 suspended suppliers linked to active batches
```

合规官第一眼要知道：

```text
现在风险有多高？
最严重的问题是什么？
应该先处理什么？
```

---

## 15.2 Findings List

问题列表：

```text
Finding ID
Severity
Type
Affected Entity
Audit Impact
Confidence
Status
Recommended Action
```

示例：

```text
F-001 | High | Unit conflict | Batch 1042 | May fail audit | 91% | Open | Reconcile weight units
```

---

## 15.3 Evidence View

点击某个 Finding 后，展示证据链：

```text
Problem:
Batch 1042 has conflicting weight values.

Evidence:
- inventory.csv row 82: 500 kg
- shipping.csv row 19: 500 lb
- sensor_log.csv row 44: 498 kg

Why it matters:
The audit requires consistent batch weight records across inventory and shipment systems.

Suggested fix:
Normalize all weights to kg and verify against the shipping manifest.
```

---

## 15.4 Natural Language Chat

合规官可以问：

```text
哪些问题最紧急？
为什么 Batch 1042 被标记？
这个修复建议有什么证据？
哪些问题可以自动修复？
哪些问题必须人工确认？
帮我生成给审计员看的解释。
```

---

## 15.5 Audit Report Generator

生成报告：

```text
Data Quality Rescue Report

Summary:
We identified 27 data quality issues across 6 source files.

High-risk issues:
- 12 unit conflicts
- 4 missing inspection records
- 3 impossible shipment dates

Actions taken:
- Normalized unit fields
- Merged duplicate supplier aliases
- Flagged unresolved contradictions for manual review

Evidence:
Each correction includes source row references and confidence scores.
```

---

# 16. Agent 架构设计

黑客松项目可以设计多个 Agent，每个 Agent 负责一个任务。

---

## 16.1 Ingestion Agent

职责：

```text
读取 Kaggle 数据文件
识别文件类型
抽取表头和字段
保存原始记录
记录来源和行号
```

输出：

```text
RawRecord nodes
SourceFile nodes
```

---

## 16.2 Schema Mapping Agent

职责：

```text
识别字段含义
把不同命名映射到统一概念
识别 batch_id / product_id / supplier_id 等关键字段
识别 measurement / unit / date / status 字段
```

示例：

```text
lot_number -> Batch ID
batch_no -> Batch ID
vendor_id -> Supplier ID
```

---

## 16.3 Entity Resolution Agent

职责：

```text
识别同一实体的不同写法
合并重复实体
建立 same_as / alias_of 关系
```

示例：

```text
ABC Inc.
ABC Incorporated
A.B.C. Inc.
```

合并为：

```text
Supplier: ABC Inc.
```

---

## 16.4 Unit Normalization Agent

职责：

```text
识别单位
标准化单位
转换数值
检测单位缺失
检测单位不一致
```

示例：

```text
500 lb -> 226.8 kg
98 F -> 36.7 C
```

---

## 16.5 Conflict Detection Agent

职责：

```text
发现同一实体的字段冲突
发现数值矛盾
发现日期顺序错误
发现状态冲突
发现业务规则冲突
```

输出：

```text
Finding nodes
```

---

## 16.6 Provenance Agent

职责：

```text
保存每个结论的证据来源
追踪每个值来自哪个文件、哪一行、哪个系统
解释为什么相信某个值
```

---

## 16.7 Fix Recommendation Agent

职责：

```text
提出修复建议
给出置信度
区分自动修复和人工确认
生成修复前后对比
```

---

## 16.8 Audit Explanation Agent

职责：

```text
把技术问题翻译成合规官能理解的语言
生成审计报告
生成给外部审计员看的解释
```

---

# 17. 示例 Finding 输出

## 示例 1：单位冲突

```text
Finding ID:
F-001

Severity:
High

Affected Entity:
Batch 1042

Problem:
Batch 1042 has conflicting weight measurements.

Evidence:
- inventory.csv row 82 says 500 kg
- shipping.csv row 19 says 500 lb

Why this matters:
The regulatory audit requires batch weight consistency across inventory and shipment records.

Suggested Fix:
Convert all weight values to kg and reconcile with the shipping manifest.

Confidence:
91%

Status:
Needs review
```

---

## 示例 2：日期矛盾

```text
Finding ID:
F-002

Severity:
High

Affected Entity:
Shipment S-884

Problem:
Shipment date is earlier than production date.

Evidence:
- production.csv row 21 says Batch 771 was produced on May 10
- shipping.csv row 47 says Batch 771 shipped on May 8

Why this matters:
A product cannot be shipped before it is produced.

Suggested Fix:
Verify whether the shipment date or batch ID was entered incorrectly.

Confidence:
96%

Status:
Needs manual confirmation
```

---

## 示例 3：缺少检查记录

```text
Finding ID:
F-003

Severity:
Critical

Affected Entity:
Batch 3301

Problem:
Batch 3301 has no linked inspection record.

Evidence:
- production.csv includes Batch 3301
- inspection.csv has no matching batch ID

Why this matters:
Regulated batches require inspection evidence before release.

Suggested Fix:
Locate the missing inspection record or mark the batch as audit-incomplete.

Confidence:
88%

Status:
Open
```

---

## 示例 4：供应商状态冲突

```text
Finding ID:
F-004

Severity:
High

Affected Entity:
Supplier S12

Problem:
Supplier S12 is marked as both approved and suspended.

Evidence:
- supplier_master.csv row 12 says Approved
- procurement.csv row 51 says Suspended

Why this matters:
Batches sourced from suspended suppliers may fail compliance review.

Suggested Fix:
Confirm current supplier status and update all linked records.

Confidence:
84%

Status:
Needs review
```

---

# 18. Natural Language Q&A 示例

Use Case 1 的亮点应该是让合规官直接问问题。

## 合规官问题 1

```text
Which issues could fail the audit?
```

系统回答：

```text
There are 9 high-risk issues that could affect the audit.

The most serious are:
1. 4 batches missing inspection records
2. 3 shipment records with impossible dates
3. 2 suppliers with conflicting approval statuses

Recommended priority:
Review missing inspection records first because they directly affect regulated batch release.
```

---

## 合规官问题 2

```text
Why is Batch 1042 risky?
```

系统回答：

```text
Batch 1042 is risky because it has inconsistent weight records across two source files.

Evidence:
- inventory.csv row 82 lists the weight as 500 kg
- shipping.csv row 19 lists the weight as 500 lb

These values are not equivalent. 500 lb is approximately 226.8 kg, which conflicts with the inventory value.

Recommended action:
Confirm the correct unit and update the shipping record if it was entered incorrectly.
```

---

## 合规官问题 3

```text
What should I fix first?
```

系统回答：

```text
Fix the following issues first:

1. Missing inspection records
Reason: These directly affect regulatory compliance.

2. Impossible shipment dates
Reason: These indicate broken batch traceability.

3. Unit conflicts in batch weights
Reason: These may affect inventory, shipment, and audit reconciliation.
```

---

## 合规官问题 4

```text
Generate an explanation for the auditor.
```

系统回答：

```text
During pre-audit data validation, we identified inconsistent batch weight records for Batch 1042. The inventory system listed the batch weight as 500 kg, while the shipping system listed it as 500 lb. Because these values are not equivalent, the record was flagged as a unit conflict.

The issue has not been automatically overwritten. The recommended action is to verify the correct unit against the original shipping manifest and normalize the final value to kilograms. The original source rows have been preserved for audit traceability.
```

---

# 19. 数据导入到 Cognee 的建议结构

即使实际 API 名称可能根据 Cognee 版本不同而变化，概念上可以按这个结构设计。

## 19.1 Raw Record

```json
{
  "type": "RawRecord",
  "record_id": "inventory.csv:82",
  "source_file": "inventory.csv",
  "row_number": 82,
  "fields": {
    "batch_id": "1042",
    "weight": "500",
    "unit": "kg",
    "timestamp": "2026-05-10"
  }
}
```

---

## 19.2 Entity Node

```json
{
  "type": "Batch",
  "id": "Batch 1042",
  "aliases": ["1042", "B-1042", "Lot 1042"],
  "source_records": ["inventory.csv:82", "shipping.csv:19"]
}
```

---

## 19.3 Measurement Node

```json
{
  "type": "Measurement",
  "id": "M-1042-WEIGHT-001",
  "measurement_type": "weight",
  "raw_value": "500 kg",
  "value": 500,
  "unit": "kg",
  "normalized_value": 500,
  "normalized_unit": "kg",
  "source_record": "inventory.csv:82"
}
```

---

## 19.4 Relationship

```json
{
  "from": "Batch 1042",
  "relationship": "has_measurement",
  "to": "M-1042-WEIGHT-001"
}
```

---

## 19.5 Finding Node

```json
{
  "type": "Finding",
  "id": "F-001",
  "finding_type": "Unit conflict",
  "severity": "High",
  "affected_entities": ["Batch 1042"],
  "evidence_records": ["inventory.csv:82", "shipping.csv:19"],
  "explanation": "Batch 1042 has conflicting weight values across source systems.",
  "recommendation": "Normalize weight units and reconcile against the shipping manifest.",
  "confidence": 0.91
}
```

---

# 20. GraphRAG 查询设计

在 Cognee 中，GraphRAG 查询不应该只是关键词搜索，而应该结合图关系。

## 查询 1：找所有高风险审计问题

```text
Find all Finding nodes where severity is High or Critical and explain their audit impact.
```

返回内容：

```text
Finding
Affected entity
Evidence
Reason
Recommendation
```

---

## 查询 2：解释某个批次为什么有风险

```text
Retrieve all Findings connected to Batch 1042, including source records, measurements, conflicts, and recommendations.
```

返回内容：

```text
Batch 1042
相关测量值
冲突来源
Finding
建议修复
```

---

## 查询 3：找所有单位冲突

```text
Find Measurements that belong to the same entity and same measurement type but have incompatible units or converted values.
```

---

## 查询 4：生成审计报告

```text
Retrieve all open Findings grouped by severity and audit impact. Generate a compliance-friendly summary with evidence.
```

---

# 21. 自动修复与人工确认

Use Case 1 不应该盲目自动改数据，因为涉及审计。

应该把修复分成三类。

---

## 21.1 Safe Auto-Fix

适合自动修复的问题：

```text
大小写不一致
空格问题
日期格式统一
单位标准写法统一
明显重复导入
```

示例：

```text
" kg " -> "kg"
"2026/05/10" -> "2026-05-10"
"ABC Incorporated" -> alias of "ABC Inc."
```

---

## 21.2 Suggested Fix

系统可以建议，但需要人确认：

```text
单位换算
数值冲突
供应商状态冲突
缺失检查记录
```

示例：

```text
500 lb 可能应该是 500 kg，但不能直接覆盖。
```

---

## 21.3 Manual Review Required

必须人工处理的问题：

```text
发货早于生产
检查记录缺失
供应商被暂停但仍有关联批次
多个来源都不一致
没有足够证据判断正确值
```

---

# 22. 审计友好的解释原则

产品输出必须满足审计场景，而不是只给技术结论。

## 22.1 每个解释必须包含

```text
问题是什么
为什么这是问题
影响哪些记录 / 批次 / 供应商
证据来自哪里
建议如何处理
是否已经修复
是否保留原始数据
```

---

## 22.2 避免的表达

不要说：

```text
Model thinks this is wrong.
Probably corrupted.
The AI fixed it.
```

审计场景下这种说法不可信。

---

## 22.3 推荐表达

应该说：

```text
This record was flagged because two source systems report incompatible values for the same batch attribute.

The original records were preserved.

The recommended correction is based on unit normalization and source-system comparison.

Manual confirmation is required before overwriting the final audit record.
```

---

# 23. 黑客松 MVP 版本

建议黑客松团队先做一个最小可用产品。

## MVP 功能

```text
1. 上传 Kaggle CSV 文件
2. 解析每一行并保存 source_file 和 row_number
3. 建立 Batch / Supplier / Product / Measurement 图谱
4. 检测 3 类问题：
   - duplicate records
   - unit conflicts
   - contradictory numbers
5. 生成 Finding 节点
6. 展示风险仪表盘
7. 支持自然语言问答：
   - Why is this batch risky?
   - What should I fix first?
   - Generate audit explanation.
```

---

## MVP 演示路径

演示时可以这样讲：

```text
Step 1:
合规官上传审计前导出的制造数据。

Step 2:
Cognee 自动把表格转成审计知识图谱。

Step 3:
系统发现同一批次存在重量冲突、单位冲突和重复供应商。

Step 4:
合规官点击 Batch 1042。

Step 5:
系统显示证据链：两个文件、两行记录、两个冲突值。

Step 6:
系统生成审计员可读的解释和修复建议。
```

---

# 24. Stretch Goals 高级功能

如果团队有时间，可以加入这些增强功能。

## 24.1 Graph Visualization

展示批次、供应商、测量值、来源文件之间的关系图。

合规官看到：

```text
Batch 1042
  connected to:
    inventory.csv
    shipping.csv
    sensor_log.csv
    Finding F-001
```

---

## 24.2 Audit Risk Prioritization

根据审计影响排序：

```text
Critical first
High second
Medium third
Low last
```

排序逻辑：

```text
Missing inspection records > impossible dates > unit conflicts > duplicates
```

---

## 24.3 Fix Simulation

展示修复前后变化：

```text
Before:
Batch 1042 weight = 500 kg / 500 lb

After:
Batch 1042 weight normalized to 500 kg
shipping record requires manual confirmation
```

---

## 24.4 Auditor Report Export

导出：

```text
PDF
Markdown
CSV
Excel
```

内容：

```text
Findings
Evidence
Recommended fixes
Open risks
Resolved risks
```

---

## 24.5 Historical Memory

如果以后有多个审计周期，Cognee 可以记住历史问题：

```text
这个供应商过去是否经常出现数据冲突？
这个工厂是否多次出现单位错误？
这个批次类型是否经常缺少检查记录？
```

---

# 25. 技术架构建议

可以设计成下面的结构：

```text
Frontend
  -> File Upload
  -> Findings Dashboard
  -> Evidence Viewer
  -> Chat Interface
  -> Report Generator

Backend
  -> Data Parser
  -> Entity Resolver
  -> Unit Normalizer
  -> Conflict Detector
  -> Finding Generator
  -> Cognee GraphRAG Memory
  -> LLM Explanation Layer
```

---

# 26. 数据流设计

```text
Kaggle files
  -> parse raw rows
  -> store raw records
  -> normalize schema
  -> identify entities
  -> build graph relationships
  -> detect conflicts
  -> create Finding nodes
  -> retrieve evidence with GraphRAG
  -> generate compliance-friendly explanations
  -> show dashboard / chat / report
```

---

# 27. Use Case 1 的核心差异化

普通数据清洗工具输出：

```text
Row 82 invalid.
```

Cognee GraphRAG 产品应该输出：

```text
Batch 1042 has a high-risk unit conflict.

Why:
The inventory system says 500 kg, while the shipping system says 500 lb.

Evidence:
inventory.csv row 82
shipping.csv row 19

Audit impact:
This may fail batch traceability review because shipment and inventory records disagree.

Recommended action:
Normalize units to kg and confirm the correct value against the shipping manifest.

Confidence:
91%
```

这就是 Cognee 在 Use Case 1 中的核心价值：

> 把错误行变成可解释的审计发现。

---

# 28. 推荐评分指标

黑客松项目可以用这些指标评估效果。

## 28.1 Detection Quality

```text
发现了多少真实问题
误报率有多高
漏报率有多低
是否能发现跨文件冲突
是否能发现非显性问题
```

---

## 28.2 Explainability

```text
每个 Finding 是否有证据
是否显示 source_file 和 row_number
是否说明为什么有问题
是否说明为什么建议这样修
```

---

## 28.3 Usability

```text
合规官是否能不用 SQL 操作
是否能在几分钟内理解风险
是否能生成审计解释
是否能按严重程度排序
```

---

## 28.4 Cognee Usage

```text
是否真正使用了图谱关系
是否建立了实体记忆
是否保存了证据链
是否支持 GraphRAG 问答
是否把 Finding 存回记忆
```

---

# 29. 推荐最终 Demo Story

一个好的演示故事可以这样讲：

```text
四天后就是监管审计。制造商发现多个系统中的批次数据互相矛盾。

合规官不会写 SQL，也没有时间手动检查所有表。

她上传了 Kaggle 数据集文件。

Data Rescue Copilot 使用 Cognee 把原始记录变成知识图谱，连接批次、产品、供应商、测量值、检查记录和来源文件。

系统自动发现：
- Batch 1042 的重量单位冲突
- Batch 3301 缺少检查记录
- Supplier S12 同时被标记为 approved 和 suspended
- Shipment S-884 的发货日期早于生产日期

合规官点击最高风险问题，看到每个问题的证据链、来源行号、建议修复动作和审计解释。

最后，她一键生成审计准备报告，说明哪些问题已修复，哪些仍需人工确认。
```

---

# 30. 一句话总结

Use Case 1 的最佳定位是：

> 用 Cognee GraphRAG 构建一个面向合规官的 Data Rescue Copilot，把损坏的制造数据转化为可追踪、可修复、可解释的审计证据图谱。

最重要的不是“清洗数据”，而是：

```text
Find:
找出坏数据

Fix:
提出可信修复建议

Explain:
用证据链解释给合规官和审计员
```

Cognee 的关键作用是：

```text
实体解析
关系记忆
冲突检测
证据追踪
Finding 生成
自然语言审计问答
审计报告生成
```
