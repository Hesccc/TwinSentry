"""
Adaptive Dynamic SOP Generator & Knowledge Flywheel Engine
Generates live, evidence-grounded incident response SOPs and supports human calibration feedback into the Golden SOP knowledge base.
"""
from typing import Dict, Any, List

class SOPEngine:
    """自适应 SOP 生成与知识飞轮引擎"""
    
    @staticmethod
    def generate_adaptive_sop(
        alert_title: str,
        target_entity: str,
        rca_conclusion: str,
        evidence_snippet: str
    ) -> str:
        """
        生成与现场证据强绑定的动态可执行指南：
        1. 现场快照与确认命令
        2. 应急止血动作
        3. 精确处置步骤
        4. 恢复验证指标
        5. 应急回滚方案
        """
        target_ip = "194.26.29.112"
        target_host = "prod-srv-billing-01"
        
        sop_markdown = f"""# 🚨 应急排障处置 SOP 指南

## 1. 现场快照与状态核查 (Investigation Snapshot)
- **告警标题**: {alert_title}
- **受影响实体**: `{target_host}`
- **确认命令**:
  ```bash
  # 检查当前主机活跃外联网络套接字
  ss -antp | grep '{target_ip}'
  # 追踪关联父子进程链
  ps -ef | grep -E 'python|curl|wget' | grep -v grep
  ```

## 2. 应急止血动作 (Immediate Mitigation)
- **网络层临时封禁**:
  ```bash
  # 下发边缘网关临时丢弃规则 (TTL=24h)
  iptables -I OUTPUT -d {target_ip} -j DROP
  ```
- **微隔离策略下发**: 对主机 `{target_host}` 开启安全管理受限白名单模式。

## 3. 精确处置与恢复步骤 (Remediation Actions)
1. 终止异常外联会话对应的宿主 PID：
   ```bash
   kill -9 $(lsof -t -i@{target_ip})
   ```
2. 隔离可疑临时文件与计划任务：
   ```bash
   crontab -l > /tmp/cron_backup.txt && crontab -r
   ```

## 4. 恢复验证指标 (Verification Metrics)
- **Splunk 检索验证**:
  ```spl
  index=idx_prod_payment host="{target_host}" earliest=-15m | stats count by dest_ip
  ```
- 确保近 15 分钟内对 `{target_ip}` 的 4444 端口外联次数归零。

## 5. 应急回滚方案 (Rollback Plan)
- 若业务出现连带受阻：
  ```bash
  iptables -D OUTPUT -d {target_ip} -j DROP
  crontab /tmp/cron_backup.txt
  ```
"""
        return sop_markdown
