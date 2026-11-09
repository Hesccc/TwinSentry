import client from './client';
import type { User, DashboardStats, Alert, AuditLogItem, SystemSettings } from '@/types';

export const authApi = {
  login: (data: { username: string; password: string }) =>
    client.post<{ token: string; user: User }>('/api/auth/login', data),
  logout: () => client.post('/api/auth/logout'),
  getProfile: () => client.get<User>('/api/auth/profile'),
  updateProfile: (data: { username?: string; password?: string }) =>
    client.put<{ message: string; user: User }>('/api/auth/profile', data),
  uploadAvatar: (formData: FormData) =>
    client.post<{ avatar_url: string }>('/api/auth/avatar', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
};

export const alertsApi = {
  // Use /api/alerts/paginated for paginated table queries
  getAlertsPaginated: (params?: {
    page?: number;
    per_page?: number;
    status?: string;
    title?: string;
    start_date?: string;
    end_date?: string;
  }) =>
    client.get<{
      items: Alert[];
      total: number;
      page: number;
      per_page: number;
      pages: number;
    }>('/api/alerts/paginated', { params }),

  // Full alerts query fallback
  getAllAlerts: () => client.get<Alert[]>('/api/alerts'),

  getAlertDetail: (alertId: string) => client.get<Alert>(`/api/alerts/${alertId}`),
  deleteAlert: (alertId: string) => client.delete(`/api/alerts/${alertId}`),
  rollbackAlert: (alertId: string) =>
    client.post<{ message: string; data: any }>(`/api/alerts/${alertId}/rollback`),
  forwardToOpenclaw: (alertId: string, target: 'analysis' | 'action') =>
    client.post('/api/webhook/forward-to-openclaw', { alert_id: alertId, target }),
};

export const statsApi = {
  getDashboardStats: () => client.get<DashboardStats>('/api/stats/dashboard'),
};

export const auditApi = {
  getLogs: (params?: { page?: number; per_page?: number; action?: string }) =>
    client.get<{
      items: AuditLogItem[];
      total: number;
      page: number;
      per_page: number;
      pages: number;
    }>('/api/audit/logs', { params }),
  getStats: () => client.get<any>('/api/audit/stats'),
};

export const settingsApi = {
  getSystemSettings: () => client.get<SystemSettings>('/api/settings/system'),
  updateSystemSettings: (data: Partial<SystemSettings>) =>
    client.put<{ message: string }>('/api/settings/system', data),
  getNotificationChannels: () => client.get<any>('/api/settings/notifications'),
  updateNotificationChannels: (data: any) =>
    client.put<{ message: string }>('/api/settings/notifications', data),
  testNotification: (channelType: string, config: any) =>
    client.post<{ success: boolean; message: string }>('/api/settings/notifications/test', {
      channel_type: channelType,
      config,
    }),
  getOpenclawSettings: () => client.get<any>('/api/settings/openclaw'),
  updateOpenclawSettings: (data: any) => client.put('/api/settings/openclaw', data),
};

export const skillsApi = {
  getConfig: () =>
    client.get<{
      base_url: string;
      analysis_key: string;
      action_key: string;
    }>('/api/skills/config'),
  getDownloadUrl: () => '/api/skills/download',
};




export const workflowApi = {
  getWorkflows: () => client.get<any[]>('/api/workflows'),
  createWorkflow: (data: any) => client.post<any>('/api/workflows', data),
  getWorkflowDetail: (id: number) => client.get<any>(`/api/workflows/${id}`),
  updateWorkflow: (id: number, data: any) => client.put<any>(`/api/workflows/${id}`, data),
  deleteWorkflow: (id: number) => client.delete(`/api/workflows/${id}`),
  runTest: (id: number, data?: { title?: string; content?: string }) =>
    client.post<any>(`/api/workflows/${id}/run-test`, data),
};

export const promptApi = {
  getPrompts: () => client.get<any[]>('/api/prompts'),
  updatePrompt: (id: number, data: { name?: string; system_prompt: string }) =>
    client.put<any>(`/api/prompts/${id}`, data),
};

export const agentApi = {
  getAgents: () => client.get<any[]>('/api/agents'),
};

export const toolsApi = {
  getTools: () => client.get<any[]>('/api/tools'),
};




export const sopApi = {
  getWorkbench: (alertId: string) => client.get<any>(`/api/sop/workbench/${alertId}`),
  confirmSOP: (alertId: string, sopContent: string) =>
    client.post<any>(`/api/sop/workbench/${alertId}/confirm`, { sop_content: sopContent }),
  getGoldenSops: () => client.get<any[]>('/api/sop/golden'),
  testSplunkQuery: (query: string, index?: string) =>
    client.post<any>('/api/splunk/query', { query, index }),
};

