"""
Workflow & Agent Management API Blueprint
"""
from flask import Blueprint, request, jsonify
from ..models import (
    db, WorkflowDefinition, WorkflowExecution,
    AgentDefinition, PromptTemplate, ToolDefinition, Alert
)
from ..services.utils import token_required, log_audit
from ..agent_engine.compiler import WorkflowCompiler
from ..agent_engine.prompts import (
    DEFAULT_SUPERVISOR_PROMPT, DEFAULT_ANALYSIS_PROMPT, DEFAULT_ACTION_PROMPT
)
from datetime import datetime
import asyncio

workflow_bp = Blueprint('workflow', __name__)

# ==============================================================================
# 1. 提示词管理 API (Prompts)
# ==============================================================================

@workflow_bp.route('/api/prompts', methods=['GET'])
@token_required
def get_prompts(current_user):
    prompts = PromptTemplate.query.order_by(PromptTemplate.id.asc()).all()
    # 如果系统首次运行为空，自动初始化默认模板
    if not prompts:
        p1 = PromptTemplate(name="默认总控调度提示词", agent_code="supervisor", system_prompt=DEFAULT_SUPERVISOR_PROMPT, is_default=True)
        p2 = PromptTemplate(name="默认分析研判提示词", agent_code="analysis", system_prompt=DEFAULT_ANALYSIS_PROMPT, is_default=True)
        p3 = PromptTemplate(name="默认处置执行提示词", agent_code="action", system_prompt=DEFAULT_ACTION_PROMPT, is_default=True)
        db.session.add_all([p1, p2, p3])
        db.session.commit()
        prompts = [p1, p2, p3]
    return jsonify([p.to_dict() for p in prompts])


@workflow_bp.route('/api/prompts/<int:prompt_id>', methods=['PUT'])
@token_required
def update_prompt(current_user, prompt_id):
    prompt = PromptTemplate.query.get_or_404(prompt_id)
    data = request.get_json() or {}
    if 'system_prompt' in data:
        prompt.system_prompt = data['system_prompt']
    if 'name' in data:
        prompt.name = data['name']
    prompt.version += 1
    db.session.commit()
    log_audit('更新提示词模板', '成功', user_id=current_user.id, details=f"更新了提示词 ID: {prompt_id}")
    return jsonify({'message': 'Prompt updated', 'data': prompt.to_dict()})


# ==============================================================================
# 2. 智能体 Agent 定义管理 API
# ==============================================================================

@workflow_bp.route('/api/agents', methods=['GET'])
@token_required
def get_agents(current_user):
    agents = AgentDefinition.query.order_by(AgentDefinition.id.asc()).all()
    if not agents:
        # 初始化默认两个双阶段 Agent
        a1 = AgentDefinition(name="内置研判分析智能体", code="analysis_agent", role="analyst", model_name="deepseek-chat")
        a2 = AgentDefinition(name="内置主动处置智能体", code="action_agent", role="responder", model_name="deepseek-chat")
        db.session.add_all([a1, a2])
        db.session.commit()
        agents = [a1, a2]
    return jsonify([a.to_dict() for a in agents])


# ==============================================================================
# 3. 工具与 MCP 管理 API
# ==============================================================================

@workflow_bp.route('/api/tools', methods=['GET'])
@token_required
def get_tools(current_user):
    tools = ToolDefinition.query.order_by(ToolDefinition.id.asc()).all()
    if not tools:
        t1 = ToolDefinition(
            name="威胁情报查询 (IP Threat Intel)",
            code="lookup_ip_threat_intel",
            tool_type="python_skill",
            description="查询指定外部 IP 的威胁情报、恶意程度与地理位置。"
        )
        t2 = ToolDefinition(
            name="边界防火墙封禁 (Block Firewall IP)",
            code="block_firewall_ip",
            tool_type="python_skill",
            description="在防火墙下发黑名单阻断规则。"
        )
        t3 = ToolDefinition(
            name="主机网络隔离 (EDR Network Isolation)",
            code="isolate_host_network",
            tool_type="python_skill",
            description="通过 EDR 对被渗透主机执行网络隔离。"
        )
        db.session.add_all([t1, t2, t3])
        db.session.commit()
        tools = [t1, t2, t3]
    return jsonify([t.to_dict() for t in tools])


# ==============================================================================
# 4. 可视化工作流编排 API (Workflows)
# ==============================================================================

