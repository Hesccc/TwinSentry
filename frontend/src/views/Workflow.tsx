import React, { useState, useEffect, useCallback } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,

  Handle,
  Position
} from '@xyflow/react';
import type { Connection, Edge, Node } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  GitMerge,
  Play,
  Save,
  Plus,
  Settings,
  Bot,
  Zap,
  ShieldCheck,
  Filter,
  CheckCircle2,
  AlertCircle,
  X,
  Layers,
  Sparkles
} from 'lucide-react';
import { workflowApi, promptApi, toolsApi } from '@/api';

// Custom Node: Trigger
const TriggerNode = ({ data }: any) => (
  <div className="px-4 py-3 rounded-2xl bg-gradient-to-r from-blue-900/60 to-indigo-900/60 border-2 border-blue-500/60 shadow-xl min-w-[180px]">
    <div className="flex items-center gap-2 mb-1">
      <Zap className="w-4 h-4 text-blue-400" />
      <span className="text-xs font-bold text-blue-300">事件输入源</span>
    </div>
    <div className="text-sm font-semibold text-white">{data.label || 'Webhook 告警接入'}</div>
    <Handle type="source" position={Position.Right} className="!w-3 !h-3 !bg-blue-400" />
  </div>
);

// Custom Node: Agent
const AgentNode = ({ data }: any) => (
  <div className="px-5 py-4 rounded-2xl bg-[#0f172a] border-2 border-indigo-500/50 shadow-2xl min-w-[220px] backdrop-blur relative group">
    <Handle type="target" position={Position.Left} className="!w-3 !h-3 !bg-indigo-400" />
    <div className="flex items-center justify-between mb-2">
      <div className="flex items-center gap-1.5">
        <Bot className="w-4 h-4 text-indigo-400" />
        <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-300">
          {data.role || '智能体'}
        </span>
      </div>
      <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-mono">
        {data.model || 'deepseek-chat'}
      </span>
    </div>
    <div className="text-sm font-bold text-white mb-1">{data.label}</div>
    <div className="text-[11px] text-gray-400 flex items-center gap-1">
      <Sparkles className="w-3 h-3 text-amber-400" />
      <span>挂载 {data.tools?.length || 1} 个工具/MCP</span>
    </div>
    <Handle type="source" position={Position.Right} className="!w-3 !h-3 !bg-indigo-400" />
  </div>
);

const nodeTypes = {
  input: TriggerNode,
  agent: AgentNode,
};

