"""
TwinSentry — 分析 Agent 技能包 (Analysis Agent Skill)
=====================================================
适用于 AI Agent 框架（如 Dify、AutoGPT、LangChain 等）。
本脚本封装了与 TwinSentry 分析 Agent 接口的完整交互逻辑：
  1. 获取一条待分析的告警任务 (GET /analysis/fetch)
  2. 提交分析结论与 Splunk 富化数据 (POST /analysis/submit)

使用前请修改下方 "===== 配置区 =====" 中的参数。
"""

import requests
import json
import logging
from typing import Optional

# ===== 配置区 =====
TWINSENTRY_BASE_URL = "http://192.168.0.2:5000"   # TwinSentry 服务器地址
ANALYSIS_AGENT_KEY  = "your-analysis-agent-key-here"  # 分析 Agent API Key
REQUEST_TIMEOUT     = 30                          # 请求超时（秒）
# ==================

logger = logging.getLogger(__name__)


class TwinSentryAnalysisSkill:
    """
    TwinSentry 分析 Agent 技能类。
    负责从 TwinSentry 获取待分析告警，并将模型的分析结论提交回系统。

    典型工作流：
        skill = TwinSentryAnalysisSkill()
        task = skill.fetch_task()
        if task:
            result = your_llm.analyze(task)
            skill.submit_result(
                alert_id        = task["id"],
                analysis_log    = result.conclusion,
                enrichment_data = result.enrichment  # 可选
            )
    """

    def __init__(
        self,
        base_url: str = TWINSENTRY_BASE_URL,
        api_key: str  = ANALYSIS_AGENT_KEY,
        timeout: int  = REQUEST_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.headers  = {
            "X-Agent-Key":  api_key,
            "Content-Type": "application/json",
            "Accept":       "application/json",
        }
        self.timeout = timeout

    # ──────────────────────────────────────────────────────────────────────
    # 公开方法
    # ──────────────────────────────────────────────────────────────────────

    def fetch_task(self) -> Optional[dict]:
        """
        从 TwinSentry 原子性获取一条待分析告警。
        服务端使用 SELECT FOR UPDATE SKIP LOCKED，保证同一告警不会被多个 Agent 并发获取。

        返回值：
            dict  — 告警信息，包含以下字段：
                id            (int)   告警 ID（提交时必须传回）
                title         (str)   告警标题
                priority      (str)   优先级：high / medium / low
                raw_text      (str)   原始文本
                text_lines    (list)  按 \\r 拆分的告警内容列表
            None  — 当前无待处理任务

        示例：
            >>> task = skill.fetch_task()
            >>> if task:
            ...     print(task["title"], task["text_lines"])
        """
        url = f"{self.base_url}/analysis/fetch"
        try:
            resp = requests.get(url, headers=self.headers, timeout=self.timeout)
            data = resp.json()
            if resp.status_code == 200 and data.get("code") == 0:
                alert = data["data"].get("alert")
                if alert:
                    logger.info(f"[AnalysisSkill] 已获取告警 #{alert['id']}: {alert['title']}")
                    return alert
                else:
                    logger.info("[AnalysisSkill] 暂无待分析任务")
                    return None
            elif resp.status_code == 404:
                logger.info("[AnalysisSkill] 暂无待分析任务（队列为空）")
                return None
            else:
                logger.warning(f"[AnalysisSkill] fetch 失败: {resp.status_code} {data.get('msg')}")
                return None
        except requests.exceptions.Timeout:
            logger.error("[AnalysisSkill] 请求超时，请检查服务器连接")
            return None
        except Exception as e:
            logger.error(f"[AnalysisSkill] fetch 异常: {e}")
            return None

    def submit_result(
        self,
        alert_id:        int,
        analysis_log:    str,
        enrichment_data: Optional[dict] = None,
    ) -> bool:
        """
        提交分析结论到 TwinSentry。
        成功后告警状态将流转为 "analyzed"，进入处置 Agent 处理队列。

        参数：
            alert_id        (int)   fetch_task() 返回的告警 ID
            analysis_log    (str)   分析结论文本（支持多行，建议包含威胁研判和建议动作）
            enrichment_data (dict)  可选，Splunk 富化数据（JSONB 字段，任意结构）

        返回值：
            True  — 提交成功
            False — 提交失败

        示例：
            >>> skill.submit_result(
            ...     alert_id=1,
            ...     analysis_log="来源 IP 1.2.3.4 命中威胁情报，建议立即封禁。",
            ...     enrichment_data={"splunk_events": [...], "threat_score": 95}
            ... )
        """
        url = f"{self.base_url}/analysis/submit"
        payload: dict = {
            "alert_id":     alert_id,
            "analysis_log": analysis_log,
        }
        if enrichment_data is not None:
            payload["enrichment_data"] = enrichment_data

        try:
            resp = requests.post(
                url,
                headers=self.headers,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                timeout=self.timeout,
            )
            data = resp.json()
            if resp.status_code == 200 and data.get("code") == 0:
                logger.info(f"[AnalysisSkill] 告警 #{alert_id} 分析结论已提交")
                return True
            else:
                logger.warning(f"[AnalysisSkill] submit 失败: {resp.status_code} {data.get('msg')}")
                return False
        except requests.exceptions.Timeout:
            logger.error("[AnalysisSkill] 提交超时")
            return False
        except Exception as e:
            logger.error(f"[AnalysisSkill] submit 异常: {e}")
            return False

    def run_once(self, analyze_func) -> bool:
        """
        便捷方法：完成一次完整的"获取 → 分析 → 提交"流程。

        参数：
            analyze_func — 可调用对象，接收告警 dict，返回 dict:
                           { "analysis_log": str, "enrichment_data": dict (可选) }

        返回值：
            True  — 成功处理一条告警
            False — 无任务或处理失败

        示例：
            >>> def my_analyze(alert: dict) -> dict:
            ...     # 调用 LLM 或其他分析逻辑
            ...     return {
            ...         "analysis_log": f"分析完成：{alert['title']} 为低威胁告警。",
            ...         "enrichment_data": {"source": "my_agent"}
            ...     }
            >>> skill.run_once(my_analyze)
        """
        task = self.fetch_task()
        if not task:
            return False

        try:
            result = analyze_func(task)
        except Exception as e:
            logger.error(f"[AnalysisSkill] 分析函数异常: {e}")
            return False

        return self.submit_result(
            alert_id=task["id"],
            analysis_log=result.get("analysis_log", ""),
            enrichment_data=result.get("enrichment_data"),
        )


# ──────────────────────────────────────────────────────────────────────────────
# 单文件运行示例（直接执行此脚本时触发）
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import time

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    skill = TwinSentryAnalysisSkill()

    def demo_analyze(alert: dict) -> dict:
        """演示用分析函数 — 请替换为实际的 LLM 调用逻辑"""
        title      = alert.get("title", "")
        text_lines = alert.get("text_lines", [])
        priority   = alert.get("priority", "low")

        summary = "\n".join(text_lines[:5]) if text_lines else "(无告警内容)"
        conclusion = (
            f"[Demo Agent] 已收到告警：{title}\n"
            f"优先级：{priority.upper()}\n"
            f"内容摘要：\n{summary}\n\n"
            f"初步研判：该告警需进一步核查，建议关注来源 IP 和异常行为模式。"
        )
        return {
            "analysis_log": conclusion,
            "enrichment_data": {"analyzed_by": "demo_agent", "lines_count": len(text_lines)},
        }

    print("=== TwinSentry 分析 Agent Skill Demo ===")
    print(f"服务地址: {TWINSENTRY_BASE_URL}")
    print("开始轮询任务（Ctrl+C 停止）...\n")

    while True:
        handled = skill.run_once(demo_analyze)
        if not handled:
            print("暂无任务，5 秒后重试...")
        time.sleep(5)