@workflow_bp.route('/api/workflows', methods=['GET', 'POST'])
@token_required
def workflows(current_user):
    if request.method == 'GET':
        wfs = WorkflowDefinition.query.order_by(WorkflowDefinition.id.desc()).all()
        # 如果空，初始化一条开箱即用的双阶段默认连线工作流
        if not wfs:
            default_graph = {
                "nodes": [
                    {
                        "id": "node_trigger",
                        "type": "input",
                        "position": {"x": 100, "y": 200},
                        "data": {"label": "告警事件接入 (Webhook)"}
                    },
                    {
                        "id": "node_analysis",
                        "type": "agent",
                        "position": {"x": 380, "y": 200},
                        "data": {
                            "label": "研判分析智能体 (Analysis Agent)",
                            "role": "analyst",
                            "model": "deepseek-chat",
                            "tools": ["lookup_ip_threat_intel"]
                        }
                    },
                    {
                        "id": "node_action",
                        "type": "agent",
                        "position": {"x": 680, "y": 200},
                        "data": {
                            "label": "阻断处置智能体 (Action Agent)",
                            "role": "responder",
                            "model": "deepseek-chat",
                            "tools": ["block_firewall_ip"]
                        }
                    }
                ],
                "edges": [
                    {"id": "e1", "source": "node_trigger", "target": "node_analysis", "animated": True},
                    {"id": "e2", "source": "node_analysis", "target": "node_action", "animated": True}
                ]
            }
            default_wf = WorkflowDefinition(
                name="双阶段智能研判与联动响应标准工作流",
                description="默认内置的工作流：告警接入 -> 威胁情报研判 -> 防火墙阻断",
                graph_data=default_graph,
                is_active=True
            )
            db.session.add(default_wf)
            db.session.commit()
            wfs = [default_wf]
        return jsonify([w.to_dict() for w in wfs])

    # POST: 新增或保存工作流
    data = request.get_json() or {}
    wf = WorkflowDefinition(
        name=data.get('name', '未命名多Agent工作流'),
        description=data.get('description', ''),
        graph_data=data.get('graph_data', {"nodes": [], "edges": []}),
        is_active=data.get('is_active', False)
    )
    db.session.add(wf)
    db.session.commit()
    log_audit('创建编排工作流', '成功', user_id=current_user.id, details=f"创建工作流: {wf.name}")
    return jsonify(wf.to_dict()), 201


@workflow_bp.route('/api/workflows/<int:wf_id>', methods=['GET', 'PUT', 'DELETE'])
@token_required
def workflow_detail(current_user, wf_id):
    wf = WorkflowDefinition.query.get_or_404(wf_id)
    if request.method == 'GET':
        return jsonify(wf.to_dict())

    if request.method == 'PUT':
        data = request.get_json() or {}
        if 'name' in data:
            wf.name = data['name']
        if 'description' in data:
            wf.description = data['description']
        if 'graph_data' in data:
            wf.graph_data = data['graph_data']
        if 'is_active' in data:
            if data['is_active']:
                # 只能有一个 active 工作流
                WorkflowDefinition.query.filter(WorkflowDefinition.id != wf_id).update({'is_active': False})
            wf.is_active = data['is_active']
        db.session.commit()
        log_audit('更新编排工作流', '成功', user_id=current_user.id, details=f"更新工作流 ID: {wf_id}")
        return jsonify(wf.to_dict())

    if request.method == 'DELETE':
        db.session.delete(wf)
        db.session.commit()
        log_audit('删除编排工作流', '成功', user_id=current_user.id, details=f"删除工作流 ID: {wf_id}")
        return jsonify({'message': 'Workflow deleted'})


# ==============================================================================
# 5. 工作流一键试运行 / 测试触发 API
# ==============================================================================

@workflow_bp.route('/api/workflows/<int:wf_id>/run-test', methods=['POST'])
@token_required
def run_workflow_test(current_user, wf_id):
    wf = WorkflowDefinition.query.get_or_404(wf_id)
    data = request.get_json() or {}
    test_title = data.get('title', '【模拟测试】可疑挖矿与异常外联探测')
    test_content = data.get('content', '源IP: 194.26.29.112, 端口: 4444, 触发特征: Mining Pool IP')

    compiler = WorkflowCompiler(wf.graph_data or {})
    graph = compiler.compile()

    initial_state = {
        "alert_id": "test-alert-001",
        "title": test_title,
        "content": test_content,
        "analysis_result": "",
        "action_result": "",
        "threat_level": "UNKNOWN",
        "current_node": "START",
        "execution_trace": []
    }

    try:
        # 运行编译出的 LangGraph 图
        result = asyncio.run(graph.ainvoke(initial_state))
        return jsonify({
            'success': True,
            'message': '工作流编译并执行成功',
            'result': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'执行失败: {str(e)}'
        }), 500

