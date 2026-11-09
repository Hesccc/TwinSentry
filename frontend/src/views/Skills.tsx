import React, { useState, useEffect } from 'react';
import { Sparkles, Download, Copy, Check, Terminal, ExternalLink, Code } from 'lucide-react';
import { skillsApi } from '@/api';

export const Skills: React.FC = () => {
  const [config, setConfig] = useState<any>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  useEffect(() => {
    skillsApi.getConfig().then((res) => setConfig(res as any)).catch(console.error);
  }, []);

  const copyText = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(id);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  return (
    <div className="max-w-4xl space-y-6">
      <div className="flex items-center justify-between p-4 rounded-2xl bg-[#0f172a]/70 border border-gray-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-gray-100">Skills Center (智能体接入中心)</h2>
            <p className="text-xs text-gray-500">为 Dify、LangChain、AutoGPT 等框架提供即插即用的 Agent 技能包</p>
          </div>
        </div>

        <a
          href={skillsApi.getDownloadUrl()}
          download
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-indigo-600/20 transition"
        >
          <Download className="w-4 h-4" />
          <span>下载集成包 (ZIP)</span>
        </a>
      </div>

      {/* Integration Credentials Info */}
      <div className="p-6 rounded-2xl bg-[#0f172a]/70 border border-gray-800 space-y-4">
        <h3 className="text-sm font-semibold text-gray-200 border-b border-gray-800 pb-3">当前服务端接入上下文</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
          <div className="p-3 bg-gray-900/80 rounded-xl border border-gray-800">
            <span className="text-gray-500 block mb-1 text-[10px]">服务根地址 (BASE_URL)</span>
            <div className="flex items-center justify-between text-gray-200">
              <span className="truncate">{config?.base_url || 'http://127.0.0.1:5000'}</span>
              <button
                onClick={() => copyText(config?.base_url || 'http://127.0.0.1:5000', 'url')}
                className="text-gray-400 hover:text-white ml-2"
              >
                {copiedKey === 'url' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          <div className="p-3 bg-gray-900/80 rounded-xl border border-gray-800">
            <span className="text-gray-500 block mb-1 text-[10px]">分析 Agent 密钥 (ANALYSIS_KEY)</span>
            <div className="flex items-center justify-between text-gray-200">
              <span className="truncate">{config?.analysis_key ? '••••••••' : '-'}</span>
              <button
                onClick={() => copyText(config?.analysis_key || '', 'an_key')}
                className="text-gray-400 hover:text-white ml-2"
              >
                {copiedKey === 'an_key' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          <div className="p-3 bg-gray-900/80 rounded-xl border border-gray-800">
            <span className="text-gray-500 block mb-1 text-[10px]">处置 Agent 密钥 (ACTION_KEY)</span>
            <div className="flex items-center justify-between text-gray-200">
              <span className="truncate">{config?.action_key ? '••••••••' : '-'}</span>
              <button
                onClick={() => copyText(config?.action_key || '', 'act_key')}
                className="text-gray-400 hover:text-white ml-2"
              >
                {copiedKey === 'act_key' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Dify / LangChain Guide */}
      <div className="p-6 rounded-2xl bg-[#0f172a]/70 border border-gray-800 space-y-4">
        <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
          <Terminal className="w-4 h-4 text-emerald-400" />
          快捷接入指引
        </h3>
        <p className="text-xs text-gray-400 leading-relaxed">
          下载 ZIP 包后，包内已自动将本服务器地址及专属 Key 注入到配置文件中：
        </p>
        <ul className="list-disc pl-5 text-xs text-gray-400 space-y-2">
          <li>
            <strong className="text-gray-200">Dify 框架</strong>: 将 <code className="text-blue-400 bg-gray-900 px-1.5 py-0.5 rounded">twinsentry_dify.yaml</code> 导入 Dify 自定义工具中即可。
          </li>
          <li>
            <strong className="text-gray-200">Python / LangChain</strong>: 直接执行 <code className="text-blue-400 bg-gray-900 px-1.5 py-0.5 rounded">python -m analysis_agent</code> 或使用包装好的 Tool Class。
          </li>
        </ul>
      </div>
    </div>
  );
};

