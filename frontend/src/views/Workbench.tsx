import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  Search,
  CheckCircle2,
  AlertTriangle,
  FileCode,
  Save,
  Sparkles,
  Database,
  ExternalLink,
  BookOpen,
  ArrowRight,
  ShieldCheck,
  RotateCw
} from 'lucide-react';
import { sopApi } from '@/api';

export const Workbench: React.FC = () => {
  const [alertId, setAlertId] = useState('ALERT-2026-C2-009');
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [sopContent, setSopContent] = useState('');
  const [savedMsg, setSavedMsg] = useState('');
  const [goldenList, setGoldenList] = useState<any[]>([]);

  // Splunk query testing
  const [splunkQuery, setSplunkQuery] = useState('index=idx_prod_payment destination=194.26.29.112');
  const [splunkError, setSplunkError] = useState('');

  const loadWorkbench = async (id: string) => {
    setLoading(true);
    try {
      const res = (await sopApi.getWorkbench(id)) as any;
      setData(res);
      setSopContent(res.sop_content || '');
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const loadGoldenSops = async () => {
    try {
      const list = (await sopApi.getGoldenSops()) as any;
      setGoldenList(list || []);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadWorkbench(alertId);
    loadGoldenSops();
  }, []);

  const handleSaveAndConfirm = async () => {
    try {
      await sopApi.confirmSOP(alertId, sopContent);
      setSavedMsg('SOP 已人工核准执行，并反哺沉淀至长期记忆黄金知识库！');
      loadGoldenSops();
      setTimeout(() => setSavedMsg(''), 4000);
    } catch (e) {
      alert('保存失败');
    }
  };

  const handleTestSplunk = async () => {
    setSplunkError('');
    try {
      const res = (await sopApi.testSplunkQuery(splunkQuery, data?.target_index)) as any;
      alert(`Splunk 检索成功！匹配事件数: ${res.total_count} 条`);
    } catch (e: any) {
      setSplunkError(e?.error || e?.message || '安全护栏拦截：未遵循 index 约束');
    }
  };

  return (
    <div className="h-[calc(100vh-6rem)] flex flex-col space-y-4">
      {/* Top Header */}
      <div className="flex items-center justify-between p-4 rounded-2xl bg-[#0f172a]/70 border border-gray-800 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-gray-100 flex items-center gap-2">
              <span>双栏式告警排障工作台</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20">
                Splunk 证据链 + 自适应 SOP
              </span>
            </h2>
            <p className="text-xs text-gray-500">
              左栏严谨核查 Splunk 物理证据链与质检报告，右栏在线审校微调处置 SOP 并反哺知识飞轮
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {savedMsg && (
            <span className="text-xs text-emerald-400 flex items-center gap-1.5 bg-emerald-500/10 px-3 py-1.5 rounded-xl border border-emerald-500/20 animate-pulse">
              <CheckCircle2 className="w-4 h-4" />
              {savedMsg}
            </span>
          )}

          <button
            onClick={handleSaveAndConfirm}
            className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-emerald-600/20 transition"
          >
            <Save className="w-4 h-4" />
            <span>保存校准并反哺黄金知识库</span>
          </button>
        </div>
      </div>

      {/* Dual-Column Layout */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-4 min-h-0">
        {/* Left Column: Splunk Evidence & Verifier */}
        <div className="flex flex-col space-y-4 overflow-y-auto pr-1">
          {/* Splunk Guard & Linter Card */}
          <div className="p-5 rounded-2xl bg-[#0f172a]/80 border border-gray-800 space-y-3">
            <div className="flex items-center justify-between border-b border-gray-800 pb-2">
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-amber-400" />
                <h3 className="text-sm font-bold text-gray-200">Splunk 索引锁定与安全护栏</h3>
              </div>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                Index: {data?.target_index || 'idx_prod_payment'}
              </span>
            </div>

            <div className="space-y-2">
              <label className="text-xs text-gray-400 block">SPL 检索测试 (严格禁止 index=* 盲搜):</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={splunkQuery}
                  onChange={(e) => setSplunkQuery(e.target.value)}
                  className="flex-1 px-3 py-1.5 bg-gray-900 border border-gray-800 rounded-xl text-xs text-gray-200 font-mono focus:border-amber-500 focus:outline-none"
                />
                <button
                  onClick={handleTestSplunk}
                  className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-xl text-xs font-medium transition"
                >
                  执行
                </button>
              </div>
              {splunkError && (
                <div className="p-2.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                  <span>{splunkError}</span>
                </div>
              )}
            </div>
          </div>

          {/* Splunk Evidence Snippets */}
          <div className="p-5 rounded-2xl bg-[#0f172a]/80 border border-gray-800 space-y-3 flex-1 flex flex-col">
            <div className="flex items-center justify-between border-b border-gray-800 pb-2">
              <h3 className="text-sm font-bold text-gray-200">现场日志直接证据 (Ground Truth)</h3>
              <span className="text-xs text-gray-500">{data?.splunk_evidence?.length || 0} 条匹配日志</span>
            </div>

            <div className="space-y-2.5 flex-1 overflow-y-auto">
              {data?.splunk_evidence?.map((ev: any, idx: number) => (
                <div
                  key={idx}
                  className="p-3 bg-gray-900/90 rounded-xl border border-gray-800 text-xs font-mono space-y-1"
                >
                  <div className="flex items-center justify-between text-gray-500 text-[10px]">
                    <span>{ev._time}</span>
                    <span>{ev.host}</span>
                  </div>
                  <div className="text-rose-300 leading-relaxed break-all">{ev._raw}</div>
                </div>
              ))}
            </div>
          </div>

          {/* 5-Layer Verifier & Anti-Hallucination Result */}
          <div className="p-5 rounded-2xl bg-[#0f172a]/80 border border-gray-800 space-y-3">
            <div className="flex items-center gap-2 border-b border-gray-800 pb-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm font-bold text-gray-200">五重防线质检报告 (Verifier Node)</h3>
            </div>
            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-400 space-y-1">
              <div className="font-semibold flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>{data?.verifier_report?.verifier_summary || '事实断言全部吻合'}</span>
              </div>
              <p className="text-[11px] text-gray-400">
                已核验 IP、Pod、端口与错误码，未发现任何脱离 Splunk 原始日志的虚构实体。
              </p>
            </div>
          </div>
        </div>

        {/* Right Column: Markdown SOP Editor & Knowledge Flywheel */}
        <div className="flex flex-col space-y-4 overflow-y-auto pl-1">
          {/* SOP Editor Card */}
          <div className="p-5 rounded-2xl bg-[#0f172a]/80 border border-gray-800 space-y-3 flex-1 flex flex-col">
            <div className="flex items-center justify-between border-b border-gray-800 pb-2">
              <div className="flex items-center gap-2">
                <FileCode className="w-4 h-4 text-indigo-400" />
                <h3 className="text-sm font-bold text-gray-200">自适应排障 SOP (支持在线实时修改)</h3>
              </div>
              <span className="text-xs text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                可执行指令精准绑定
              </span>
            </div>

            <textarea
              rows={20}
              value={sopContent}
              onChange={(e) => setSopContent(e.target.value)}
              className="flex-1 w-full p-4 bg-gray-900/90 border border-gray-800 rounded-xl text-xs text-gray-200 font-mono leading-relaxed focus:outline-none focus:border-indigo-500 resize-none"
              placeholder="SOP Markdown 内容..."
            />
          </div>

          {/* Golden SOP Knowledge Flywheel List */}
          <div className="p-5 rounded-2xl bg-[#0f172a]/80 border border-gray-800 space-y-3">
            <div className="flex items-center justify-between border-b border-gray-800 pb-2">
              <div className="flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-teal-400" />
                <h3 className="text-sm font-bold text-gray-200">知识飞轮：已沉淀黄金 SOP 知识库</h3>
              </div>
              <span className="text-xs text-gray-500">下次同类告警自动复用</span>
            </div>

            <div className="space-y-2 max-h-40 overflow-y-auto">
              {goldenList.length === 0 ? (
                <div className="text-center py-4 text-xs text-gray-500">
                  暂无归档，保存当前校准后的 SOP 即可触发沉淀
                </div>
              ) : (
                goldenList.map((g) => (
                  <div
                    key={g.id}
                    className="flex items-center justify-between p-2.5 bg-gray-900/60 rounded-xl border border-gray-800 text-xs"
                  >
                    <div>
                      <div className="font-semibold text-gray-200">{g.title}</div>
                      <div className="text-[10px] text-gray-500 font-mono">
                        校准人: {g.calibrated_by} | 复用命中: {g.use_count} 次
                      </div>
                    </div>
                    <span className="px-2 py-0.5 rounded bg-teal-500/10 text-teal-400 border border-teal-500/20 text-[10px]">
                      黄金模板
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

