import React, { useState } from 'react';
import { User as UserIcon, Lock, Save, CheckCircle2 } from 'lucide-react';
import { authApi } from '@/api';

export const Profile: React.FC = () => {
  const userStr = localStorage.getItem('ts_user');
  const user = userStr ? JSON.parse(userStr) : null;

  const [username, setUsername] = useState(user?.username || 'admin');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState('');

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMsg('');
    try {
      const res = await authApi.updateProfile({
        username,
        password: password.trim() ? password : undefined,
      });
      setMsg('资料已更新');
      const updatedUser = { ...user, username };
      localStorage.setItem('ts_user', JSON.stringify(updatedUser));
      setTimeout(() => setMsg(''), 3000);
    } catch (e: any) {
      alert(e?.message || '更新失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-xl space-y-6">
      <div className="flex items-center justify-between p-4 rounded-2xl bg-[#0f172a]/70 border border-gray-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <UserIcon className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-gray-100">管理员个人中心</h2>
            <p className="text-xs text-gray-500">修改登录凭证与个人安全选项</p>
          </div>
        </div>
      </div>

      {msg && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl flex items-center gap-2 text-xs text-emerald-400">
          <CheckCircle2 className="w-4 h-4" />
          <span>{msg}</span>
        </div>
      )}

      <form onSubmit={handleUpdate} className="p-6 rounded-2xl bg-[#0f172a]/70 border border-gray-800 space-y-4">
        <div>
          <label className="block text-xs font-semibold text-gray-400 mb-2">登录用户名</label>
          <input
            type="text"
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-xl text-xs text-gray-200 focus:outline-none focus:border-blue-500"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-400 mb-2">新密码 (留空则不修改)</label>
          <input
            type="password"
            placeholder="若不修改密码请留空"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-xl text-xs text-gray-200 focus:outline-none focus:border-blue-500"
          />
        </div>

        <div className="pt-2">
          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold transition disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            <span>保存变更</span>
          </button>
        </div>
      </form>
    </div>
  );
};

