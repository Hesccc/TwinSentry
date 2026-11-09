import React, { useEffect, useState, useRef } from 'react';
import {
  ShieldAlert,
  Filter,
  AlertTriangle,
  RotateCw,
  CheckCircle2,
  Clock,
  Layers,
  Activity
} from 'lucide-react';
import * as echarts from 'echarts';
import { statsApi } from '@/api';
import type { DashboardStats } from '@/types';

export const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  const trendChartRef = useRef<HTMLDivElement>(null);
  const statusChartRef = useRef<HTMLDivElement>(null);

  const fetchStats = async () => {
    try {
      const data = await statsApi.getDashboardStats();
      setStats(data as any);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  // Initialize and update ECharts
  useEffect(() => {
    if (!stats) return;

    // 1. Trend chart
    let trendChart: echarts.ECharts | null = null;
    if (trendChartRef.current) {
      trendChart = echarts.init(trendChartRef.current);
      const hours = stats.trend_data?.hours || [];
      const collected = stats.trend_data?.collected || [];
      const generated = stats.trend_data?.generated || [];
      const disposed = stats.trend_data?.disposed || [];

      trendChart.setOption({
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'axis',
          backgroundColor: '#1f2937',
          borderColor: '#374151',
          textStyle: { color: '#f3f4f6' }
        },
        legend: {
          data: ['采集总数', '生成告警', '已处置'],
          textStyle: { color: '#9ca3af' },
          top: 0,
          right: 10
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '3%',
          top: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: hours,
          axisLine: { lineStyle: { color: '#374151' } },
          axisLabel: { color: '#9ca3af', fontSize: 11 }
        },
        yAxis: {
          type: 'value',
          splitLine: { lineStyle: { color: '#1f2937' } },
          axisLabel: { color: '#9ca3af', fontSize: 11 }
        },
        series: [
          {
            name: '采集总数',
            type: 'line',
            smooth: true,
            data: collected,
            itemStyle: { color: '#3b82f6' },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
                { offset: 1, color: 'rgba(59, 130, 246, 0.0)' }
              ])
            }
          },
          {
            name: '生成告警',
            type: 'line',
            smooth: true,
            data: generated,
            itemStyle: { color: '#eab308' }
          },
          {
            name: '已处置',
            type: 'line',
            smooth: true,
            data: disposed,
            itemStyle: { color: '#10b981' }
          }
        ]
      });
    }

    // 2. Status Donut chart
    let statusChart: echarts.ECharts | null = null;
    if (statusChartRef.current) {
      statusChart = echarts.init(statusChartRef.current);
      const dist = stats.status_distribution || [];
      statusChart.setOption({
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'item',
          backgroundColor: '#1f2937',
          borderColor: '#374151',
          textStyle: { color: '#f3f4f6' }
        },
        legend: {
          orient: 'vertical',
          bottom: 10,
          left: 'center',
          textStyle: { color: '#9ca3af' }
        },
        series: [
          {
            name: '状态分布',
            type: 'pie',
            radius: ['45%', '70%'],
            avoidLabelOverlap: false,
            itemStyle: {
              borderRadius: 8,
              borderColor: '#0f172a',
              borderWidth: 2
            },
            label: { show: false },
            emphasis: {
              label: {
                show: true,
                fontSize: 14,
                fontWeight: 'bold',
                color: '#f3f4f6'
              }
            },
            data: dist.map((item) => {
              let color = '#3b82f6';
              if (item.name === '待分析') color = '#eab308';
              if (item.name === '分析中') color = '#6366f1';
              if (item.name === '已分析') color = '#a855f7';
              if (item.name === '处置中') color = '#06b6d4';
              if (item.name === '已处置') color = '#10b981';
              return { ...item, itemStyle: { color } };
            })
          }
        ]
      });
    }

    const handleResize = () => {
      trendChart?.resize();
      statusChart?.resize();
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      trendChart?.dispose();
      statusChart?.dispose();
    };
  }, [stats]);

  const cards = [
    { title: '采集总数', value: stats?.raw_count ?? 0, icon: ShieldAlert, color: 'from-blue-600/20 to-blue-900/30 text-blue-400 border-blue-500/20' },
    { title: '去重拦截', value: stats?.dedup_count ?? 0, icon: Filter, color: 'from-purple-600/20 to-purple-900/30 text-purple-400 border-purple-500/20' },
    { title: '待分析', value: stats?.pending_count ?? 0, icon: Clock, color: 'from-amber-600/20 to-amber-900/30 text-amber-400 border-amber-500/20' },
    { title: '严重告警', value: stats?.active_count ?? 0, icon: AlertTriangle, color: 'from-rose-600/20 to-rose-900/30 text-rose-400 border-rose-500/20' },
    { title: '处理中', value: stats?.processing_count ?? 0, icon: RotateCw, color: 'from-cyan-600/20 to-cyan-900/30 text-cyan-400 border-cyan-500/20' },
    { title: '已处置', value: stats?.processed_count ?? 0, icon: CheckCircle2, color: 'from-emerald-600/20 to-emerald-900/30 text-emerald-400 border-emerald-500/20' },
  ];

  return (
    <div className="space-y-6">
      {/* Top Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {cards.map((card, i) => {
          const Icon = card.icon;
          return (
            <div
              key={i}
              className={`p-5 rounded-2xl bg-gradient-to-br border backdrop-blur-sm relative overflow-hidden transition-all hover:scale-[1.02] ${card.color}`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">{card.title}</span>
                <Icon className="w-5 h-5 opacity-80" />
              </div>
              <div className="text-2xl font-bold tracking-tight text-white">{card.value}</div>
            </div>
          );
        })}
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Trend Chart (2 cols) */}
        <div className="lg:col-span-2 p-6 rounded-2xl bg-[#0f172a]/70 border border-gray-800">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-semibold text-gray-200 flex items-center gap-2">
              <Activity className="w-4 h-4 text-blue-400" />
              告警趋势综合分析 (24h)
            </h3>
            <span className="text-xs text-gray-500">动态自动刷新</span>
          </div>
          <div ref={trendChartRef} className="w-full h-80" />
        </div>

        {/* Status Distribution (1 col) */}
        <div className="p-6 rounded-2xl bg-[#0f172a]/70 border border-gray-800">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-semibold text-gray-200 flex items-center gap-2">
              <Layers className="w-4 h-4 text-indigo-400" />
              状态分布
            </h3>
          </div>
          <div ref={statusChartRef} className="w-full h-80" />
        </div>
      </div>

      {/* Bottom section: Top Alerts & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Alerts */}
        <div className="p-6 rounded-2xl bg-[#0f172a]/70 border border-gray-800">
          <h3 className="text-base font-semibold text-gray-200 mb-4">Top 告警类型</h3>
          <div className="space-y-3">
            {stats?.top_alerts?.length ? (
              stats.top_alerts.map((alert, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between p-3 rounded-xl bg-gray-900/60 border border-gray-800/80"
                >
                  <span className="text-sm text-gray-300 truncate max-w-[80%]">{alert.title}</span>
                  <span className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
                    {alert.count} 次
                  </span>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-sm text-gray-500">暂无告警数据</div>
            )}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="p-6 rounded-2xl bg-[#0f172a]/70 border border-gray-800">
          <h3 className="text-base font-semibold text-gray-200 mb-4">最近活动轨迹</h3>
          <div className="space-y-3">
            {stats?.recent_activities?.length ? (
              stats.recent_activities.map((act, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between p-3 rounded-xl bg-gray-900/60 border border-gray-800/80 text-xs"
                >
                  <div className="flex flex-col">
                    <span className="text-gray-300 font-medium">{act.action}</span>
                    <span className="text-gray-500 truncate max-w-[200px]">{act.target}</span>
                  </div>
                  <span className="text-gray-500 font-mono">{act.time}</span>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-sm text-gray-500">暂无活动记录</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

