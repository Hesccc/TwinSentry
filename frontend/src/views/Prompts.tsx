import React, { useState, useEffect } from 'react';
import { Terminal, Save, CheckCircle2, RotateCcw, MessageSquare, Layers } from 'lucide-react';
import { promptApi } from '@/api';

export const Prompts: React.FC = () => {
  const [prompts, setPrompts] = useState<any[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<any>(null);
  const [systemPrompt, setSystemPrompt] = useState('');
  const [saveMsg, setSaveMsg] = useState('');
  const [loading, setLoading] = useState(false);

  const loadPrompts = async () => {
    try {
      const data = (await promptApi.getPrompts()) as any;
      setPrompts(data || []);
      if (data?.length > 0) {
        setSelectedPrompt(data[0]);
        setSystemPrompt(data[0].system_prompt);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadPrompts();
  }, []);

  const handleSelect = (p: any) => {
    setSelectedPrompt(p);
    setSystemPrompt(p.system_prompt);
    setSaveMsg('');
  };

  const handleSave = async () => {
    if (!selectedPrompt) return;
    setLoading(true);
    setSaveMsg('');
    try {
      await promptApi.updatePrompt(selectedPrompt.id, {
        name: selectedPrompt.name,
        system_prompt: systemPrompt
      });
      setSaveMsg('提示词模板已保存并更新生效');
      loadPrompts();
      setTimeout(() => setSaveMsg(''), 3000);
    } catch (e) {
      alert('保存失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-center justify-between p-4 rounded-2xl bg-[#0f172a]/70 border border-gray-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Terminal className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-gray-100">智能体提示词中心 (Prompt Engineering)</h2>
            <p className="text-xs text-gray-500">在线查看与实时修改各阶段 Agent 的系统提示词 (System Prompt)</p>
          </div>
        </div>

        {saveMsg && (
          <span className="text-xs text-emerald-400 flex items-center gap-1 bg-emerald-500/10 px-3 py-1.5 rounded-xl border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            {saveMsg}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Left: Prompt list */}
        <div className="p-4 rounded-2xl bg-[#0f172a]/70 border border-gray-800 space-y-2">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">预设角色模板</h3>
          {prompts.map((p) => (
            <button
              key={p.id}
              onClick={() => handleSelect(p)}
              className={`w-full text-left p-3 rounded-xl text-xs font-medium transition flex items-center justify-between ${
                selectedPrompt?.id === p.id
                  ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
                  : 'text-gray-300 hover:bg-gray-800/40'
              }`}
            >
              <div className="truncate pr-2">
                <div className="font-semibold">{p.name}</div>
                <div className="text-[10px] text-gray-500 mt-0.5 font-mono">{p.agent_code}</div>
              </div>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-400">
                v{p.version}
              </span>
            </button>
          ))}
        </div>

        {/* Right: Prompt Editor */}
        <div className="md:col-span-3 p-6 rounded-2xl bg-[#0f172a]/70 border border-gray-800 space-y-4">
          <div className="flex items-center justify-between border-b border-gray-800 pb-3">
            <div>
              <h3 className="text-sm font-bold text-gray-200">{selectedPrompt?.name || '选择提示词模板'}</h3>
              <p className="text-[11px] text-gray-500 font-mono mt-0.5">
                目标智能体: {selectedPrompt?.agent_code || '-'}
              </p>
            </div>
            <button
              onClick={handleSave}
              disabled={loading}
              className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-indigo-600/20 transition disabled:opacity-50"
            >
              <Save className="w-3.5 h-3.5" />
              <span>保存修改</span>
            </button>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-400 mb-2">
              System Prompt (系统级指令)
            </label>
            <textarea
              rows={16}
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              className="w-full p-4 bg-gray-900/90 border border-gray-800 rounded-xl text-xs text-gray-200 font-mono leading-relaxed focus:outline-none focus:border-indigo-500"
              placeholder="在此输入 Agent 的 System Prompt..."
            />
          </div>

          <div className="p-3 rounded-xl bg-gray-900/60 border border-gray-800 text-[11px] text-gray-400">
            <span className="text-indigo-400 font-semibold block mb-1">支持插值变量说明：</span>
            <span>在后续多轮推理中，可使用 <code className="text-indigo-300">{"{{alert.title}}"}</code>、<code className="text-indigo-300">{"{{alert.text}}"}</code> 动态提取触发告警的关键特征。</span>
          </div>
        </div>
      </div>
    </div>
  );
};



