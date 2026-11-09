import React, { useState, useEffect } from 'react';
import { FileText, Search, RefreshCw, ChevronLeft, ChevronRight, ShieldCheck, Activity } from 'lucide-react';
import { auditApi } from '@/api';
import type { AuditLogItem } from '@/types';

export const Audit: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const res = await auditApi.getLogs({ page, per_page: 15 });
      const data = res as any;
      setLogs(data.items || []);
      setTotalPages(data.pages || 1);
      setTotal(data.total || 0);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [page]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between p-4 rounded-2xl bg-[#0f172a]/70 border border-gray-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-gray-100">审计与操作轨迹</h2>
            <p className="text-xs text-gray-500">记录系统用户与 Agent 关键操作及调用日志</p>
          </div>
        </div>
        <button
          onClick={() => fetchLogs()}
          disabled={loading}
          className="p-2 bg-gray-900 border border-gray-800 rounded-xl text-gray-400 hover:text-white transition disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-purple-400' : ''}`} />
        </button>
      </div>

      <div className="rounded-2xl bg-[#0f172a]/70 border border-gray-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-gray-900/60 border-b border-gray-800 text-gray-400 uppercase font-semibold">
              <tr>
                <th className="px-6 py-3.5">时间</th>
                <th className="px-6 py-3.5">主体 / IP</th>
                <th className="px-6 py-3.5">操作类型</th>
                <th className="px-6 py-3.5">详细信息</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-12 text-center text-gray-500">
                    {loading ? '正在加载审计日志...' : '暂无审计日志'}
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-800/30 transition">
                    <td className="px-6 py-4 font-mono text-gray-400 whitespace-nowrap">
                      {log.created_at}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="font-semibold text-gray-200">{log.username || 'Agent/System'}</span>
                      <span className="text-[10px] text-gray-500 block font-mono">{log.ip_address || '-'}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
                        {log.action}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-gray-300 font-mono text-[11px] max-w-md truncate">
                      {log.details || '-'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="px-6 py-3 border-t border-gray-800 flex items-center justify-between text-xs text-gray-400">
          <div>共 {total} 条审计记录</div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="p-1.5 rounded-lg bg-gray-900 border border-gray-800 hover:text-white disabled:opacity-40 transition"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="px-2">第 {page} / {totalPages} 页</span>
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
    </div>
  );
};

