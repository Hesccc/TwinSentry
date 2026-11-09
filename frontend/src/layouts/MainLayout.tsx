import React from 'react';
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom';
import {
  ShieldAlert,
  Wrench,
  GitMerge,
  Terminal,
  LayoutDashboard,
  BellRing,
  Settings,
  FileText,
  User,
  LogOut,
  Sparkles
} from 'lucide-react';
import { authApi } from '@/api';

export const MainLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const userStr = localStorage.getItem('ts_user');
  const user = userStr ? JSON.parse(userStr) : null;

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch (e) {
      // ignore
    } finally {
      localStorage.removeItem('ts_token');
      localStorage.removeItem('ts_user');
      navigate('/login');
    }
  };

    const navItems = [
    { name: '告警概览', path: '/', icon: LayoutDashboard },
    { name: '实时告警', path: '/alerts', icon: BellRing },
    { name: '排障工作台', path: '/workbench', icon: Wrench },
    { name: '工作流编排', path: '/workflow', icon: GitMerge },
    { name: '提示词管理', path: '/prompts', icon: Terminal },
    { name: 'Skills 中心', path: '/skills', icon: Sparkles },
    { name: '审计监控', path: '/audit', icon: FileText },
    { name: '系统设置', path: '/settings', icon: Settings },
  ];

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#0b0f19] text-gray-100">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 flex flex-col border-r border-gray-800 bg-[#0f172a]/80 backdrop-blur">
        {/* Brand */}
        <div className="flex items-center gap-3 px-6 py-5 border-b border-gray-800">
          <div className="p-2 rounded-xl bg-blue-600/20 text-blue-400 border border-blue-500/30">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-lg font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
              TwinSentry
            </h1>
            <p className="text-xs text-gray-400">安全告警智能闭环中枢</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-blue-600/15 text-blue-400 border border-blue-500/20 shadow-sm'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* User bar */}
        <div className="p-4 border-t border-gray-800 flex items-center justify-between">
          <NavLink
            to="/profile"
            className="flex items-center gap-3 text-sm text-gray-300 hover:text-white transition group"
          >
            <div className="w-8 h-8 rounded-full bg-gray-800 border border-gray-700 flex items-center justify-center text-blue-400 overflow-hidden">
              {user?.avatar ? (
                <img src={user.avatar} alt="avatar" className="w-full h-full object-cover" />
              ) : (
                <User className="w-4 h-4" />
              )}
            </div>
            <div className="flex flex-col">
              <span className="font-medium group-hover:text-blue-400 transition truncate max-w-[100px]">
                {user?.username || '管理员'}
              </span>
              <span className="text-[10px] text-gray-500">已登录</span>
            </div>
          </NavLink>
          <button
            onClick={handleLogout}
            title="退出登录"
            className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header */}
        <header className="h-14 border-b border-gray-800 bg-[#0f172a]/50 flex items-center justify-between px-8">
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <span>状态:</span>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              Agent 节点就绪
            </span>
          </div>
          <div className="text-xs text-gray-500">
            双阶段分析与处置引擎已激活
          </div>
        </header>

        {/* Content Outlet */}
        <main className="flex-1 overflow-y-auto p-8 bg-[#0b0f19]">
          <Outlet />
        </main>
      </div>
    </div>
  );
};





