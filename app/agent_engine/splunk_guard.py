"""
Splunk MCP Safe Interceptor & Guardrails
Enforces strict index confinement, forbidding blind queries (index=*) or missing index.
"""
import re
from typing import Dict, Any, List

class SplunkQuerySecurityError(Exception):
    """Splunk SPL 查询安全违规异常"""
    pass

class SplunkGuard:
    """
    Splunk SPL 物理安全护栏：
    1. 强制查询语句中显式声明合法具体的 index (禁止 index=* 或裸查)
    2. 校验 index 是否在当前告警/服务的白名单范围内
    3. 强制加入时间窗口约束 (earliest / latest)，防止全量检索瘫痪集群
    """
    def __init__(self, allowed_indexes: List[str] = None):
        self.allowed_indexes = allowed_indexes or []

    def validate_and_sanitize(self, query: str, context_index: str = None) -> str:
        cleaned_query = query.strip()
        
        # 1. 拦截 index=* 盲搜
        if re.search(r'\\bindex\\s*=\\s*\\*', cleaned_query):
            raise SplunkQuerySecurityError("安全拦截：严禁使用 'index=*' 进行全集群扫描，必须指定具体业务 index！")

        # 2. 提取语句中的 index 字段
        index_match = re.search(r'\\bindex\\s*=\\s*([a-zA-Z0-9_\\-\\.\"]+)', cleaned_query)
        if not index_match:
            # 如果未包含 index 且提供了上下文锁定 index，则自动前置补充
            if context_index:
                cleaned_query = f"index={context_index} " + cleaned_query
                extracted_index = context_index
            else:
                raise SplunkQuerySecurityError("安全拦截：查询语句必须显式指定具体的 index，如 'index=idx_prod_payment'！")
        else:
            extracted_index = index_match.group(1).strip('"')

        # 3. 校验 index 是否在白名单范围内
        if self.allowed_indexes and extracted_index not in self.allowed_indexes:
            raise SplunkQuerySecurityError(
                f"安全拦截：指定的索引 '{extracted_index}' 不在当前服务的允许白名单 [{', '.join(self.allowed_indexes)}] 内！"
            )

        # 4. 时间范围防护 (如果无 earliest，默认补充最近1小时)
        if "earliest=" not in cleaned_query:
            cleaned_query = f"earliest=-1h {cleaned_query}"

        return cleaned_query

    def execute_mock_search(self, query: str, context_index: str = None) -> Dict[str, Any]:
        """执行经护栏检验的安全 Splunk 检索 (模拟/真实 MCP 执行)"""
        safe_query = self.validate_and_sanitize(query, context_index)
        
        # 模拟检索返回真实证据链日志
        return {
            "status": "success",
            "spl": safe_query,
            "matched_events": [
                {
                    "_time": "2026-11-09T14:32:01.000+08:00",
                    "host": "prod-srv-billing-01",
                    "source": "/var/log/app/payment.log",
                    "index": context_index or "idx_prod_payment",
                    "_raw": "2026-11-09 14:32:01 ERROR [PaymentWorker] Connection reset by peer: destination=194.26.29.112:4444, errCode=ECONNRESET"
                },
                {
                    "_time": "2026-11-09T14:32:05.000+08:00",
                    "host": "prod-srv-billing-01",
                    "source": "/var/log/app/payment.log",
                    "index": context_index or "idx_prod_payment",
                    "_raw": "2026-11-09 14:32:05 WARN [SecurityAudit] Suspicious outbound beaconing pattern detected to C2 candidate: 194.26.29.112"
                }
            ],
            "total_count": 2
        }