# ==============================================================================
# 6. Splunk 安全检索与排障工作台 API (专项 4.1 & 4.2)
# ==============================================================================
from ..agent_engine.splunk_guard import SplunkGuard, SplunkQuerySecurityError
from ..agent_engine.verifier import EvidenceVerifier
from ..agent_engine.sop_engine import SOPEngine
from ..models import GoldenSOP, AlertSOPRecord

@workflow_bp.route('/api/splunk/query', methods=['POST'])
@token_required
def query_splunk(current_user):
    data = request.get_json() or {}
    query = data.get('query', '')
    context_index = data.get('index', 'idx_prod_payment')
    allowed_indexes = data.get('allowed_indexes', ['idx_prod_payment', 'idx_prod_trace', 'idx_security_audit'])
    
    guard = SplunkGuard(allowed_indexes=allowed_indexes)
    try:
        res = guard.execute_mock_search(query, context_index)
        return jsonify(res)
    except SplunkQuerySecurityError as e:
        return jsonify({'error': str(e), 'security_violation': True}), 400


@workflow_bp.route('/api/sop/workbench/<alert_id>', methods=['GET'])
@token_required
def get_alert_workbench(current_user, alert_id):
    """获取指定告警的双栏排障工作台数据 (证据链 + 质检 + SOP)"""
    record = AlertSOPRecord.query.filter_by(alert_id=alert_id).first()
    if not record:
        # 自动生成初版工作台数据
        guard = SplunkGuard(allowed_indexes=['idx_prod_payment'])
        splunk_data = guard.execute_mock_search("index=idx_prod_payment destination=194.26.29.112", "idx_prod_payment")
        
        rca = (
            "【确凿根因】主机 prod-srv-billing-01 上的 PaymentWorker 服务发生异常外联。\\n"
            "目的 IP 194.26.29.112:4444 命中境外可疑 C2 节点特征，行为表现为高频心跳外联与 ECONNRESET。"
        )
        
        # 质检
        verifier = EvidenceVerifier("异常外联告警: 194.26.29.112", splunk_data["matched_events"])
        v_report = verifier.verify(rca)
        
        # 动态自适应 SOP
        sop = SOPEngine.generate_adaptive_sop(
            alert_title="[严重] 生产主机异常外联 C2 节点告警",
            target_entity="prod-srv-billing-01",
            rca_conclusion=rca,
            evidence_snippet=str(splunk_data["matched_events"])
        )
        
        record = AlertSOPRecord(
            alert_id=alert_id,
            target_index="idx_prod_payment",
            splunk_evidence=splunk_data["matched_events"],
            rca_summary=rca,
            verifier_report=v_report,
            sop_content=sop,
            status="draft"
        )
        db.session.add(record)
        db.session.commit()
        
    return jsonify(record.to_dict())


@workflow_bp.route('/api/sop/workbench/<alert_id>/confirm', methods=['POST'])
@token_required
def confirm_and_feed_golden_sop(current_user, alert_id):
    """运维工程师在线保存校准后的 SOP，并反哺沉淀至长期记忆黄金知识库 (知识飞轮)"""
    record = AlertSOPRecord.query.filter_by(alert_id=alert_id).first_or_404()
    data = request.get_json() or {}
    
    if 'sop_content' in data:
        record.sop_content = data['sop_content']
    record.status = 'confirmed'
    
    # 沉淀至 GoldenSOP 知识飞轮
    pattern = "C2_BEACONING_PAYMENT_SVC"
    golden = GoldenSOP.query.filter_by(alert_pattern=pattern).first()
    if golden:
        golden.sop_content = record.sop_content
        golden.use_count += 1
        golden.calibrated_by = current_user.username
    else:
        golden = GoldenSOP(
            alert_pattern=pattern,
            title="【黄金SOP】C2异常外联应急处置预案",
            sop_content=record.sop_content,
            calibrated_by=current_user.username,
            use_count=1
        )
        db.session.add(golden)
        
    db.session.commit()
    log_audit('人工校准并归档黄金SOP', '成功', user_id=current_user.id, details=f"告警 ID: {alert_id}，已沉淀知识飞轮")
    return jsonify({
        'message': 'SOP 已保存并成功反哺至黄金知识库',
        'golden_sop': golden.to_dict(),
        'record': record.to_dict()
    })


@workflow_bp.route('/api/sop/golden', methods=['GET'])
@token_required
def list_golden_sops(current_user):
    sops = GoldenSOP.query.order_by(GoldenSOP.use_count.desc()).all()
    return jsonify([s.to_dict() for s in sops])
