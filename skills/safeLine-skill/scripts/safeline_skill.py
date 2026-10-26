#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
长亭雷池 (SafeLine) IP 封禁工具

功能：向雷池 WAF 社区版的 IP 组中添加恶意 IP
API 文档：https://help.waf-ce.chaitin.cn/
配置：通过 .env 文件或环境变量设置连接参数
支持白名单：处于白名单中的 IP 地址将自动跳过封禁
"""

import requests
import json
import sys
import os
import ipaddress
from typing import List, Dict, Any, Optional, Union
from pathlib import Path

# ==========================================
# 加载 .env 配置文件
# ==========================================
def _load_env() -> None:
    """尝试从 .env 文件加载环境变量（需要 python-dotenv）"""
    try:
        from dotenv import load_dotenv
        # 查找 .env 文件：优先从脚本所在目录的上一级（技能根目录）查找
        script_dir = Path(__file__).parent
        skill_root = script_dir.parent
        env_file = skill_root / ".env"
        if env_file.exists():
            load_dotenv(env_file)
        else:
            # 也尝试从脚本所在目录查找
            local_env = script_dir / ".env"
            if local_env.exists():
                load_dotenv(local_env)
    except ImportError:
        pass  # python-dotenv 未安装时跳过，使用已有环境变量


_load_env()


def _build_base_url() -> str:
    """从环境变量构建 base_url"""
    host = os.environ.get("SAFELINE_HOST", "")
    port = os.environ.get("SAFELINE_PORT", "9443")
    if host:
        return f"https://{host}:{port}"
    return "https://waf.example.com:9443"  # 默认占位符


# ==========================================
# 从环境变量读取配置（.env 文件或系统环境变量）
# ==========================================
SAFELINE_BASE_URL = os.environ.get("SAFELINE_BASE_URL", _build_base_url())
SAFELINE_TOKEN = os.environ.get("SAFELINE_TOKEN", "YOUR_API_TOKEN")
SAFELINE_GROUP_ID = int(os.environ.get("SAFELINE_GROUP_ID", "1"))
SAFELINE_WHITELIST = os.environ.get("SAFELINE_WHITELIST", "")
# ==========================================


# ==========================================
# 白名单解析工具函数
# ==========================================
def _parse_whitelist(whitelist_str: str) -> List[Union[ipaddress.IPv4Network, ipaddress.IPv6Network]]:
    """
    解析白名单字符串，返回 IP 网络对象列表。
    """
    networks = []
    if not whitelist_str.strip():
        return networks
    # 支持逗号和分号作为分隔符
    entries = [e.strip() for e in whitelist_str.replace(";", ",").split(",") if e.strip()]
    for entry in entries:
        try:
            # strict=False 允许主机位非零的 CIDR（如 192.168.1.100/24）
            networks.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            print(f"警告：白名单条目格式无效，已忽略：{entry}", file=sys.stderr)
    return networks


def _is_whitelisted(
    ip_str: str,
    whitelist: List[Union[ipaddress.IPv4Network, ipaddress.IPv6Network]]
) -> bool:
    """
    检查给定 IP 地址（或 CIDR）是否命中白名单。
    """
    if not whitelist:
        return False
    try:
        target = ipaddress.ip_network(ip_str, strict=False)
    except ValueError:
        return False  # 无法解析的格式，不屏蔽

    for wl_net in whitelist:
        if target.num_addresses == 1:
            if target.network_address in wl_net:
                return True
        else:
            if target.subnet_of(wl_net):
                return True
    return False


class SafeLineIPBan:
    """雷池 IP 封禁/查询工具类"""

    def __init__(
        self,
        base_url: str = SAFELINE_BASE_URL,
        token: str = SAFELINE_TOKEN,
        whitelist: Optional[str] = None
    ):
        """
        初始化工具

        Args:
            base_url: 雷池管理后台的访问地址（包含协议和端口）
            token: X-SLCE-API-TOKEN 用于鉴权
            whitelist: 白名单字符，逗号或分号分隔的 IP/CIDR 列表。
        """
        self.base_url = base_url.rstrip('/')
        self.token = token
        
        # 新的请求头部机制
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-SLCE-API-TOKEN": self.token
        }
        
        # 解析白名单：优先使用传入参数，其次使用环境变量
        wl_str = whitelist if whitelist is not None else SAFELINE_WHITELIST
        self.whitelist = _parse_whitelist(wl_str)

    def get_ipgroups(self) -> Dict[str, Any]:
        """获取当前创建的IP地址组详细信息，地址组名称、ID"""
        url = f"{self.base_url}/api/open/ipgroup"
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            response = requests.get(url, headers=self.headers, verify=False, timeout=30)
            
            result = {
                "success": response.status_code == 200,
                "status_code": response.status_code
            }
            if response.status_code == 200:
                try:
                    result["data"] = response.json()
                except json.JSONDecodeError:
                    result["message"] = "请求成功，但无法解析响应 JSON"
                    result["response_text"] = response.text
            else:
                result["message"] = self._get_error_message(response.status_code)
                try:
                    result["error_response"] = response.json()
                except json.JSONDecodeError:
                    result["error_text"] = response.text
            return result
        except Exception as e:
            return self._handle_request_exception(e)

    def get_ipgroup_detail(self, group_id: int) -> Dict[str, Any]:
        """通过地址组ID，获取地址组的详细信息，输出地址组的IP地址"""
        if not isinstance(group_id, int) or group_id <= 0:
            return {
                "success": False,
                "message": "错误：group_id 必须是正整数",
                "error_code": "INVALID_GROUP_ID"
            }

        url = f"{self.base_url}/api/open/ipgroup/detail"
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            response = requests.get(url, headers=self.headers, params={"id": group_id}, verify=False, timeout=30)
            
            result = {
                "success": response.status_code == 200,
                "status_code": response.status_code
            }
            if response.status_code == 200:
                try:
                    result["data"] = response.json()
                except json.JSONDecodeError:
                    result["message"] = "请求成功，但无法解析响应 JSON"
                    result["response_text"] = response.text
            else:
                result["message"] = self._get_error_message(response.status_code)
                try:
                    result["error_response"] = response.json()
                except json.JSONDecodeError:
                    result["error_text"] = response.text
            return result
        except Exception as e:
            return self._handle_request_exception(e)

    def append_ips(
        self,
        target_ips: List[str],
        group_id: int
    ) -> Dict[str, Any]:
        """
        通过地址组ID，向地址组添加 IP 地址 (覆盖改用附加机制)

        Args:
            target_ips: 需要封禁的 IP 地址列表，支持 IPv4、IPv6、CIDR
            group_id: 黑名单 IP 组的唯一 ID（正整数）

        Returns:
            包含成功状态和详细信息的字典
        """
        # 验证输入参数
        if not target_ips:
            return {
                "success": False,
                "message": "错误：IP 列表不能为空",
                "error_code": "EMPTY_IP_LIST"
            }

        if not isinstance(group_id, int) or group_id <= 0:
            return {
                "success": False,
                "message": "错误：group_id 必须是正整数",
                "error_code": "INVALID_GROUP_ID"
            }

        # 白名单过滤：剔除命中白名单的 IP
        skipped_ips = [ip for ip in target_ips if _is_whitelisted(ip, self.whitelist)]
        filtered_ips = [ip for ip in target_ips if not _is_whitelisted(ip, self.whitelist)]

        if skipped_ips:
            print(
                f"信息：以下 {len(skipped_ips)} 个 IP 在白名单中，已自动跳过："
                f"{', '.join(skipped_ips)}",
                file=sys.stderr
            )

        if not filtered_ips:
            return {
                "success": True,
                "message": "所有 IP 均在白名单中，无需封禁",
                "banned_ips": [],
                "skipped_ips": skipped_ips,
                "group_id": group_id
            }

        # 构造请求数据 (使用 /api/open/ipgroup/append 的格式)
        url = f"{self.base_url}/api/open/ipgroup/append"
        payload = {
            "ip_group_ids": [group_id],
            "ips": filtered_ips
        }

        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                verify=False,
                timeout=30
            )

            # 处理响应
            result = {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "banned_ips": filtered_ips,
                "skipped_ips": skipped_ips,
                "group_id": group_id
            }

            if response.status_code == 200:
                try:
                    response_data = response.json()
                    result["response"] = response_data
                    result["message"] = f"成功附加 {len(filtered_ips)} 个 IP 到组 {group_id}"
                except json.JSONDecodeError:
                    result["message"] = "请求成功，但无法解析响应 JSON"
                    result["response_text"] = response.text
            else:
                result["message"] = self._get_error_message(response.status_code)
                try:
                    result["error_response"] = response.json()
                except json.JSONDecodeError:
                    result["error_text"] = response.text

            return result

        except Exception as e:
            return self._handle_request_exception(e)

    def _handle_request_exception(self, e: Exception) -> Dict[str, Any]:
        """统一处理网络请求异常"""
        if isinstance(e, requests.exceptions.SSLError):
            return {"success": False, "message": "SSL 连接错误", "error": str(e), "error_code": "SSL_ERROR"}
        elif isinstance(e, requests.exceptions.ConnectionError):
            return {"success": False, "message": f"连接失败，请检查 base_url: {self.base_url}", "error": str(e), "error_code": "CONNECTION_ERROR"}
        elif isinstance(e, requests.exceptions.Timeout):
            return {"success": False, "message": "请求超时", "error": str(e), "error_code": "TIMEOUT"}
        elif isinstance(e, requests.exceptions.RequestException):
            return {"success": False, "message": "请求异常", "error": str(e), "error_code": "REQUEST_ERROR"}
        else:
            return {"success": False, "message": f"未知错误: {str(e)}", "error_code": "UNKNOWN_ERROR"}

    def _get_error_message(self, status_code: int) -> str:
        """根据状态码返回中文错误信息"""
        error_messages = {
            400: "错误：请求参数格式不正确",
            401: "错误：鉴权失败，请检查 X-SLCE-API-TOKEN",
            403: "错误：权限不足",
            404: "错误：接口不存在或 IP 组 ID 无效",
            405: "错误：请求方法不允许",
            500: "错误：服务器内部错误",
            502: "错误：网关错误",
            503: "错误：服务不可用"
        }
        return error_messages.get(status_code, f"错误：HTTP {status_code}")

    def get_config_info(self) -> Dict[str, str]:
        """返回当前配置信息（脱敏 Token）"""
        masked_token = (
            self.token[:4] + "****" + self.token[-4:]
            if len(self.token) > 8
            else "****"
        )
        return {
            "base_url": self.base_url,
            "token": masked_token,
            "whitelist": " ".join(str(w) for w in self.whitelist) if self.whitelist else "无"
        }


def run_tests() -> bool:
    """
    内置自测试：直接调用 SafeLineIPBan 的各函数验证代码正确性。
    通过 `python safeline_skill.py --test` 触发，无需真实 WAF 连接。
    """
    import unittest
    from unittest.mock import patch, MagicMock

    print("====================================================")
    print("SafeLine IP 封禁/查询工具 - 内置自测试")
    print("====================================================")

    class SelfTest(unittest.TestCase):

        def _tool(self):
            """创建测试用实例（使用虚假但格式正确的凭据）"""
            return SafeLineIPBan(
                base_url="https://192.168.1.1:9443",
                token="test-token-abcdefgh"
            )

        def _mock_response(self, status_code, json_data=None, text=""):
            resp = MagicMock()
            resp.status_code = status_code
            resp.text = text
            if json_data is not None:
                resp.json.return_value = json_data
            else:
                resp.json.side_effect = json.JSONDecodeError("err", "", 0)
            return resp

        # ----------------------------------------
        # 1. 参数验证
        # ----------------------------------------
        def test_01_empty_ip_list(self):
            """空 IP 列表应返回失败及 EMPTY_IP_LIST 错误"""
            result = self._tool().append_ips([], group_id=1)
            self.assertFalse(result["success"])
            self.assertEqual(result["error_code"], "EMPTY_IP_LIST")

        def test_02_invalid_group_id_zero(self):
            """group_id = 0 测试"""
            result = self._tool().append_ips(["1.2.3.4"], group_id=0)
            self.assertFalse(result["success"])
            self.assertEqual(result["error_code"], "INVALID_GROUP_ID")

        def test_03_invalid_group_id_negative(self):
            """在 GET 详情方法中测试负 group_id"""
            result = self._tool().get_ipgroup_detail(-1)
            self.assertFalse(result["success"])
            self.assertEqual(result["error_code"], "INVALID_GROUP_ID")

        # ----------------------------------------
        # 2. 查询接口 API 测试 (Mock)
        # ----------------------------------------
        def test_04_get_ipgroups(self):
            """模拟获取全部 IP 组信息"""
            with patch("requests.get") as mock_get:
                mock_get.return_value = self._mock_response(200, {"data": {"total": 1, "nodes": []}})
                result = self._tool().get_ipgroups()
            self.assertTrue(result["success"])
            self.assertIn("data", result)

        def test_05_get_ipgroup_detail(self):
            """模拟获取特定组 IP"""
            with patch("requests.get") as mock_get:
                mock_get.return_value = self._mock_response(200, {"data": {"data": {"ips": ["1.1.1.1"]}}})
                result = self._tool().get_ipgroup_detail(5)
            self.assertTrue(result["success"])
            self.assertIn("data", result)
            call_kwargs = mock_get.call_args.kwargs
            self.assertEqual(call_kwargs["params"]["id"], 5)

        # ----------------------------------------
        # 3. HTTP 响应处理 (Append)
        # ----------------------------------------
        def test_06_http_200_success(self):
            """附加请求 HTTP 200 → success=True"""
            with patch("requests.post") as mock_post:
                mock_post.return_value = self._mock_response(200, {"code": 0, "message": "success"})
                result = self._tool().append_ips(["1.2.3.4"], group_id=1)
            self.assertTrue(result["success"])
            self.assertEqual(result["status_code"], 200)

        def test_07_http_401_auth_error(self):
            """HTTP 401 包含 Token 提示信息"""
            with patch("requests.post") as mock_post:
                mock_post.return_value = self._mock_response(401, {"error": "unauthorized"})
                result = self._tool().append_ips(["1.2.3.4"], group_id=1)
            self.assertFalse(result["success"])
            self.assertEqual(result["status_code"], 401)
            self.assertIn("TOKEN", result["message"])

        # ----------------------------------------
        # 4. 网络异常处理
        # ----------------------------------------
        def test_08_connection_error(self):
            """ConnectionError -> CONNECTION_ERROR"""
            with patch("requests.post", side_effect=requests.exceptions.ConnectionError("refused")):
                result = self._tool().append_ips(["1.2.3.4"], group_id=1)
            self.assertFalse(result["success"])
            self.assertEqual(result["error_code"], "CONNECTION_ERROR")

        # ----------------------------------------
        # 5. 请求体结构与白名单
        # ----------------------------------------
        def test_09_request_payload_structure(self):
            """验证发送给 Append API 的 JSON 请求体包含 ip_group_ids 和 ips"""
            with patch("requests.post") as mock_post:
                mock_post.return_value = self._mock_response(200, {"code": 0})
                self._tool().append_ips(["5.5.5.5", "6.6.6.6"], group_id=7)
                call_kwargs = mock_post.call_args.kwargs
                payload = call_kwargs.get("json", {})
            self.assertEqual(payload.get("ip_group_ids"), [7])
            self.assertEqual(payload.get("ips"), ["5.5.5.5", "6.6.6.6"])

        def test_10_whitelist_filter(self):
            """白名单内的部分 IP 应该被过滤并放进 skipped_ips。被屏蔽的放入 banned_ips"""
            tool = SafeLineIPBan("https://1", "tok", whitelist="10.0.0.0/8,1.2.3.4")
            with patch("requests.post") as mock_post:
                mock_post.return_value = self._mock_response(200, {"code": 0})
                result = tool.append_ips(["10.1.2.3", "1.2.3.4", "8.8.8.8"], group_id=2)
            self.assertTrue(result["success"])
            self.assertEqual(result["banned_ips"], ["8.8.8.8"])
            self.assertEqual(len(result["skipped_ips"]), 2)

        def test_11_all_whitelisted(self):
            """如果所有输入 IP 在白名单内，应跳过整个请求过程"""
            tool = SafeLineIPBan("https://1", "tok", whitelist="8.8.8.8")
            result = tool.append_ips(["8.8.8.8"], group_id=2)
            self.assertTrue(result["success"])
            self.assertEqual(result["banned_ips"], [])
            self.assertEqual(result["skipped_ips"], ["8.8.8.8"])

    # 运行所有测试
    loader = unittest.TestLoader()
    loader.sortTestMethodsUsing = None  # 保持定义顺序
    suite = loader.loadTestsFromTestCase(SelfTest)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("====================================================")
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f"共 {result.testsRun} 项测试，通过 {passed} 项，"
          f"失败 {len(result.failures)} 项，错误 {len(result.errors)} 项")
    print("====================================================")
    return result.wasSuccessful()


def main():
    """命令行入口函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="长亭雷池 (SafeLine) IP 封禁/查询工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
