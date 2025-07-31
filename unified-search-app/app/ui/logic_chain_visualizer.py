# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""DeepSearch逻辑链可视化组件."""

import json
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots


def visualize_logic_chain(logic_chain_data: dict[str, Any]) -> None:
    """可视化DeepSearch的逻辑链.
    
    Args:
        logic_chain_data: 逻辑链数据，包含paths和其他元数据
    """
    if not logic_chain_data or "paths" not in logic_chain_data:
        st.warning("没有逻辑链数据可显示")
        return
    
    paths = logic_chain_data.get("paths", [])
    if not paths:
        st.warning("逻辑链中没有搜索路径")
        return
    
    st.subheader("🔍 深度搜索逻辑链")
    
    # 创建标签页
    tab1, tab2, tab3 = st.tabs(["搜索路径图", "置信度分析", "详细信息"])
    
    with tab1:
        _render_search_path_graph(paths)
    
    with tab2:
        _render_confidence_analysis(paths, logic_chain_data)
    
    with tab3:
        _render_detailed_info(logic_chain_data)


def _render_search_path_graph(paths: list[dict[str, Any]]) -> None:
    """渲染搜索路径图."""
    if not paths:
        return
    
    # 创建路径流程图
    fig = go.Figure()
    
    # 为不同搜索类型定义颜色
    color_map = {
        "local": "#1f77b4",     # 蓝色
        "global": "#ff7f0e",    # 橙色
        "drift": "#2ca02c",     # 绿色
        "deep": "#d62728",      # 红色
        "basic": "#9467bd",     # 紫色
    }
    
    x_positions = []
    y_positions = []
    colors = []
    texts = []
    sizes = []
    
    for i, path in enumerate(paths):
        x_positions.append(i + 1)
        y_positions.append(1)
        
        search_type = path.get("search_type", "unknown")
        colors.append(color_map.get(search_type, "#808080"))
        
        confidence = path.get("confidence", 0)
        texts.append(f"步骤 {path.get('step', i+1)}<br>"
                    f"类型: {search_type}<br>"
                    f"置信度: {confidence:.2f}")
        
        # 根据置信度调整大小
        sizes.append(max(20, min(60, confidence * 80)))
    
    # 添加散点图
    fig.add_trace(go.Scatter(
        x=x_positions,
        y=y_positions,
        mode='markers+text',
        marker=dict(
            size=sizes,
            color=colors,
            line=dict(width=2, color='white'),
            opacity=0.8
        ),
        text=[f"步骤 {i+1}" for i in range(len(paths))],
        textposition="middle center",
        textfont=dict(color='white', size=12),
        hovertext=texts,
        hoverinfo='text',
        name="搜索步骤"
    ))
    
    # 添加连接线
    if len(paths) > 1:
        fig.add_trace(go.Scatter(
            x=x_positions,
            y=y_positions,
            mode='lines',
            line=dict(color='gray', width=2, dash='dash'),
            showlegend=False,
            hoverinfo='none'
        ))
    
    fig.update_layout(
        title="搜索路径流程图",
        xaxis_title="搜索步骤",
        yaxis=dict(
            showticklabels=False,
            showgrid=False,
            range=[0.5, 1.5]
        ),
        xaxis=dict(
            showgrid=False,
            dtick=1
        ),
        height=300,
        showlegend=True
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 添加图例
    st.markdown("**搜索类型说明:**")
    cols = st.columns(len(color_map))
    for i, (search_type, color) in enumerate(color_map.items()):
        with cols[i]:
            st.markdown(f"<span style='color: {color}'>●</span> {search_type.title()}", 
                       unsafe_allow_html=True)


def _render_confidence_analysis(paths: list[dict[str, Any]], logic_chain_data: dict[str, Any]) -> None:
    """渲染置信度分析."""
    if not paths:
        return
    
    # 创建置信度趋势图
    steps = [path.get("step", i+1) for i, path in enumerate(paths)]
    confidences = [path.get("confidence", 0) for path in paths]
    search_types = [path.get("search_type", "unknown") for path in paths]
    
    fig = px.line(
        x=steps,
        y=confidences,
        title="置信度变化趋势",
        labels={"x": "搜索步骤", "y": "置信度"},
        markers=True
    )
    
    # 添加不同搜索类型的颜色标记
    color_map = {
        "local": "#1f77b4",
        "global": "#ff7f0e", 
        "drift": "#2ca02c",
        "deep": "#d62728",
        "basic": "#9467bd",
    }
    
    for i, (step, confidence, search_type) in enumerate(zip(steps, confidences, search_types)):
        fig.add_trace(go.Scatter(
            x=[step],
            y=[confidence],
            mode='markers',
            marker=dict(
                size=15,
                color=color_map.get(search_type, "#808080"),
                line=dict(width=2, color='white')
            ),
            name=f"{search_type.title()} 搜索",
            showlegend=True,
            hovertemplate=f"步骤 {step}<br>类型: {search_type}<br>置信度: {confidence:.2f}<extra></extra>"
        ))
    
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    # 显示统计信息
    col1, col2, col3 = st.columns(3)
    
    with col1:
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        st.metric("平均置信度", f"{avg_confidence:.2f}")
    
    with col2:
        max_confidence = max(confidences) if confidences else 0
        st.metric("最高置信度", f"{max_confidence:.2f}")
    
    with col3:
        total_confidence = logic_chain_data.get("total_confidence", 0)
        st.metric("总体置信度", f"{total_confidence:.2f}")


def _render_detailed_info(logic_chain_data: dict[str, Any]) -> None:
    """渲染详细信息."""
    paths = logic_chain_data.get("paths", [])
    
    st.markdown("### 搜索路径详细信息")
    
    for i, path in enumerate(paths):
        with st.expander(f"步骤 {path.get('step', i+1)}: {path.get('search_type', 'unknown').title()} 搜索"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**基本信息**")
                st.write(f"- 搜索类型: {path.get('search_type', 'unknown')}")
                st.write(f"- 查询: {path.get('query', 'N/A')}")
                st.write(f"- 置信度: {path.get('confidence', 0):.2f}")
                st.write(f"- 时间戳: {path.get('timestamp', 'N/A')}")
            
            with col2:
                st.write("**上下文使用**")
                context_used = path.get('context_used', [])
                if context_used:
                    for ctx in context_used:
                        st.write(f"- {ctx}")
                else:
                    st.write("- 无特定上下文")
            
            st.write("**推理过程**")
            reasoning = path.get('reasoning', '无推理信息')
            st.write(reasoning)
    
    # 显示最终推理
    final_reasoning = logic_chain_data.get("final_reasoning", "")
    if final_reasoning:
        st.markdown("### 最终推理")
        st.info(final_reasoning)
    
    # 显示原始数据
    with st.expander("查看原始逻辑链数据"):
        st.json(logic_chain_data)


def create_logic_chain_summary(logic_chain_data: dict[str, Any]) -> str:
    """创建逻辑链摘要文本.
    
    Args:
        logic_chain_data: 逻辑链数据
        
    Returns:
        逻辑链的文本摘要
    """
    if not logic_chain_data or "paths" not in logic_chain_data:
        return "没有逻辑链数据"
    
    paths = logic_chain_data.get("paths", [])
    if not paths:
        return "逻辑链中没有搜索路径"
    
    summary_parts = []
    summary_parts.append(f"执行了 {len(paths)} 个搜索步骤:")
    
    for path in paths:
        step = path.get("step", "?")
        search_type = path.get("search_type", "unknown")
        confidence = path.get("confidence", 0)
        summary_parts.append(f"  步骤 {step}: {search_type} 搜索 (置信度: {confidence:.2f})")
    
    total_confidence = logic_chain_data.get("total_confidence", 0)
    summary_parts.append(f"总体置信度: {total_confidence:.2f}")
    
    final_reasoning = logic_chain_data.get("final_reasoning", "")
    if final_reasoning:
        summary_parts.append(f"最终推理: {final_reasoning}")
    
    return "\n".join(summary_parts) 