export const Workflow: React.FC = () => {
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [activeWf, setActiveWf] = useState<any>(null);
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);

  // Test execution state
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);
  const [saveMsg, setSaveMsg] = useState('');

  const loadWorkflows = async () => {
    try {
      const data = (await workflowApi.getWorkflows()) as any;
      setWorkflows(data || []);
      if (data?.length > 0) {
        const first = data[0];
        setActiveWf(first);
        setNodes(first.graph_data?.nodes || []);
        setEdges(first.graph_data?.edges || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadWorkflows();
  }, []);

  const onNodesChange = useCallback(
    (changes: any) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );

  const onEdgesChange = useCallback(
    (changes: any) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge({ ...params, animated: true }, eds)),
    []
  );

  const handleSave = async () => {
    if (!activeWf) return;
    try {
      await workflowApi.updateWorkflow(activeWf.id, {
        graph_data: { nodes, edges },
        is_active: true
      });
      setSaveMsg('工作流编排拓扑已保存生效');
      setTimeout(() => setSaveMsg(''), 3000);
    } catch (e) {
      alert('保存失败');
    }
  };

  const handleRunTest = async () => {
    if (!activeWf) return;
    setTesting(true);
    setTestResult(null);
    try {
      const res = await workflowApi.runTest(activeWf.id, {
        title: '【实时模拟】内网主机向外发起 C2 心跳通信',
        content: '源主机: WS-FINANCE-02, 目的IP: 194.26.29.112:4444, 协议: HTTPS, 行为: 周期性 beacon'
      });
      setTestResult((res as any).result);
    } catch (e: any) {
      alert(e?.message || '测试执行失败');
    } finally {
      setTesting(false);
    }
  };

  const handleAddAgentNode = () => {
    const id = `agent_${Date.now()}`;
    const newNode: Node = {
      id,
      type: 'agent',
      position: { x: 400 + Math.random() * 80, y: 150 + Math.random() * 80 },
      data: {
        label: '自定义安全专家智能体',
        role: 'analyst',
        model: 'deepseek-chat',
        tools: ['lookup_ip_threat_intel']
      }
    };
    setNodes((nds) => [...nds, newNode]);
  };

  return (
    <div className="h-[calc(100vh-6rem)] flex flex-col space-y-4">
      {/* Top action toolbar */}
      <div className="flex items-center justify-between p-4 rounded-2xl bg-[#0f172a]/70 border border-gray-800 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <GitMerge className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-gray-100 flex items-center gap-2">
              <span>{activeWf?.name || '多 Agent 工作流连线编排'}</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                LangGraph 引擎驱动
              </span>
            </h2>
            <p className="text-xs text-gray-500">拖拽节点连线，定义告警事件在多个专业智能体之间的流转逻辑</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {saveMsg && (
            <span className="text-xs text-emerald-400 flex items-center gap-1 bg-emerald-500/10 px-3 py-1.5 rounded-xl border border-emerald-500/20">
              <CheckCircle2 className="w-3.5 h-3.5" />
              {saveMsg}
            </span>
          )}

          <button
            onClick={handleAddAgentNode}
            className="flex items-center gap-1.5 px-3 py-2 bg-gray-900 border border-gray-800 hover:text-white text-gray-300 rounded-xl text-xs font-semibold transition"
          >
            <Plus className="w-4 h-4 text-indigo-400" />
            <span>添加 Agent 节点</span>
          </button>

          <button
            onClick={handleRunTest}
            disabled={testing}
            className="flex items-center gap-1.5 px-4 py-2 bg-blue-600/20 text-blue-400 border border-blue-500/30 hover:bg-blue-600/30 rounded-xl text-xs font-semibold transition disabled:opacity-50"
          >
            <Play className={`w-3.5 h-3.5 ${testing ? 'animate-spin' : ''}`} />
            <span>{testing ? '测试流转中...' : '模拟运行测试'}</span>
          </button>

          <button
            onClick={handleSave}
            className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-indigo-600/20 transition"
          >
            <Save className="w-4 h-4" />
            <span>保存并生效</span>
          </button>
        </div>
      </div>

      {/* Main Canvas Area */}
      <div className="flex-1 flex gap-4 min-h-0 relative">
        <div className="flex-1 rounded-2xl bg-[#090d16] border border-gray-800 overflow-hidden relative shadow-inner">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            onNodeClick={(_, node) => setSelectedNode(node)}
            fitView
          >
            <Background color="#1e293b" gap={20} size={1} />
            <Controls className="!bg-[#0f172a] !border-gray-800 !text-gray-300" />
          </ReactFlow>
        </div>

        {/* Right drawer: Node Configuration */}
        {selectedNode && (
          <div className="w-80 rounded-2xl bg-[#0f172a] border border-gray-800 p-5 flex flex-col space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <div className="flex items-center gap-2">
                <Settings className="w-4 h-4 text-indigo-400" />
                <h3 className="text-sm font-bold text-gray-200">节点参数配置</h3>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-gray-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs overflow-y-auto flex-1">
              <div>
                <label className="text-gray-400 block mb-1">节点名称</label>
                <input
                  type="text"
                  value={selectedNode.data.label as string || ''}
                  onChange={(e) => {
                    const label = e.target.value;
                    setNodes((nds) =>
                      nds.map((n) =>
                        n.id === selectedNode.id ? { ...n, data: { ...n.data, label } } : n
                      )
                    );
                    setSelectedNode((prev: any) => ({
                      ...prev,
                      data: { ...prev.data, label }
                    }));
                  }}
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-xl text-gray-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-gray-400 block mb-1">智能体角色 (Role)</label>
                <select
                  value={selectedNode.data.role as string || 'analyst'}
                  onChange={(e) => {
                    const role = e.target.value;
                    setNodes((nds) =>
                      nds.map((n) =>
                        n.id === selectedNode.id ? { ...n, data: { ...n.data, role } } : n
                      )
                    );
                  }}
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-xl text-gray-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value="supervisor">总控调度智能体 (Supervisor)</option>
                  <option value="analyst">研判分析智能体 (Analyst)</option>
                  <option value="responder">阻断处置智能体 (Responder)</option>
                </select>
              </div>

              <div>
                <label className="text-gray-400 block mb-1">挂载大模型 (LLM Model)</label>
                <input
                  type="text"
                  value={selectedNode.data.model as string || 'deepseek-chat'}
                  onChange={(e) => {
                    const model = e.target.value;
                    setNodes((nds) =>
                      nds.map((n) =>
                        n.id === selectedNode.id ? { ...n, data: { ...n.data, model } } : n
                      )
                    );
                  }}
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-xl text-gray-200 font-mono focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-gray-400 block mb-1">挂载工具与 MCP 权限</label>
                <div className="p-3 rounded-xl bg-gray-900 border border-gray-800 space-y-2">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" defaultChecked className="rounded bg-gray-800" />
                    <span>威胁情报查询 (lookup_ip_threat_intel)</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" defaultChecked className="rounded bg-gray-800" />
                    <span>边缘防火墙阻断 (block_firewall_ip)</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" className="rounded bg-gray-800" />
                    <span>主机网络隔离 (isolate_host_network)</span>
                  </label>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Execution Trace Bottom Drawer */}
        {testResult && (
          <div className="absolute bottom-4 left-4 right-4 max-h-64 bg-[#0f172a]/95 border border-indigo-500/40 rounded-2xl p-5 shadow-2xl overflow-y-auto backdrop-blur-lg">
            <div className="flex items-center justify-between mb-3 border-b border-gray-800 pb-2">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span className="text-sm font-bold text-gray-100">LangGraph 运行轨迹回放</span>
              </div>
              <button
                onClick={() => setTestResult(null)}
                className="text-gray-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <span className="text-blue-400 font-semibold">研判分析结论:</span>
                <p className="mt-1 p-2 bg-gray-900 rounded-lg text-gray-300 font-mono whitespace-pre-wrap">
                  {testResult.analysis_result || '无输出'}
                </p>
              </div>
              <div>
                <span className="text-emerald-400 font-semibold">处置执行回执:</span>
                <p className="mt-1 p-2 bg-gray-900 rounded-lg text-gray-300 font-mono whitespace-pre-wrap">
                  {testResult.action_result || '无输出'}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};



