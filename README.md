# AI Terms Database

AI Dictionary（AI 时代词典）的**远程在线词库**，用于客户端启动时自动同步最新 AI 术语。

## 项目介绍

本仓库保存 AI 领域的高质量术语数据，供 [AI Dictionary](https://github.com/) 桌面客户端
通过「启动自动同步词库系统」增量下载。当前版本包含 **1094 个 AI 相关术语**，
覆盖以下领域：

- AI 基础概念
- 大语言模型（LLM）
- AI Agent
- RAG 与检索
- AI 开发框架与工具
- 模型训练与对齐
- AI 基础设施（算力 / 推理 / 部署）
- 多模态 AI
- AI 安全与治理
- 最新 AI 趋势
- NLP、机器学习、强化学习、数据工程、计算机视觉、推荐系统等

## 词库用途

AI Dictionary 客户端启动时会：

1. 读取本仓库的 `version.json`，与本地词库版本比较；
2. 若远程版本更新，下载 `terms.json`；
3. **增量插入**本地不存在的词条（不删除、不覆盖，不影响用户收藏与历史）；
4. 无网络时静默使用本地词库，不影响使用。

## 文件说明

### version.json

```json
{
  "version": "1.1.0",
  "update_time": "2026-08-08",
  "description": "AI Dictionary initial online vocabulary update",
  "terms_count": 1094
}
```

`version` 为语义化版本号：**每次发布新词库必须调高**，客户端才会触发更新。

### terms.json

JSON 数组，每个词条格式如下（必须与客户端模型兼容）：

```json
{
  "english_name": "Agent",
  "chinese_name": "智能体",
  "category": "AI Agent",
  "difficulty": 2,
  "short_description": "能够自主完成任务的 AI 系统。",
  "detail_description": "详细解释……",
  "application": ["ChatGPT Agent", "Claude Agent"],
  "related_terms": ["LLM", "RAG", "Memory"]
}
```

字段说明：

| 字段 | 说明 | 要求 |
|---|---|---|
| english_name | 英文名称 | 唯一，不区分大小写，不得重复 |
| chinese_name | 中文名称 | 非空 |
| category | 分类 | 使用稳定的中文分类 |
| difficulty | 难度 | 整数 1~3（入门 / 进阶 / 高级） |
| short_description | 一句话解释 | 非空 |
| detail_description | 详细解释 | 非空，2~3 句为宜 |
| application | 应用场景 | 非空字符串数组 |
| related_terms | 相关词条 | 非空字符串数组，引用其他 english_name |

## 如何贡献新词

1. Fork 本仓库；
2. 编辑 `terms.json`，在数组中**追加**新词条（保持字段完整、难度合法、英文名不重复）；
3. 提交 Pull Request，说明新增词条所属领域；
4. 维护者合并后，将 `version.json` 的 `version` 与 `update_time`、`terms_count` 一并更新。

贡献规范：

- 英文名准确、中文名自然；
- 解释面向 AI 初学者，同时保留专业含义；
- 给出实际应用场景，关联相关概念；
- 不要复制百科原文，不要空泛解释，不要加入同义词变体（如 GPT / GPT Model / GPT AI）。

## 版本更新规则

- 每次发布调高 `version`（如 1.1.0 → 1.2.0）；
- 同步更新 `update_time` 与 `terms_count`；
- 客户端在启动时自动检查：本地版本 ≥ 远程则跳过；24 小时内不重复检查；
- 词库只做**增量追加**，不删除旧词条，保证所有用户数据安全。
