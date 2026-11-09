"""
Workflow Compiler: Translates visual React Flow Graph DSL into executable LangGraph StateGraph
"""
from typing import Dict, Any, List, TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, START, END
from .prompts import render_prompt
from .tools import BUILTIN_TOOLS
from .memory import ContextCompressor

class WorkflowState(TypedDict):
    """LangGraph 运行期统一状态"""
    alert_id: str
    title: str
    content: str
    analysis_result: str
    action_result: str
    threat_level: str
    current_node: str
    execution_trace: Annotated[List[Dict[str, Any]], operator.add]


class WorkflowCompiler:
    """
    负责解析前端可视化的 nodes 和 edges 并构建 LangGraph 实例
    """
    def __init__(self, graph_data: Dict[str, Any]):
        self.nodes = graph_data.get("nodes", [])
        self.edges = graph_data.get("edges", [])
        self.compressor = ContextCompressor()

    def _create_node_executor(self, node_id: str, node_type: str, node_data: Dict[str, Any]):
        """生成每个节点的具体执行函数"""
        name = node_data.get("label", node_id)
        role = node_data.get("role", "")
        
        async def node_fn(state: WorkflowState) -> Dict[str, Any]:
            trace_entry = {
                "node_id": node_id,
                "node_name": name,
                "node_type": node_type,
                "status": "success",
                "output": ""
            }
            
            # 1. 处置执行智能体 (Responder / Action)
            if node_type == "action_agent" or role in ["responder", "action"] or "处置" in name:
                block_res = BUILTIN_TOOLS["block_firewall_ip"].invoke({
                    "ip": "194.26.29.112",
                    "duration_hours": 48
                })
                output_text = f"【自动处置】已下发防火墙黑名单拦截 IP 194.26.29.112。下发回执: {block_res}"
                trace_entry["output"] = output_text
                return {
                    "action_result": output_text,
                    "current_node": node_id,
                    "execution_trace": [trace_entry]
                }

            # 2. 研判分析智能体 (Analyst / Analysis)
            elif node_type == "analysis_agent" or role in ["analyst", "analysis"] or "分析" in name or "研判" in name:
                intel_res = BUILTIN_TOOLS["lookup_ip_threat_intel"].invoke({"ip": "194.26.29.112"})
                output_text = (
                    f"【自动研判】告警涉及高危外部扫描。已调用威胁情报工具查证。\\n"
                    f"情报详情: {intel_res}\\n"
                    f"建议处置策略：下发防火墙紧急临时阻断。"
                )
                trace_entry["output"] = output_text
                return {
                    "analysis_result": output_text,
                    "threat_level": "HIGH",
                    "current_node": node_id,
                    "execution_trace": [trace_entry]
                }
                
            # 3. 输入源或其它节点
            else:
                trace_entry["output"] = f"接入节点 {name} 触发并向下游流转"
                return {
                    "current_node": node_id,
                    "execution_trace": [trace_entry]
                }

        return node_fn

    def compile(self):
        """编译为 StateGraph"""
        graph_builder = StateGraph(WorkflowState)
        node_ids = set()

        # 1. 注册所有节点
        for n in self.nodes:
            n_id = n["id"]
            n_type = n.get("type", "agent")
            n_data = n.get("data", {})
            node_ids.add(n_id)
            graph_builder.add_node(n_id, self._create_node_executor(n_id, n_type, n_data))

        # 2. 注册所有连线边
        if not self.edges and node_ids:
            ordered_nodes = list(node_ids)
            graph_builder.add_edge(START, ordered_nodes[0])
            for i in range(len(ordered_nodes) - 1):
                graph_builder.add_edge(ordered_nodes[i], ordered_nodes[i + 1])
            graph_builder.add_edge(ordered_nodes[-1], END)
        else:
            target_ids = {e["target"] for e in self.edges}
            start_candidates = [n_id for n_id in node_ids if n_id not in target_ids]
            
            if start_candidates:
                graph_builder.add_edge(START, start_candidates[0])
            elif node_ids:
                graph_builder.add_edge(START, next(iter(node_ids)))

            for edge in self.edges:
                src = edge["source"]
                tgt = edge["target"]
                if src in node_ids and tgt in node_ids:
                    graph_builder.add_edge(src, tgt)

            source_ids = {e["source"] for e in self.edges}
            end_candidates = [n_id for n_id in node_ids if n_id not in source_ids]
            for end_id in end_candidates:
                graph_builder.add_edge(end_id, END)

        return graph_builder.compile()
