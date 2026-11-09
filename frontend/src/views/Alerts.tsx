import React, { useState, useEffect } from 'react';
import {
  Search,
  Filter,
  Trash2,
  Eye,
  RefreshCw,
  X,
  Undo2,
  Send,
  ChevronLeft,
  ChevronRight,
  AlertTriangle
} from 'lucide-react';
import { alertsApi } from '@/api';
import type { Alert, AlertStatus } from '@/types';

export const Alerts: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  // Selected alert for modal
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const res = await alertsApi.getAlertsPaginated({
        page,
        per_page: 15,
        status: statusFilter === 'all' ? undefined : statusFilter,
        title: search.trim() || undefined,
      });
      const data = res as any;
      setAlerts(data.items || []);
      setTotalPages(data.pages || 1);
      setTotal(data.total || 0);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, [page, statusFilter]);

  const handleDelete = async (alertId: string) => {
    if (!window.confirm('确认软删除该告警吗？')) return;
    try {
      await alertsApi.deleteAlert(alertId);
      if (selectedAlert?.alert_id === alertId) {
        setSelectedAlert(null);
      }
      fetchAlerts();
    } catch (e) {
      console.error(e);
      alert('删除失败');
    }
  };

  const handleRollback = async (alertId: string) => {
    if (!window.confirm('确认人工回退该告警的状态吗？')) return;
    try {
      await alertsApi.rollbackAlert(alertId);
      fetchAlerts();
      if (selectedAlert?.alert_id === alertId) {
        setSelectedAlert(null);
      }
    } catch (e: any) {
      alert(e?.message || '状态回退失败');
    }
  };

  const handleForward = async (alertId: string, target: 'analysis' | 'action') => {
    try {
      await alertsApi.forwardToOpenclaw(alertId, target);
      alert('已成功派发至外部 OpenClaw 智能体系统');
      fetchAlerts();
    } catch (e: any) {
      alert(e?.message || '外发失败，请确认系统设置中 OpenClaw 配置有效');
    }
  };

  const getStatusBadge = (status: AlertStatus) => {
    switch (status) {
      case '待分析':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">待分析</span>;
      case '分析中':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">分析中</span>;
      case '已分析':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-500/10 text-purple-400 border border-purple-500/20">已分析</span>;
      case '处置中':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">处置中</span>;
      case '已处置':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">已处置</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-500/10 text-gray-400 border border-gray-500/20">{status}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Filters & Actions bar */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-4 p-4 rounded-2xl bg-[#0f172a]/70 border border-gray-800">
        <div className="flex items-center gap-3 w-full md:w-auto">
          {/* Status tabs */}
          <div className="flex items-center p-1 rounded-xl bg-gray-900 border border-gray-800 text-xs">
            {['all', '待分析', '分析中', '已分析', '处置中', '已处置'].map((st) => (
              <button
                key={st}
                onClick={() => {
                  setStatusFilter(st);
                  setPage(1);
                }}
                className={`px-3 py-1.5 rounded-lg font-medium transition ${
                  statusFilter === st
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                {st === 'all' ? '全部' : st}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto justify-end">
          <div className="relative flex-1 md:w-64">
            <Search className="w-4 h-4 text-gray-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="搜索告警标题/内容..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && fetchAlerts()}
              className="w-full pl-10 pr-4 py-2 bg-gray-900/80 border border-gray-800 rounded-xl text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          <button
            onClick={() => fetchAlerts()}
            disabled={loading}
            className="p-2 bg-gray-900 border border-gray-800 rounded-xl text-gray-400 hover:text-white transition disabled:opacity-50"
            title="刷新"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-blue-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Alert Table */}
      <div className="rounded-2xl bg-[#0f172a]/70 border border-gray-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-gray-900/60 border-b border-gray-800 text-gray-400 uppercase font-semibold">
              <tr>
                <th className="px-6 py-3.5">ID / 时间</th>
                <th className="px-6 py-3.5">告警标题</th>
                <th className="px-6 py-3.5">当前阶段</th>
                <th className="px-6 py-3.5">分析摘要</th>
                <th className="px-6 py-3.5 text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60">
              {alerts.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-gray-500">
                    {loading ? '正在加载数据...' : '未检索到匹配告警'}
                  </td>
                </tr>
              ) : (
                alerts.map((alert) => (
                  <tr key={alert.alert_id} className="hover:bg-gray-800/30 transition">
                    <td className="px-6 py-4 font-mono text-gray-400 whitespace-nowrap">
                      <div className="text-gray-300 font-medium">{alert.alert_id.slice(0, 8)}...</div>
                      <div className="text-[10px] text-gray-500">{alert.created_at}</div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="font-medium text-gray-200 max-w-xs truncate" title={alert.title}>
                        {alert.title}
                      </div>
                      <div className="text-[11px] text-gray-500 max-w-sm truncate mt-0.5">
                        {alert.text}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(alert.status)}
                    </td>
                    <td className="px-6 py-4 max-w-xs truncate text-gray-400">
                      {alert.analysis_result ? (
                        <span className="text-gray-300 truncate block">{alert.analysis_result}</span>
                      ) : (
                        <span className="text-gray-600 italic">待分析智能体处理</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1.5">
                        {/* Rollback button if analyzing or processing */}
                        {(alert.status === '分析中' || alert.status === '处置中') && (
                          <button
                            onClick={() => handleRollback(alert.alert_id)}
                            className="p-1.5 rounded-lg bg-amber-600/10 text-amber-400 hover:bg-amber-600/20 transition"
                            title="回退状态"
                          >
                            <Undo2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                        <button
                          onClick={() => setSelectedAlert(alert)}
                          className="p-1.5 rounded-lg bg-blue-600/10 text-blue-400 hover:bg-blue-600/20 transition"
                          title="查看详情"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDelete(alert.alert_id)}
                          className="p-1.5 rounded-lg bg-red-600/10 text-red-400 hover:bg-red-600/20 transition"
                          title="软删除"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination bar */}
        <div className="px-6 py-3 border-t border-gray-800 flex items-center justify-between text-xs text-gray-400">
          <div>
            共 <span className="font-semibold text-gray-200">{total}</span> 条告警记录
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="p-1.5 rounded-lg bg-gray-900 border border-gray-800 hover:text-white disabled:opacity-40 transition"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="px-2">
              第 {page} / {totalPages} 页
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="p-1.5 rounded-lg bg-gray-900 border border-gray-800 hover:text-white disabled:opacity-40 transition"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Alert Details Modal */}
      {selectedAlert && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-2xl bg-[#0f172a] border border-gray-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-gray-100">告警全流程详情</h3>
                {getStatusBadge(selectedAlert.status)}
              </div>
              <button
                onClick={() => setSelectedAlert(null)}
                className="p-1.5 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-5 text-xs text-gray-300">
              <div>
                <span className="text-gray-500 block mb-1">告警 ID</span>
                <span className="font-mono text-gray-200 select-all">{selectedAlert.alert_id}</span>
              </div>
              <div>
                <span className="text-gray-500 block mb-1">标题</span>
                <span className="font-semibold text-gray-100 text-sm">{selectedAlert.title}</span>
              </div>
              <div>
                <span className="text-gray-500 block mb-1">原始 Payload / 结构化文本</span>
                <pre className="p-3 rounded-xl bg-gray-900/80 border border-gray-800 font-mono text-[11px] whitespace-pre-wrap">
                  {selectedAlert.text}
                </pre>
              </div>

              {/* Analysis Result */}
              <div>
                <span className="text-blue-400 font-semibold block mb-1">智能体研判分析结果</span>
                <div className="p-3 rounded-xl bg-blue-950/20 border border-blue-900/30 text-gray-200">
                  {selectedAlert.analysis_result || '尚待分析智能体处理'}
                </div>
              </div>

              {/* Disposition Result */}
              <div>
                <span className="text-emerald-400 font-semibold block mb-1">处置执行结果</span>
                <div className="p-3 rounded-xl bg-emerald-950/20 border border-emerald-900/30 text-gray-200">
                  {selectedAlert.disposition_result || '尚待处置智能体执行'}
                </div>
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-800 bg-gray-900/40 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleForward(selectedAlert.alert_id, 'analysis')}
                  className="px-3 py-1.5 rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 hover:bg-indigo-600/30 transition text-xs flex items-center gap-1.5"
                >
                  <Send className="w-3 h-3" />
                  <span>派发给 OpenClaw 分析</span>
                </button>
                <button
                  onClick={() => handleForward(selectedAlert.alert_id, 'action')}
                  className="px-3 py-1.5 rounded-xl bg-purple-600/20 text-purple-400 border border-purple-500/30 hover:bg-purple-600/30 transition text-xs flex items-center gap-1.5"
                >
                  <Send className="w-3 h-3" />
                  <span>派发给 OpenClaw 处置</span>
                </button>
              </div>
              <button
                onClick={() => setSelectedAlert(null)}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-xl text-xs font-medium transition"
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

