"""
TwinSentry — 处置 Agent 技能包 (Disposition Agent Skill)
=========================================================
适用于 AI Agent 框架（如 Dify、AutoGPT、LangChain 等）。
本脚本封装了与 TwinSentry 处置 Agent 接口的完整交互逻辑：
  1. 获取一条已分析、待处置的告警任务 (GET /agent/disposition/fetch)
  2. 提交处置动作记录 (POST /agent/disposition/submit)

使用前请修改下方 "===== 配置区 =====" 中的参数。
"""

import requests
import json
import logging
from typing import Optional

# ===== 配置区 =====
TWINSENTRY_BASE_URL   = "http://192.168.0.2:5000"     # TwinSentry 服务器地址
DISPOSITION_AGENT_KEY = "05b3a520e16a86424fd3c9666cd11fad422ff7e98102f1b02090991aa15c8eda"  # 处置 Agent API Key
REQUEST_TIMEOUT       = 30                            # 请求超时（秒）
# ==================

logger = logging.getLogger(__name__)


class TwinSentryDispositionSkill:
    """
    TwinSentry 处置 Agent 技能类。
    负责从 TwinSentry 获取已分析告警，并将执行的处置动作提交回系统。

    典型工作流：
        skill = TwinSentryDispositionSkill()
        task = skill.fetch_task()
        if task:
            action = your_agent.dispose(task)
            skill.submit_result(
                alert_id   = task["id"],
                action_log = action.summary
            )
    """

    def __init__(
        self,
        base_url: str = TWINSENTRY_BASE_URL,
        api_key: str  = DISPOSITION_AGENT_KEY,
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
        从 TwinSentry 原子性获取一条已完成分析、待处置的告警。
        服务端使用 SELECT FOR UPDATE SKIP LOCKED，保证同一告警不会被多个 Agent 并发获取。

        返回值：
            dict  — 告警信息，包含以下字段：
                id              (int)   告警 ID（提交时必须传回）
                title           (str)   告警标题
                priority        (str)   优先级：high / medium / low
                raw_text        (str)   原始文本
                text_lines      (list)  按 \\r 拆分的告警内容列表
                enrichment_data (dict)  分析 Agent 写入的 Splunk 富化数据
                analysis_log    (str)   分析 Agent 的分析结论（处置依据）
            None  — 当前无待处置任务

        示例：
            >>> task = skill.fetch_task()
            >>> if task:
            ...     print(task["analysis_log"])  # 读取分析结论
            ...     print(task["enrichment_data"])  # 读取富化数据
        """
        url = f"{self.base_url}/disposition/fetch"
        try:
            resp = requests.get(url, headers=self.headers, timeout=self.timeout)
            data = resp.json()
            if resp.status_code == 200 and data.get("code") == 0:
                alert = data["data"].get("alert")
                if alert:
                    logger.info(f"[DispositionSkill] 已获取告警 #{alert['id']}: {alert['title']}")
                    return alert
                else:
                    logger.info("[DispositionSkill] 暂无待处置任务")
                    return None
            elif resp.status_code == 404:
                logger.info("[DispositionSkill] 暂无待处置任务（队列为空）")
                return None
            else:
                logger.warning(f"[DispositionSkill] fetch 失败: {resp.status_code} {data.get('msg')}")
                return None
        except requests.exceptions.Timeout:
            logger.error("[DispositionSkill] 请求超时，请检查服务器连接")
            return None
        except Exception as e:
            logger.error(f"[DispositionSkill] fetch 异常: {e}")
            return None

    def submit_result(
        self,
        alert_id:   int,
        action_log: str,
    ) -> bool:
        """
        提交处置动作记录到 TwinSentry。
        成功后告警状态将流转为 "disposed"，完成全生命周期。

        参数：
            alert_id   (int)  fetch_task() 返回的告警 ID
            action_log (str)  处置动作详细记录（建议逐条列出实际执行的操作）

        返回值：
            True  — 提交成功
            False — 提交失败

        处置记录示例：
            "1. 已在雷池 WAF 封禁来源 IP 1.2.3.4（规则 ID: R-2024-001）\n"
            "2. 已在 Linux 主机 server01 终止进程 PID 4321 (python3 -m miner)\n"
            "3. 已通知安全团队，工单号 TICKET-8899\n"
            "处置完成时间: 2024-01-01 10:05:00"
        """
        url = f"{self.base_url}/disposition/submit"
        payload = {
            "alert_id":   alert_id,
            "action_log": action_log,
        }
        try:
            resp = requests.post(
                url,
                headers=self.headers,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                timeout=self.timeout,
            )
            data = resp.json()
            if resp.status_code == 200 and data.get("code") == 0:
                logger.info(f"[DispositionSkill] 告警 #{alert_id} 处置记录已提交，状态 → disposed")
                return True
            else:
                logger.warning(f"[DispositionSkill] submit 失败: {resp.status_code} {data.get('msg')}")
                return False
        except requests.exceptions.Timeout:
            logger.error("[DispositionSkill] 提交超时")
            return False
        except Exception as e:
            logger.error(f"[DispositionSkill] submit 异常: {e}")
            return False

    def run_once(self, dispose_func) -> bool:
        """
        便捷方法：完成一次完整的"获取 → 处置 → 提交"流程。

        参数：
            dispose_func — 可调用对象，接收告警 dict，返回 dict:
                           { "action_log": str }

        返回值：
            True  — 成功处理一条告警
            False — 无任务或处理失败

        示例：
            >>> def my_dispose(alert: dict) -> dict:
            ...     analysis = alert.get("analysis_log", "")
            ...     enrichment = alert.get("enrichment_data", {})
            ...     # 根据分析结论决定处置动作
            ...     return {
            ...         "action_log": (
            ...             f"根据分析结论：{analysis[:100]}...\n"
            ...             f"已执行自动封禁，操作完成。"
            ...         )
            ...     }
            >>> skill.run_once(my_dispose)
        """
        task = self.fetch_task()
        if not task:
            return False

        try:
            result = dispose_func(task)
        except Exception as e:
            logger.error(f"[DispositionSkill] 处置函数异常: {e}")
            return False

        return self.submit_result(
            alert_id=task["id"],
            action_log=result.get("action_log", ""),
        )


# ──────────────────────────────────────────────────────────────────────────────
# 单文件运行示例（直接执行此脚本时触发）
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import time

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    skill = TwinSentryDispositionSkill()

    def demo_dispose(alert: dict) -> dict:
        """演示用处置函数 — 请替换为实际的处置逻辑（调用安全工具 API 等）"""
        title        = alert.get("title", "")
        priority     = alert.get("priority", "low")
        analysis_log = alert.get("analysis_log", "（无分析结论）")
        enrichment   = alert.get("enrichment_data") or {}

        action = (
            f"[Demo Disposition Agent] 告警处置报告\n"
            f"告警标题: {title}\n"
            f"优先级: {priority.upper()}\n\n"
            f"参考分析结论:\n{analysis_log[:200]}\n\n"
            f"执行处置动作:\n"
            f"1. [模拟] 已记录该告警，待人工复核\n"
            f"2. [模拟] 已通知值班安全工程师\n"
            f"富化数据字段数: {len(enrichment)}\n"
            f"处置状态: 完成（Demo 模式，未执行真实操作）"
        )
        return {"action_log": action}

    print("=== TwinSentry 处置 Agent Skill Demo ===")
    print(f"服务地址: {TWINSENTRY_BASE_URL}")
    print("开始轮询任务（Ctrl+C 停止）...\n")

    while True:
        handled = skill.run_once(demo_dispose)
        if not handled:
            print("暂无任务，5 秒后重试...")
        time.sleep(5)
