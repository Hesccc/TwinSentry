"""
TwinSentry — 处置 Agent 技能包 (Disposition Agent Skill)
=========================================================
本 Python 脚本封装了与 TwinSentry 分析 Agent 接口的完整交互逻辑：
  1. 获取一条已分析、待处置的告警任务 (GET /agent/disposition/fetch)
  2. 提交处置动作记录 (POST /agent/disposition/submit)

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
TWINSENTRY_BASE_URL   = os.environ.get("TWINSENTRY_BASE_URL", "http://192.168.0.2:5000")     # TwinSentry 服务器地址
ACTION_AGENT_KEY      = os.environ.get("ACTION_AGENT_KEY", "your-action-agent-key-here")  # 处置 Agent API Key
REQUEST_TIMEOUT       = int(os.environ.get("REQUEST_TIMEOUT", 30))                            # 请求超时（秒）
# ==================

logger = logging.getLogger(__name__)


class TwinSentryActionSkill:
    """
    TwinSentry 处置 Agent 技能类。
    负责从 TwinSentry 获取已分析告警，并将执行的处置动作提交回系统。

    典型工作流：
        skill = TwinSentryActionSkill()
        task = skill.fetch_task()
        if task:
            action = your_agent.dispose(task)
            skill.submit_result(
                alert_id        = task["id"],
                action_log      = action.summary,
                enrichment_data = result.enrichment  # 可选
            )
    """

    def __init__(
        self,
        base_url: str = TWINSENTRY_BASE_URL,
        api_key: str  = ACTION_AGENT_KEY,
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
        从 TwinSentry 原子性获取一条已完成分析、待处置的告警。
        服务端使用 SELECT FOR UPDATE SKIP LOCKED，保证同一告警不会被多个 Agent 并发获取。

        参数：
            alert_id (int): 可选。如果传入，则只尝试获取该给定 ID 的告警。


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
        params = {"alert_id": alert_id} if alert_id is not None else None
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            data = resp.json()
            if resp.status_code == 200 and data.get("code") == 0:
                alert = data["data"].get("alert")
                if alert:
                    logger.info(f"[ActionSkill] 已获取告警 #{alert['id']}: {alert['title']}")
                    return alert
                else:
                    logger.info("[ActionSkill] 暂无待处置任务")
                    return None
            elif resp.status_code == 404:
                logger.info("[ActionSkill] 暂无待处置任务（队列为空）")
                return None
            else:
                logger.warning(f"[ActionSkill] fetch 失败：{resp.status_code} {data.get('msg')}")
                return None
        except requests.exceptions.Timeout:
            logger.error("[ActionSkill] 请求超时，请检查服务器连接")
            return None
        except Exception as e:
            logger.error(f"[ActionSkill] fetch 异常：{e}")
            return None

    def submit_result(
        self,
        alert_id:        int,
        action_log:      str,
        enrichment_data: Optional[dict] = None,
    ) -> bool:
        """
        提交处置动作记录到 TwinSentry。
        成功后告警状态将流转为 "disposed"，完成全生命周期。

        参数：
            alert_id        (int)   fetch_task() 返回的告警 ID
            action_log      (str)   处置动作详细记录（建议逐条列出实际执行的操作）
            enrichment_data (dict)  可选，附加的富化数据（JSONB 字段，任意结构）

        返回值：
            True  — 提交成功
            False — 提交失败

        处置记录示例：
            "1. 已在雷池 WAF 封禁来源 IP 1.2.3.4（规则 ID: R-2024-001）\n"
            "2. 已在 Linux 主机 server01 终止进程 PID 4321 (python3 -m miner)\n"
            "3. 已通知安全团队，工单号 TICKET-8899\n"
            "处置完成时间：2024-01-01 10:05:00"
        """
        url = f"{self.base_url}/disposition/submit"
        payload: dict = {
            "alert_id":   alert_id,
            "action_log": action_log,
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
                logger.info(f"[ActionSkill] 告警 #{alert_id} 处置记录已提交，状态 → disposed")
                return True
            else:
                logger.warning(f"[ActionSkill] submit 失败：{resp.status_code} {data.get('msg')}")
                return False
        except requests.exceptions.Timeout:
            logger.error("[ActionSkill] 提交超时")
            return False
        except Exception as e:
            logger.error(f"[ActionSkill] submit 异常：{e}")
            return False

    def run_once(self, dispose_func, alert_id: Optional[int] = None) -> bool:
        """
        便捷方法：完成一次完整的"获取 → 处置 → 提交"流程。

        参数：
            dispose_func — 可调用对象，接收告警 dict，返回 dict:
                           { "action_log": str, "enrichment_data": dict (可选) }
            alert_id     — 可选，只处理特定 ID 的告警


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
        task = self.fetch_task(alert_id=alert_id)
        if not task:
            return False

        try:
            result = dispose_func(task)
        except Exception as e:
            logger.error(f"[ActionSkill] 处置函数异常：{e}")
            return False

        return self.submit_result(
            alert_id=task["id"],
            action_log=result.get("action_log", ""),
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
      # 1. 获取一条待处置的安全告警
      uv run action_agent_skill.py fetch_task
      # 2. 获取指定 ID 的告警
      uv run action_agent_skill.py fetch_task --alert_id 12345
      # 3. 提交告警处置结果
      uv run action_agent_skill.py submit_result --alert_id 12345 --data "已封禁 IP 1.2.3.4"
      # 4. 提交处置结果并附加富化数据
      uv run action_agent_skill.py submit_result --alert_id 12345 --data "已封禁 IP" --enrichment '{"waf_rule": "R-001"}'

    更多信息:
      使用 uv run action_agent_skill.py <command> -h 查看子命令的详细帮助
""")
                return "".join(parts)
            return super()._format_action(action)

    # 详细的脚本描述
    DESCRIPTION = """TwinSentry 处置 Agent 命令行工具

本工具用于与 TwinSentry 安全事件分析平台进行交互，提供以下功能：
  - 获取待处置的安全告警任务
  - 提交告警处置结果与富化数据
"""

    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=CustomHelpFormatter
    )
    parser.add_argument("-v", "--version", action="version", version="TwinSentry Action Agent Skill v1.0")

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    # fetch_task 子命令
    fetch_args = [{"name": "--alert_id", "help": "指定告警 ID，获取指定 ID 的告警"}]
    fetch_parser = subparsers.add_parser(
        "fetch_task",
        help="从 TwinSentry 获取一条待处置的安全告警",
        description="原子性获取一条已完成分析、待处置的安全告警任务。\n服务端使用 SELECT FOR UPDATE SKIP LOCKED，保证同一告警不会被多个 Agent 并发获取。",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    fetch_parser.add_argument(
        "--alert_id",
        type=int,
        metavar="ID",
        help="指定告警 ID，获取指定 ID 的告警"
    )
    subcommand_help.add_subcommand("fetch_task", "从 TwinSentry 获取一条待处置的安全告警", fetch_args)

    # submit_result 子命令
    submit_args = [
        {"name": "--alert_id", "help": "指定告警 ID"},
        {"name": "--data", "help": "提交指定的告警 ID 的处置结果"},
        {"name": "--enrichment", "help": "可选，附加富化数据 (JSON 格式)"}
    ]
    submit_parser = subparsers.add_parser(
        "submit_result",
        help="向 TwinSentry 提交告警处置结果",
        description="提交处置动作记录到 TwinSentry。\n成功后告警状态将流转为 'disposed'，完成全生命周期。",
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
        help="提交指定的告警 ID 的处置结果"
    )
    submit_parser.add_argument(
        "--enrichment",
        type=str,
        default=None,
        metavar="JSON",
        help="可选，附加富化数据 (JSON 格式)"
    )
    subcommand_help.add_subcommand("submit_result", "向 TwinSentry 提交告警处置结果", submit_args)

    # run_once 子命令
    run_parser = subparsers.add_parser(
        "run_once",
        help=argparse.SUPPRESS,
        description="便捷方法：完成一次完整的流程。\n使用内置的 demo_dispose 函数模拟处置逻辑，仅用于演示。",
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
    skill = TwinSentryActionSkill()

    def demo_dispose(alert: dict) -> dict:
        """演示用处置函数 — 请替换为实际的处置逻辑（调用安全工具 API 等）"""
        title        = alert.get("title", "")
        priority     = alert.get("priority", "low")
        analysis_log = alert.get("analysis_log", "（无分析结论）")
        enrichment   = alert.get("enrichment_data") or {}

        action = (
            f"[Demo Disposition Agent] 告警处置报告\n"
            f"告警标题：{title}\n"
            f"优先级：{priority.upper()}\n\n"
            f"参考分析结论:\n{analysis_log[:200]}\n\n"
            f"执行处置动作:\n"
            f"1. [模拟] 已记录该告警，待人工复核\n"
            f"2. [模拟] 已通知值班安全工程师\n"
            f"富化数据字段数：{len(enrichment)}\n"
            f"处置状态：完成（Demo 模式，未执行真实操作）"
        )
        return {"action_log": action}

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
            action_log=args.data,
            enrichment_data=enrichment_data
        )
        if success:
            print(f"告警 {args.alert_id} 处置结果提交成功。")
        else:
            print(f"告警 {args.alert_id} 处置结果提交失败。")
    elif args.command == "run_once":
        if args.loop:
            # 持续轮询模式
            print("=== TwinSentry 处置 Agent Skill Demo (轮询模式) ===")
            print(f"服务地址：{TWINSENTRY_BASE_URL}")
            print("开始轮询任务（Ctrl+C 停止）...\n")
            while True:
                handled = skill.run_once(demo_dispose)
                if not handled:
                    print("暂无任务，5 秒后重试...")
                time.sleep(5)
        else:
            # 单次执行模式
            print("=== TwinSentry 处置 Agent Skill Demo ===")
            print(f"服务地址：{TWINSENTRY_BASE_URL}")
            handled = skill.run_once(demo_dispose, alert_id=args.alert_id)
            if handled:
                print("单次任务执行完成。")
            else:
                print("无待处理任务或执行失败。")
    else:
        parser.print_help()
