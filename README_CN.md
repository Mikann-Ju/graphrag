# GraphRAG - 基于知识图谱的检索增强生成系统

👉 [Microsoft Research 博客文章](https://www.microsoft.com/en-us/research/blog/graphrag-unlocking-llm-discovery-on-narrative-private-data/)<br/>
👉 [阅读文档](https://microsoft.github.io/graphrag)<br/>
👉 [GraphRAG 论文](https://arxiv.org/pdf/2404.16130)

<div align="left">
  <a href="https://pypi.org/project/graphrag/">
    <img alt="PyPI - 版本" src="https://img.shields.io/pypi/v/graphrag">
  </a>
  <a href="https://pypi.org/project/graphrag/">
    <img alt="PyPI - 下载量" src="https://img.shields.io/pypi/dm/graphrag">
  </a>
  <a href="https://github.com/microsoft/graphrag/issues">
    <img alt="GitHub Issues" src="https://img.shields.io/github/issues/microsoft/graphrag">
  </a>
  <a href="https://github.com/microsoft/graphrag/discussions">
    <img alt="GitHub Discussions" src="https://img.shields.io/github/discussions/microsoft/graphrag">
  </a>
</div>

## 项目概述

GraphRAG 是一个革命性的数据管道和转换套件，专门设计用于利用大语言模型（LLM）的力量从非结构化文本中提取有意义的结构化数据。它通过构建知识图谱来增强LLM对私有数据的推理能力。

### 核心特性

- **知识图谱构建**: 自动从文档中提取实体和关系，构建结构化知识图谱
- **社区发现**: 使用Leiden算法自动发现和总结知识社区
- **多种搜索模式**: 支持本地搜索、全局搜索、DRIFT搜索和基础向量搜索
- **LLM缓存**: 内置缓存机制，提高效率并增强网络容错性
- **可扩展架构**: 模块化设计，支持自定义工作流程

## 系统架构

### 主要组件

1. **索引管道 (Indexing Pipeline)**
   - 文档分块和预处理
   - 实体和关系提取
   - 图嵌入和社区发现
   - 社区报告生成

2. **查询引擎 (Query Engine)**
   - 本地搜索：基于特定实体的查询
   - 全局搜索：基于社区报告的查询
   - DRIFT搜索：结合社区信息的增强本地搜索
   - 基础搜索：传统向量检索

### 知识模型

GraphRAG 使用标准化的知识模型，包括：
- **实体表 (entities.parquet)**: 图中的节点
- **关系表 (relationships.parquet)**: 图中的边
- **文本单元表 (text_units.parquet)**: 源文档块
- **社区表 (communities.parquet)**: 发现的社区

## 快速开始

### 安装

```bash
pip install graphrag
```

### 轻量快速开始（本地小样本）

无需立即配置 API Key，先用极小文本样本跑通流程：

```bash
# 1) 创建最小项目与样例文本
mkdir -p ./rag-lite/input
echo "你好，GraphRAG 轻量模式。" > ./rag-lite/input/sample.txt

# 2) 初始化（生成 .env 与 settings.yaml）
graphrag init --root ./rag-lite

# 3) 在 ./rag-lite/settings.yaml 中采用轻量参数
#    - chunk_size: 256
#    - batch_size: 8, batch_max_tokens: 1500
#    - 先不启用 claims（可选的重活步骤）
# 4) 待获取 API Key 后再执行索引
# graphrag index --root ./rag-lite
```

可选：PDF 输入（实验性）。在 `settings.yaml` 中设置 `input.file_type: pdf` 与 `file_pattern: ".*\\.pdf$"`，安装 PyMuPDF 后可启用启发式 PDF→Markdown 层级还原。详见 docs/index/inputs.md。

### 基本使用

1. **初始化项目**
```bash
graphrag init --root /path/to/your/project
```

2. **配置设置**
编辑 `settings.yml` 文件，配置您的数据源和模型设置。

3. **运行索引**
```bash
graphrag index --root /path/to/your/project
```

4. **执行查询**
```python
from graphrag import GraphRAG

# 初始化GraphRAG
rag = GraphRAG.from_project_root("/path/to/your/project")

# 执行查询
response = rag.query("您的问题")
print(response)
```

## 搜索模式详解

### 1. 本地搜索 (Local Search)
- **适用场景**: 需要理解文档中特定实体的问题
- **示例**: "洋甘菊有什么治疗功效？"
- **工作原理**: 结合知识图谱和原始文档块生成答案

### 2. 全局搜索 (Global Search)
- **适用场景**: 需要理解整个数据集的问题
- **示例**: "这个笔记本中提到的最重要的草药价值是什么？"
- **工作原理**: 以map-reduce方式搜索所有AI生成的社区报告

### 3. DRIFT搜索 (DRIFT Search)
- **适用场景**: 需要更全面信息的本地搜索查询
- **工作原理**: 在搜索过程中包含社区信息，扩大查询的起点广度

### 4. 基础搜索 (Basic Search)
- **适用场景**: 传统向量检索比较
- **工作原理**: 基于向量相似度的简单RAG实现

## 高级功能

### 提示调优 (Prompt Tuning)
为了获得最佳结果，强烈建议根据您的数据调优提示。请参考[提示调优指南](https://microsoft.github.io/graphrag/prompt_tuning/overview/)。

### 自带图谱 (Bring Your Own Graph)
如果您已有现有的知识图谱，GraphRAG支持导入和总结您自己的图数据。

### 工作流程自定义
GraphRAG支持自定义工作流程，您可以选择只运行需要的特定步骤：

```yaml
workflows: [create_communities, create_community_reports]
```

## 成本考虑

⚠️ **重要提醒**: GraphRAG索引可能是一项昂贵的操作，请：
- 仔细阅读所有文档以了解流程和涉及的成本
- 从小规模开始测试
- 监控API使用量和成本

## 项目结构

```
graphrag/
├── graphrag/           # 核心库代码
│   ├── index/         # 索引管道
│   ├── query/         # 查询引擎
│   ├── config/        # 配置管理
│   └── ...
├── docs/              # 文档
├── examples_notebooks/ # 示例笔记本
├── tests/             # 测试代码
└── unified-search-app/ # 统一搜索应用
```

## 贡献指南

- 查看 [CONTRIBUTING.md](./CONTRIBUTING.md) 了解贡献指南
- 查看 [DEVELOPING.md](./DEVELOPING.md) 开始开发
- 在 [GitHub Discussions](https://github.com/microsoft/graphrag/discussions) 中参与讨论

## 版本管理

请查看 [breaking-changes.md](./breaking-changes.md) 了解版本管理方法。

**重要**: 
- 在次要版本更新之间运行 `graphrag init --root [path] --force` 确保配置格式最新
- 在主要版本更新之间运行提供的迁移笔记本以避免重新索引

## 负责任AI

查看 [RAI_TRANSPARENCY.md](./RAI_TRANSPARENCY.md) 了解：
- GraphRAG是什么？
- GraphRAG能做什么？
- GraphRAG的预期用途
- 如何评估GraphRAG？
- GraphRAG的局限性
- 有效和负责任使用的操作因素

## 许可证和商标

本项目可能包含项目、产品或服务的商标或徽标。Microsoft商标或徽标的授权使用必须遵循[Microsoft商标和品牌指南](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general)。

## 隐私

[Microsoft隐私声明](https://privacy.microsoft.com/en-us/privacystatement)

---

**注意**: 本仓库提供了一个使用知识图谱内存结构增强LLM输出的方法。请注意，提供的代码仅作为演示，不是Microsoft官方支持的产品。 