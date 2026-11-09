export interface User {
  id: number;
  username: string;
  avatar?: string;
  is_admin?: boolean;
}

export type AlertStatus = '待分析' | '分析中' | '已分析' | '处置中' | '已处置';

export interface Alert {
  alert_id: string;
  title: string;
  text: string;
  status: AlertStatus;
  created_at: string;
  updated_at: string;
  analysis_result?: string;
  disposition_result?: string;
  is_delete: number;
}

export interface DashboardStats {
  raw_count: number;
  dedup_count: number;
  pending_count: number;
  active_count: number;
  processing_count: number;
  processed_count: number;
  trend_data: {
    hours: string[];
    collected: number[];
    generated: number[];
    disposed: number[];
  };
  status_distribution: {
    name: string;
    value: number;
  }[];
  top_alerts: {
    title: string;
    count: number;
  }[];
  recent_activities: {
    time: string;
    action: string;
    target: string;
    status: string;
  }[];
}

export interface AuditLogItem {
  id: number;
  user_id?: number;
  username?: string;
  action: string;
  ip_address?: string;
  details?: string;
  created_at: string;
}

export interface SystemSettings {
  NOTIFY_TIMEOUT_MINUTES: number;
  DEDUP_STRATEGY: 'title' | 'title_content';
  ANALYSIS_AGENT_KEY: string;
  ACTION_AGENT_KEY: string;
  SMTP_SERVER?: string;
  SMTP_PORT?: number;
  SMTP_USER?: string;
  SMTP_PASSWORD?: string;
  SMTP_FROM?: string;
  EMAIL_RECEIVERS?: string;
  FEISHU_WEBHOOK?: string;
  WECHAT_WEBHOOK?: string;
  CUSTOM_WEBHOOK?: string;
}