配置方式（优先级从高到低）：
  1. 命令行参数 --url / --token
  2. 环境变量 SAFELINE_BASE_URL / SAFELINE_TOKEN / SAFELINE_WHITELIST
  3. 技能根目录下的 .env 文件

查询示例：
  python safeline_skill.py --list-groups
  python safeline_skill.py --show-group 5

添加配置/白名单查询：
  python safeline_skill.py --show-config

附加（添加）IP 到指定组：
  python safeline_skill.py 1 1.1.1.1 2.2.2.2
  python safeline_skill.py 1 --ip-file ips.txt
        """
    )
    
    # 将主要的执行动作声明在一组互斥组中
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument("--list-groups", action="store_true", help="列出所有 IP 地址组")
    action_group.add_argument("--show-group", type=int, metavar="GROUP_ID", help="显示指定 IP 组详情及组内 IP")
    action_group.add_argument("--show-config", action="store_true", help="显示当前配置信息后退出")
    action_group.add_argument("--test", action="store_true", help="运行内置自测试（验证代码）")

    parser.add_argument("group_id", type=int, nargs="?", help="黑名单 IP 组 ID（执行附加参数时需要）")
    parser.add_argument("ips", nargs="*", help="需要封禁的 IP 地址")
    parser.add_argument("--ip-file", help="从文件读取 IP 列表（每行一个 IP）")
    parser.add_argument("--comment", default="自定义黑名单", help="(不再被附加上传，供兼容参数保留)")
    parser.add_argument("--url", dest="base_url", help="覆盖 .env 中的 SAFELINE_BASE_URL")
    parser.add_argument("--token", dest="token", help="覆盖 .env 中的 SAFELINE_TOKEN")

    args = parser.parse_args()

    # --test: 运行内置自测试后退出
    if args.test:
        success = run_tests()
        sys.exit(0 if success else 1)

    # 命令行参数优先，其次使用 .env / 环境变量中的值
    base_url = args.base_url or SAFELINE_BASE_URL
    token = args.token or SAFELINE_TOKEN

    tool = SafeLineIPBan(base_url, token)

    # 查看配置信息
    if args.show_config:
        config = tool.get_config_info()
        print("当前配置：")
        for k, v in config.items():
            print(f"  {k}: {v}")
        sys.exit(0)

    # 检查配置是否默认值警告
    if base_url == "https://waf.example.com:9443" or token == "YOUR_API_TOKEN":
        print(
            "警告：检测到默认占位符配置。\n"
            "请在技能根目录的 .env 文件中设置 SAFELINE_HOST、SAFELINE_PORT 和 SAFELINE_TOKEN，\n"
            "或通过 --url / --token 参数传入。",
            file=sys.stderr
        )

    # 查询全量 IP 组
    if args.list_groups:
        result = tool.get_ipgroups()
        if result["success"]:
            # 解析结构: {"data": {"data": {"nodes": [...]}}} 或类似的雷池返回体
            # 根据用户给出：{"data":{"nodes": [...] ...}}
            data = result.get("data", {})
            if "data" in data and "nodes" in data["data"]:
                nodes = data["data"]["nodes"]
            elif "nodes" in data:
                nodes = data["nodes"]
            elif "data" in data and isinstance(data["data"], dict) and "data" in data["data"] and "nodes" in data["data"]["data"]:
                nodes = data["data"]["data"]["nodes"]
            # 处理嵌套比较深的节点，基于所获取到的 "data"
            else:
               # 回退到直接层级尝试
               nodes = data.get("data", {}).get("nodes", [])
            
            print(f"==========================================")
            print(f"获 取 到 {len(nodes)} 个 IP 地址组信息：")
            print(f"==========================================")
            for node in nodes:
                print(f" [ID: {node.get('id')}] - 名称: {node.get('comment', '无备注')}")
            sys.exit(0)
        else:
            print(f"获取列表失败：{result.get('message', '未知原因')}", file=sys.stderr)
            sys.exit(1)

    # 查询指定 IP 组详情
    if args.show_group is not None:
        result = tool.get_ipgroup_detail(args.show_group)
        if result["success"]:
            # {"data": {"data": {"id": 5, "comment": "...", "ips": [...]}}} 
            resp_data = result.get("data", {})
            group_data = resp_data.get("data", {})
            if "data" in group_data:
                group_data = group_data["data"]

            ips = group_data.get("ips", [])
            print(f"==========================================")
            print(f"地址组 ID: {group_data.get('id', args.show_group)}")
            print(f"地址组名称: {group_data.get('comment', '未知')}")
            print(f"共包含 {len(ips)} 个 IP 地址")
            print(f"==========================================")
            for ip in ips:
                print(f"  - {ip}")
            sys.exit(0)
        else:
            print(f"获取 IP 组详情失败：{result.get('message', '未知原因')}", file=sys.stderr)
            sys.exit(1)

    # 如果均不是上述选项，则进入添加 (append) 模式
    # 强制要求 group_id
    if args.group_id is None:
        print("错误：执行附加封禁操作时，请提供目标地址组 <group_id> 以及需要封禁的 IP。或使用 `--list-groups` 等查询选项", file=sys.stderr)
        parser.print_usage(sys.stderr)
        sys.exit(1)

    # 收集要封禁的 IP
    target_ips = list(args.ips)
    if args.ip_file:
        try:
            with open(args.ip_file, 'r', encoding='utf-8') as f:
                file_ips = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                target_ips.extend(file_ips)
        except FileNotFoundError:
            print(f"错误：文件不存在 - {args.ip_file}", file=sys.stderr)
            sys.exit(1)

    if not target_ips:
        print("错误：没有提供需要添加到地址组中的 IP 地址", file=sys.stderr)
        sys.exit(1)

    # 执行附加封禁
    result = tool.append_ips(target_ips, args.group_id)

    # 输出结果
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 返回适当的退出码
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
