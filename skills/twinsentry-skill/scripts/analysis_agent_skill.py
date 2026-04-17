"""
TwinSentry — 分析 Agent 技能包 (Analysis Agent Skill)
=====================================================
本 Python 脚本封装了与 TwinSentry 分析 Agent 接口的完整交互逻辑：
  1. 获取一条待分析的告警任务 (GET /analysis/fetch)
  2. 提交分析结论与 Splunk 富化数据 (POST /analysis/submit)

使用前请修改下方 "===== 配置区 =====" 中的参数。
"""

import requests
import json
import logging
from typing import Optional

import os
from dotenv import load_dotenv

load_dotenv()

# ===== 配置区 =====
TWINSENTRY_BASE_URL = os.environ.get("TWINSENTRY_BASE_URL", "http://192.168.0.2:5000")   # TwinSentry 服务器地址
ANALYSIS_AGENT_KEY  = os.environ.get("ANALYSIS_AGENT_KEY", "your-analysis-agent-key-here")  # 分析 Agent API Key
REQUEST_TIMEOUT     = int(os.environ.get("REQUEST_TIMEOUT", 30))                          # 请求超时（秒）
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

    def fetch_task(self, alert_id: Optional[int] = None) -> Optional[dict]:
        """
        从 TwinSentry 原子性获取一条待分析告警。
        服务端使用 SELECT FOR UPDATE SKIP LOCKED，保证同一告警不会被多个 Agent 并发获取。

        参数：
            alert_id (int): 可选。如果传入，则只尝试获取该给定 ID 的告警。


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
        params = {"alert_id": alert_id} if alert_id is not None else None
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
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
                logger.warning(f"[AnalysisSkill] fetch 失败：{resp.status_code} {data.get('msg')}")
                return None
        except requests.exceptions.Timeout:
            logger.error("[AnalysisSkill] 请求超时，请检查服务器连接")
            return None
        except Exception as e:
            logger.error(f"[AnalysisSkill] fetch 异常：{e}")
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
                logger.warning(f"[AnalysisSkill] submit 失败：{resp.status_code} {data.get('msg')}")
                return False
        except requests.exceptions.Timeout:
            logger.error("[AnalysisSkill] 提交超时")
            return False
        except Exception as e:
            logger.error(f"[AnalysisSkill] submit 异常：{e}")
            return False

    def run_once(self, analyze_func, alert_id: Optional[int] = None) -> bool:
        """
        便捷方法：完成一次完整的"获取 → 分析 → 提交"流程。

        参数：
            analyze_func — 可调用对象，接收告警 dict，返回 dict:
                           { "analysis_log": str, "enrichment_data": dict (可选) }
            alert_id     — 可选，只处理特定 ID 的告警


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
        task = self.fetch_task(alert_id=alert_id)
        if not task:
            return False

        try:
            result = analyze_func(task)
        except Exception as e:
            logger.error(f"[AnalysisSkill] 分析函数异常：{e}")
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
    import argparse
    import time

    # 存储子命令参数信息的类
    class SubcommandHelp:
        def __init__(self):
            self.subcommands = {}

        def add_subcommand(self, name, help_text, args):
            self.subcommands[name] = {"help": help_text, "args": args}

    subcommand_help = SubcommandHelp()

    # 自定义格式化类，用于显示子命令参数
    class CustomHelpFormatter(argparse.RawDescriptionHelpFormatter):
        def _format_action(self, action):
            if isinstance(action, argparse._SubParsersAction):
                # 自定义子命令显示格式
                parts = []
                parts.append("\n可用命令:\n")
                parts.append("  <command>\n")

                for name, parser in action.choices.items():
                    if name == "run_once":
                        continue  # 跳过隐藏的 run_once

                    # 获取子命令的帮助文本
                    help_text = parser.description.split('\n')[0] if parser.description else ""
                    # 简化描述，只取第一句
                    if "。" in help_text:
                        help_text = help_text.split("。")[0] + "。"

                    parts.append(f"    {name:<13} {help_text}\n")

                    # 显示该子命令的参数
                    sub_args = subcommand_help.subcommands.get(name, {}).get("args", [])
                    for arg_info in sub_args:
                        parts.append(f"      {arg_info['name']:<11} {arg_info['help']}\n")

                    parts.append("\n")

                # 添加使用示例和更多信息
                parts.append("""    使用示例:
      # 1. 获取一条待分析的安全告警
      python3 analysis_agent_skill.py fetch_task
      # 2. 获取指定 ID 的告警
      python3 analysis_agent_skill.py fetch_task --alert_id 12345
      # 3. 提交告警分析结论
      python3 analysis_agent_skill.py submit_result --alert_id 12345 --data "分析结论内容"

    更多信息:
      使用 python3 analysis_agent_skill.py <command> -h 查看子命令的详细帮助
""")
                return "".join(parts)
            return super()._format_action(action)

    # 详细的脚本描述
    DESCRIPTION = """TwinSentry 分析 Agent 命令行工具

本工具用于与 TwinSentry 安全事件分析平台进行交互，提供以下功能：
  - 获取待分析的安全告警任务
  - 提交告警分析结论与 Splunk 富化数据
"""

    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=CustomHelpFormatter
    )
    parser.add_argument("-v", "--version", action="version", version="TwinSentry Analysis Agent Skill v1.0")

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    # fetch_task 子命令
    fetch_args = [{"name": "--alert_id", "help": "指定告警 ID，获取指定 ID 的告警"}]
    fetch_parser = subparsers.add_parser(
        "fetch_task",
        help="从 TwinSentry 获取一条待分析的安全告警",
        description="原子性获取一条待分析的安全告警任务。\n服务端使用 SELECT FOR UPDATE SKIP LOCKED，保证同一告警不会被多个 Agent 并发获取。",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    fetch_parser.add_argument(
        "--alert_id",
        type=int,
        metavar="ID",
        help="指定告警 ID，获取指定 ID 的告警"
    )
    subcommand_help.add_subcommand("fetch_task", "从 TwinSentry 获取一条待分析的安全告警", fetch_args)

    # submit_result 子命令
    submit_args = [
        {"name": "--alert_id", "help": "指定告警 ID"},
        {"name": "--data", "help": "提交指定的告警 ID 的分析结论"},
        {"name": "--enrichment", "help": "可选，Splunk 富化数据 (JSON 格式)"}
    ]
    submit_parser = subparsers.add_parser(
        "submit_result",
        help="向 TwinSentry 提交告警分析结论",
        description="提交分析结论与 Splunk 富化数据到 TwinSentry。\n成功后告警状态将流转为 'analyzed'，进入处置 Agent 处理队列。",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    submit_parser.add_argument(
        "--alert_id",
        type=int,
        required=True,
        metavar="ID",
        help="指定告警 ID"
    )
    submit_parser.add_argument(
        "--data",
        type=str,
        required=True,
        metavar="CONTENT",
        help="提交指定的告警 ID 的分析结论"
    )
    submit_parser.add_argument(
        "--enrichment",
        type=str,
        default=None,
        metavar="JSON",
        help="可选，Splunk 富化数据 (JSON 格式)"
    )
    subcommand_help.add_subcommand("submit_result", "向 TwinSentry 提交告警分析结论", submit_args)

    # run_once 子命令
    run_parser = subparsers.add_parser(
        "run_once",
        help=argparse.SUPPRESS,
        description="便捷方法：完成一次完整的流程。\n使用内置的 demo_analyze 函数模拟分析逻辑，仅用于演示。",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    run_parser.add_argument(
        "--alert_id",
        type=int,
        metavar="ID",
        help="可选，只处理特定 ID 的告警"
    )
    run_parser.add_argument(
        "--loop",
        action="store_true",
        help="持续轮询模式，每 5 秒检查一次新任务"
    )

    args = parser.parse_args()

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

    if args.command == "fetch_task":
        task = skill.fetch_task(alert_id=args.alert_id)
        if task:
            print(json.dumps(task, indent=2, ensure_ascii=False))
        else:
            print("未能获取到任务。")
    elif args.command == "submit_result":
        enrichment_data = None
        if args.enrichment:
            try:
                enrichment_data = json.loads(args.enrichment)
            except json.JSONDecodeError as e:
                print(f"JSON 格式错误：{e}")
                exit(1)
        success = skill.submit_result(
            alert_id=args.alert_id,
            analysis_log=args.data,
            enrichment_data=enrichment_data
        )
        if success:
            print(f"告警 {args.alert_id} 分析结论提交成功。")
        else:
            print(f"告警 {args.alert_id} 分析结论提交失败。")
    elif args.command == "run_once":
        if args.loop:
            # 持续轮询模式
            print("=== TwinSentry 分析 Agent Skill Demo (轮询模式) ===")
            print(f"服务地址：{TWINSENTRY_BASE_URL}")
            print("开始轮询任务（Ctrl+C 停止）...\n")
            while True:
                handled = skill.run_once(demo_analyze)
                if not handled:
                    print("暂无任务，5 秒后重试...")
                time.sleep(5)
        else:
            # 单次执行模式
            print("=== TwinSentry 分析 Agent Skill Demo ===")
            print(f"服务地址：{TWINSENTRY_BASE_URL}")
            handled = skill.run_once(demo_analyze, alert_id=args.alert_id)
            if handled:
                print("单次任务执行完成。")
            else:
                print("无待处理任务或执行失败。")
    else:
        parser.print_help()
