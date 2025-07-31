#!/bin/bash

# DeepSearch Feature Git Push Script
# 将DeepSearch功能推送到GitHub

echo "🚀 开始推送 DeepSearch 功能到 GitHub..."

# 检查是否有未提交的更改
echo "📋 检查Git状态..."
git status

# 添加所有更改
echo "📁 添加所有文件到Git..."
git add .

# 提交更改
echo "💾 提交DeepSearch功能..."
git commit -m "feat: 添加DeepSearch高级搜索功能

🎯 核心功能:
- DeepSearch多层搜索算法
- 路径控制与可视化逻辑链
- 意图识别与智能搜索策略
- 置信度评估与自适应深度调整

🔧 技术实现:
- 新增DeepSearch核心搜索类
- 集成意图识别器 (IntentRecognizer)
- 创建可视化逻辑链组件
- 添加DeepSearchContextBuilder上下文构建器
- 配置模型和默认值设置

🌐 界面集成:
- CLI命令支持 (graphrag query --method deep)
- API接口 (deep_search, deep_search_streaming)
- Web界面集成 (unified-search-app)
- 逻辑链可视化界面

📚 文档更新:
- README.md 添加DeepSearch介绍
- docs/query/deep_search.md 详细文档
- 项目配置指南和简历介绍更新
- DeepSearch快速入门指南

🎮 游戏数据分析:
- 游戏专用意图识别器
- 玩家行为分析示例
- 付费转化路径分析
- 运营策略优化功能

✨ 特色亮点:
- 智能路径控制算法
- 实时置信度评估
- 交互式逻辑链可视化
- 多搜索策略融合
- 自适应深度调整"

# 推送到GitHub
echo "🌐 推送到GitHub remote origin..."
git push origin main

# 检查推送结果
if [ $? -eq 0 ]; then
    echo "✅ DeepSearch功能已成功推送到GitHub!"
    echo ""
    echo "🎉 功能亮点总结:"
    echo "   🎯 路径控制 - 智能搜索深度与方向控制"
    echo "   🔍 逻辑链可视化 - 完整的搜索过程透明化"
    echo "   🚀 多搜索融合 - 本地+全局搜索策略结合"
    echo "   📊 置信度评估 - 动态评估搜索质量"
    echo "   ⚡ 自适应深度 - 根据置信度自动调整"
    echo "   🎮 游戏数据专用 - 针对游戏分析优化"
    echo ""
    echo "📖 使用方法:"
    echo "   CLI: graphrag query --method deep --query \"您的问题\""
    echo "   Web: 启用 'Include deep search' 选项"
    echo "   API: await api.deep_search(...)"
    echo ""
    echo "📚 文档位置:"
    echo "   - README.md (功能介绍)"
    echo "   - docs/query/deep_search.md (详细文档)"
    echo "   - DeepSearch快速入门指南.md (快速开始)"
    echo ""
else
    echo "❌ 推送失败，请检查网络连接和权限设置"
    echo "💡 可能的解决方案:"
    echo "   1. 检查GitHub认证: git config --list"
    echo "   2. 检查远程仓库: git remote -v"
    echo "   3. 手动推送: git push origin main"
fi

echo ""
echo "🔗 项目仓库: https://github.com/microsoft/graphrag"
echo "🆕 新功能: DeepSearch - 下一代智能搜索" 