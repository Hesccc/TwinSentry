import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Bell, Key, Save, Send, CheckCircle2 } from 'lucide-react';
import { settingsApi } from '@/api';
import type { SystemSettings } from '@/types';

export const Settings: React.FC = () => {
  const [settings, setSettings] = useState<Partial<SystemSettings>>({});
  const [channels, setChannels] = useState<any>({});
  const [loading, setLoading] = useState(false);
  const [savedMsg, setSavedMsg] = useState('');
  const [testResult, setTestResult] = useState('');

  const loadData = async () => {
    try {
      const s = await settingsApi.getSystemSettings();
      setSettings(s as any);
      const c = await settingsApi.getNotificationChannels();
      setChannels(c as any);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setSavedMsg('');
    try {
      await settingsApi.updateSystemSettings(settings);
      setSavedMsg('系统配置更新成功');
      setTimeout(() => setSavedMsg(''), 3000);
    } catch (e) {
      alert('保存失败');
    } finally {
      setLoading(false);
    }
  };

  const handleTestChannel = async (type: string) => {
    setTestResult('测试发送中...');
    try {
      const res = await settingsApi.testNotification(type, channels[type] || {});
      setTestResult((res as any).message || '测试通过');
    } catch (e: any) {
      setTestResult(e?.message || '测试调用失败');
    }
  };

  return (
    <div className="max-w-4xl space-y-6">
      <div className="flex items-center justify-between p-4 rounded-2xl bg-[#0f172a]/70 border border-gray-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <SettingsIcon className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-gray-100">系统全局参数与通道配置</h2>
            <p className="text-xs text-gray-500">配置智能体认证密钥、超时阈值与外部告警推送通道</p>
          </div>
        </div>

        {savedMsg && (
          <div className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-lg">
            <CheckCircle2 className="w-4 h-4" />
            <span>{savedMsg}</span>
          </div>
        )}
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* Agent Keys & Base Settings */}
        <div className="p-6 rounded-2xl bg-[#0f172a]/70 border border-gray-800 space-y-4">
          <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2 border-b border-gray-800 pb-3">
            <Key className="w-4 h-4 text-blue-400" />
            智能体鉴权与策略 (Agent Keys)
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block text-gray-400 mb-1.5 font-medium">分析智能体密钥 (ANALYSIS_AGENT_KEY)</label>
              <input
                type="text"
                value={settings.ANALYSIS_AGENT_KEY || ''}
                onChange={(e) => setSettings({ ...settings, ANALYSIS_AGENT_KEY: e.target.value })}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-xl text-gray-200 font-mono focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-gray-400 mb-1.5 font-medium">处置智能体密钥 (ACTION_AGENT_KEY)</label>
              <input
                type="text"
                value={settings.ACTION_AGENT_KEY || ''}
                onChange={(e) => setSettings({ ...settings, ACTION_AGENT_KEY: e.target.value })}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-xl text-gray-200 font-mono focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-gray-400 mb-1.5 font-medium">告警去重策略 (DEDUP_STRATEGY)</label>
              <select
                value={settings.DEDUP_STRATEGY || 'title'}
                onChange={(e) => setSettings({ ...settings, DEDUP_STRATEGY: e.target.value as any })}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-xl text-gray-200 focus:border-blue-500 focus:outline-none"
              >
                <option value="title">仅标题去重 (Title Only)</option>
                <option value="title_content">标题 + 内容组合去重 (Title + Content)</option>
              </select>
            </div>

            <div>
              <label className="block text-gray-400 mb-1.5 font-medium">超时报警阈值 (分钟)</label>
              <input
                type="number"
                value={settings.NOTIFY_TIMEOUT_MINUTES || 20}
                onChange={(e) => setSettings({ ...settings, NOTIFY_TIMEOUT_MINUTES: Number(e.target.value) })}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-xl text-gray-200 focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>
        </div>

        {/* Webhook Notifications */}
        <div className="p-6 rounded-2xl bg-[#0f172a]/70 border border-gray-800 space-y-4">
          <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2 border-b border-gray-800 pb-3">
            <Bell className="w-4 h-4 text-purple-400" />
            第三方告警通知渠道
          </h3>

          <div className="space-y-4 text-xs">
            <div>
              <label className="block text-gray-400 mb-1.5 font-medium">企业微信机器人 Webhook</label>
              <input
                type="text"
                value={settings.WECHAT_WEBHOOK || ''}
                onChange={(e) => setSettings({ ...settings, WECHAT_WEBHOOK: e.target.value })}
                placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."
                className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-xl text-gray-200 font-mono focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-gray-400 mb-1.5 font-medium">飞书机器人 Webhook</label>
              <input
                type="text"
                value={settings.FEISHU_WEBHOOK || ''}
                onChange={(e) => setSettings({ ...settings, FEISHU_WEBHOOK: e.target.value })}
                placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..."
                className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-xl text-gray-200 font-mono focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-gray-400 mb-1.5 font-medium">自定义通知 Webhook</label>
              <input
                type="text"
                value={settings.CUSTOM_WEBHOOK || ''}
                onChange={(e) => setSettings({ ...settings, CUSTOM_WEBHOOK: e.target.value })}
                placeholder="https://your-soc-api.example.com/alerts"
                className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-xl text-gray-200 font-mono focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end">
          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-blue-600/20 transition disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            <span>保存全部系统配置</span>
          </button>
        </div>
      </form>
    </div>
  );
};

