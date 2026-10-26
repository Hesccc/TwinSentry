"""
splunk-skill — splunk_skill.py
=====================================
适用于 AI Agent 框架（如 Dify、LangChain、OpenClaw 等）。
本脚本封装了与 Splunk REST API（v10.2）的完整交互逻辑，提供 11 个工具方法：

  1.  health_check()                       — 连接检测，返回已安装应用列表
  2.  current_user()                       — 当前认证用户身份与权限
  3.  list_users()                         — 所有用户及角色
  4.  list_indexes()                       — 可访问索引列表
  5.  get_index_info(index_name)           — 特定索引详情
  6.  indexes_and_sourcetypes()            — 索引与 sourcetype 映射
  7.  search_splunk(query, ...)            — 执行 SPL 搜索（异步作业模式）
  8.  list_saved_searches()               — 列出保存的搜索
  9.  list_kvstore_collections()          — 列出 KV Store 集合
  10. create_kvstore_collection(name)     — 创建 KV Store 集合
  11. delete_kvstore_collection(name)     — 删除 KV Store 集合

使用前请修改下方 「配置区」 中的连接参数。
直接运行本脚本可进入自动测试模式，逐一验证所有功能。
"""

import json
import logging
import time
import urllib.parse
from typing import Any, Dict, Optional

import requests
import urllib3

# 抑制 SSL 不验证时的警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ╔══════════════════════════════════════════════╗
# ║                  配  置  区                  ║
# ╚══════════════════════════════════════════════╝
SPLUNK_HOST     = "192.168.0.1"     # Splunk 主机 IP 或域名（不含 http://）
SPLUNK_PORT     = 8089              # 管理端口，默认 8089
SPLUNK_USERNAME = "admin"           # 用户名（Basic Auth）
SPLUNK_PASSWORD = ""                # 密码（Basic Auth）
SPLUNK_TOKEN    = ""                # Bearer Token（填写后优先使用，留空则用用户名/密码）
SPLUNK_APP      = "search"          # App 命名空间（KV Store 操作使用）
VERIFY_SSL      = False             # 是否验证 SSL 证书（自签名证书请保持 False）
REQUEST_TIMEOUT = 60                # 单次请求超时（秒），默认60秒
SEARCH_TIMEOUT  = 120               # 等待搜索完成的超时（秒）,默认120秒
# ════════════════════════════════════════════════

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 辅助函数
# ─────────────────────────────────────────────────────────────────────────────

def _ok(data: Any) -> Dict[str, Any]:
    """构建成功响应"""
    return {"success": True, "data": data}


def _err(msg: str) -> Dict[str, Any]:
    """构建失败响应"""
    return {"success": False, "error": msg}


def _parse_entries(feed: dict) -> list:
    """
    从 Splunk Atom Feed JSON 中提取 entry 列表，
    并将每个 entry 的 content/name 字段扁平化为易于消费的 dict。
    """
    entries = feed.get("entry", [])
    result = []
    for entry in entries:
        item = {"name": entry.get("name", "")}
        content = entry.get("content", {})
        if isinstance(content, dict):
            item.update(content)
        result.append(item)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 主技能类
# ─────────────────────────────────────────────────────────────────────────────

class SplunkSkill:
    """
    Splunk Agent 技能类。
    封装 Splunk REST API，供 AI Agent 框架调用，执行搜索和管理操作。

    初始化示例：
        skill = SplunkSkill()                         # 使用脚本顶部配置
        skill = SplunkSkill(host="10.0.0.1",          # 覆盖连接参数
                            username="admin",
                            password="pass")
    """

    def __init__(
        self,
        host: str       = SPLUNK_HOST,
        port: int       = SPLUNK_PORT,
        username: str   = SPLUNK_USERNAME,
        password: str   = SPLUNK_PASSWORD,
        token: str      = SPLUNK_TOKEN,
        verify_ssl: bool = VERIFY_SSL,
        timeout: int    = REQUEST_TIMEOUT,
        app: str        = SPLUNK_APP,
    ):
        self.base_url   = f"https://{host}:{port}"
        self.username   = username
        self.password   = password
        self.token      = token.strip()
        self.verify_ssl = verify_ssl
        self.timeout    = timeout
        self.app        = app

        # 构建认证头 / 元组
        if self.token:
            self._auth_headers = {"Authorization": f"Bearer {self.token}"}
            self._auth_tuple   = None
        else:
            self._auth_headers = {}
            self._auth_tuple   = (self.username, self.password)

        self._session = requests.Session()
        self._session.verify = self.verify_ssl

    # ──────────────────────────────────────────────────────────────────────────
    # 内部请求封装
    # ──────────────────────────────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        data: Optional[dict]   = None,
        json_body: bool        = False,
    ) -> requests.Response:
        """
        发送 HTTP 请求到 Splunk REST API。
        自动附加认证信息，并强制返回 JSON 格式（output_mode=json）。
        """
        url = f"{self.base_url}{path}"

        # 强制 JSON 响应
        if params is None:
            params = {}
        if "output_mode" not in params:
            params["output_mode"] = "json"

        headers = dict(self._auth_headers)

        if json_body and data is not None:
            headers["Content-Type"] = "application/json"
            return self._session.request(
                method, url,
                params=params,
                json=data,
                headers=headers,
                auth=self._auth_tuple,
                timeout=self.timeout,
            )
        else:
            if data is not None:
                headers["Content-Type"] = "application/x-www-form-urlencoded"
            return self._session.request(
                method, url,
                params=params,
                data=data,
                headers=headers,
                auth=self._auth_tuple,
                timeout=self.timeout,
            )

    # ──────────────────────────────────────────────────────────────────────────
    # 搜索作业辅助流程
    # ──────────────────────────────────────────────────────────────────────────

    def _run_search_job(
        self,
        spl: str,
        earliest_time: str = "-60m",
        latest_time: str   = "now",
        max_count: int     = 100,
    ) -> Dict[str, Any]:
        """
        完整的 Splunk 异步搜索流程：
          1. 创建搜索作业（POST /services/search/jobs）
          2. 轮询作业状态直到完成
          3. 拉取并返回搜索结果
        """
        # Step 1: 创建作业
        try:
            # 生成命令（以 | 开头，如 tstats/metadata）不能加 search 前缀
            stripped = spl.strip()
            if stripped.startswith("|") or stripped.lower().startswith("search"):
                search_str = stripped
            else:
                search_str = f"search {stripped}"
            resp = self._request(
                "POST", "/services/search/jobs",
                data={
                    "search":        search_str,
                    "earliest_time": earliest_time,
                    "latest_time":   latest_time,
                    "max_count":     str(max_count),
                }
            )
        except Exception as e:
            return _err(f"创建搜索作业失败: {e}")

        if resp.status_code not in (200, 201):
            return _err(f"创建作业 HTTP {resp.status_code}: {resp.text[:300]}")

        try:
            sid = resp.json().get("sid")
        except Exception:
            return _err(f"解析 SID 失败，原始响应: {resp.text[:300]}")

        if not sid:
            return _err("未获取到搜索作业 SID")

        logger.info(f"[SplunkSkill] 搜索作业已创建, SID={sid}")

        # Step 2: 轮询等待完成
        start = time.time()
        while time.time() - start < SEARCH_TIMEOUT:
            try:
                poll = self._request("GET", f"/services/search/jobs/{sid}")
            except Exception as e:
                return _err(f"轮询作业状态异常: {e}")

            if poll.status_code == 404:
                return _err(f"作业 SID={sid} 不存在（已过期或被删除）")

            try:
                state = poll.json()
                entry = state.get("entry", [{}])[0]
                content = entry.get("content", {})
                is_done       = str(content.get("isDone", "0")) == "1"
                dispatch_state = content.get("dispatchState", "")
                failed         = str(content.get("isFailed", "0")) == "1"
            except Exception as e:
                return _err(f"解析作业状态失败: {e}")

            logger.debug(f"[SplunkSkill] SID={sid} 状态={dispatch_state}")

            if failed:
                messages = content.get("messages", {})
                return _err(f"搜索作业失败: {messages}")

            if is_done:
                break

            time.sleep(1)
        else:
            return _err(f"搜索作业超时（>{SEARCH_TIMEOUT}s），SID={sid}")

        # Step 3: 拉取结果
        try:
            res = self._request(
                "GET", f"/services/search/jobs/{sid}/results",
                params={"output_mode": "json", "count": str(max_count)},
            )
        except Exception as e:
            return _err(f"拉取搜索结果失败: {e}")

        if res.status_code != 200:
            return _err(f"拉取结果 HTTP {res.status_code}: {res.text[:300]}")

        try:
            result_json = res.json()
        except Exception:
            return _err(f"解析结果 JSON 失败: {res.text[:300]}")

        rows = result_json.get("results", [])
        logger.info(f"[SplunkSkill] 搜索完成，返回 {len(rows)} 条结果")
        return _ok({
            "sid":     sid,
            "count":   len(rows),
            "results": rows,
        })

    def _run_oneshot_search(
        self,
        spl: str,
        earliest_time: str = "-60m",
        latest_time: str   = "now",
        max_count: int     = 100,
    ) -> Dict[str, Any]:
        """
        Splunk 同步搜索（oneshot）流程：
        请求发送后会阻塞直到搜索完成并返回结果，适合获取少量数据。
        """
        try:
            stripped = spl.strip()
            if stripped.startswith("|") or stripped.lower().startswith("search"):
                search_str = stripped
            else:
                search_str = f"search {stripped}"
                
            resp = self._request(
                "POST", "/services/search/jobs",
                data={
                    "search":        search_str,
                    "earliest_time": earliest_time,
                    "latest_time":   latest_time,
                    "max_count":     str(max_count),
                    "exec_mode":     "oneshot",
                }
            )
        except Exception as e:
            return _err(f"创建同步搜索作业失败: {e}")

        if resp.status_code not in (200, 201):
            return _err(f"同步搜索 HTTP {resp.status_code}: {resp.text[:300]}")

        try:
            result_json = resp.json()
        except Exception:
            # oneshot 返回为空时也可能解析失败
            return _err(f"解析结果 JSON 失败: {resp.text[:300]}")

        if isinstance(result_json, list):
            rows = result_json
        elif isinstance(result_json, dict):
            rows = result_json.get("results", [])
        else:
            rows = []

        logger.info(f"[SplunkSkill] 同步搜索完成，返回 {len(rows)} 条结果")
        return _ok({
            "sid":     "oneshot",
            "count":   len(rows),
            "results": rows,
        })

    # ══════════════════════════════════════════════════════════════════════════
    # 工  具  方  法
    # ══════════════════════════════════════════════════════════════════════════

    def health_check(self) -> Dict[str, Any]:
        """
        检查与 Splunk 的连接，返回已安装应用程序列表。
        用于验证配置是否正确以及网络连通性。

        端点: GET /services/apps/local

        返回示例:
            {
                "success": True,
                "data": {
                    "total_apps": 12,
                    "apps": [{"name": "search", "label": "Search & Reporting", ...}, ...]
                }
            }
        """
        try:
            resp = self._request("GET", "/services/apps/local")
        except Exception as e:
            return _err(f"连接失败: {e}")

        if resp.status_code == 401:
            return _err("认证失败：用户名/密码或 Token 不正确")
        if resp.status_code != 200:
            return _err(f"HTTP {resp.status_code}: {resp.text[:300]}")

        try:
            feed = resp.json()
        except Exception:
            return _err("响应解析失败（非 JSON）")

        apps = []
        for entry in feed.get("entry", []):
            content = entry.get("content", {})
            apps.append({
                "name":    entry.get("name", ""),
                "label":   content.get("label", ""),
                "version": content.get("version", ""),
                "enabled": not content.get("disabled", False),
            })

        logger.info(f"[SplunkSkill] health_check 成功，检测到 {len(apps)} 个应用")
        return _ok({"total_apps": len(apps), "apps": apps})

    # ──────────────────────────────────────────────────────────────────────────

    def current_user(self) -> Dict[str, Any]:
        """
        返回当前已认证用户的身份和权限详细信息。

        端点: GET /services/authentication/current-context

        返回示例:
            {
                "success": True,
                "data": {
                    "username": "admin",
                    "roles": ["admin", "power"],
                    "capabilities": ["search", "rest_apps_management", ...]
                }
            }
        """
        try:
            resp = self._request("GET", "/services/authentication/current-context")
        except Exception as e:
            return _err(f"请求失败: {e}")

        if resp.status_code != 200:
            return _err(f"HTTP {resp.status_code}: {resp.text[:300]}")

        try:
            feed = resp.json()
            entry = feed.get("entry", [{}])[0]
            content = entry.get("content", {})
        except Exception as e:
            return _err(f"解析响应失败: {e}")

        user_info = {
            "username":     content.get("username", ""),
            "roles":        content.get("roles", []),
            "capabilities": content.get("capabilities", []),
            "real_name":    content.get("realName", ""),
            "email":        content.get("email", ""),
            "default_app":  content.get("defaultApp", ""),
        }
        logger.info(f"[SplunkSkill] 当前用户: {user_info['username']}")
        return _ok(user_info)

    # ──────────────────────────────────────────────────────────────────────────

    def list_users(self) -> Dict[str, Any]:
        """
        检索所有 Splunk 用户的列表，包括其角色和账户状态。
        需要管理员权限。

        端点: GET /services/authentication/users

        返回示例:
            {
                "success": True,
                "data": {
                    "total": 3,
                    "users": [{"name": "admin", "roles": [...], "email": "..."}, ...]
                }
            }
        """
        try:
            resp = self._request(
                "GET", "/services/authentication/users",
                params={"output_mode": "json", "count": "0"},
            )
        except Exception as e:
            return _err(f"请求失败: {e}")

        if resp.status_code == 403:
            return _err("权限不足：需要管理员权限才能列出用户")
        if resp.status_code != 200:
            return _err(f"HTTP {resp.status_code}: {resp.text[:300]}")

        try:
            feed = resp.json()
        except Exception as e:
            return _err(f"解析响应失败: {e}")

        users = []
        for entry in feed.get("entry", []):
            content = entry.get("content", {})
            users.append({
                "name":        entry.get("name", ""),
                "real_name":   content.get("realName", ""),
                "email":       content.get("email", ""),
                "roles":       content.get("roles", []),
                "default_app": content.get("defaultApp", ""),
                "locked_out":  content.get("locked-out", False),
            })

        logger.info(f"[SplunkSkill] 共 {len(users)} 个用户")
        return _ok({"total": len(users), "users": users})

    # ──────────────────────────────────────────────────────────────────────────

    def list_indexes(self) -> Dict[str, Any]:
        """
        列出当前凭据可访问的所有 Splunk 索引。

        端点: GET /services/data/indexes

        返回示例:
            {
                "success": True,
                "data": {
                    "total": 10,
                    "indexes": [{"name": "main", "total_event_count": 12345, ...}, ...]
                }
            }
        """
        try:
            resp = self._request(
                "GET", "/services/data/indexes",
                params={"output_mode": "json", "count": "0"},
            )
        except Exception as e:
            return _err(f"请求失败: {e}")

        if resp.status_code != 200:
            return _err(f"HTTP {resp.status_code}: {resp.text[:300]}")

        try:
            feed = resp.json()
        except Exception as e:
            return _err(f"解析响应失败: {e}")

        indexes = []
        for entry in feed.get("entry", []):
            content = entry.get("content", {})
            indexes.append({
                "name":              entry.get("name", ""),
                "total_event_count": content.get("totalEventCount", 0),
                "current_db_size_mb": round(
                    int(content.get("currentDBSizeMB", 0)), 2
                ),
                "max_total_data_size_mb": content.get("maxTotalDataSizeMB", 0),
                "home_path":         content.get("homePath", ""),
                "frozen_time_period_in_secs": content.get("frozenTimePeriodInSecs", 0),
                "disabled":          content.get("disabled", False),
            })

        logger.info(f"[SplunkSkill] 共 {len(indexes)} 个索引")
        return _ok({"total": len(indexes), "indexes": indexes})

    # ──────────────────────────────────────────────────────────────────────────

    def get_index_info(self, index_name: str) -> Dict[str, Any]:
        """
        获取特定 Splunk 索引的详细信息。

        参数:
            index_name (str): 索引名称，例如 "main"

        端点: GET /services/data/indexes/{index_name}

        返回示例:
            {
                "success": True,
                "data": {
                    "name": "main",
                    "total_event_count": 9999,
                    ...
                }
            }
        """
        if not index_name:
            return _err("index_name 参数不能为空")

        encoded_name = urllib.parse.quote(index_name, safe="")
        try:
            resp = self._request("GET", f"/services/data/indexes/{encoded_name}")
        except Exception as e:
            return _err(f"请求失败: {e}")

        if resp.status_code == 404:
            return _err(f"索引 '{index_name}' 不存在")
        if resp.status_code != 200:
            return _err(f"HTTP {resp.status_code}: {resp.text[:300]}")

        try:
            feed = resp.json()
            entry = feed.get("entry", [{}])[0]
            content = entry.get("content", {})
        except Exception as e:
            return _err(f"解析响应失败: {e}")

        info = {
            "name":                      entry.get("name", index_name),
            "total_event_count":         content.get("totalEventCount", 0),
            "current_db_size_mb":        content.get("currentDBSizeMB", 0),
            "max_total_data_size_mb":    content.get("maxTotalDataSizeMB", 0),
            "home_path":                 content.get("homePath", ""),
            "cold_path":                 content.get("coldPath", ""),
            "thawed_path":               content.get("thawedPath", ""),
            "frozen_time_period_in_secs": content.get("frozenTimePeriodInSecs", 0),
            "min_time":                  content.get("minTime", ""),
            "max_time":                  content.get("maxTime", ""),
            "disabled":                  content.get("disabled", False),
            "is_internal":               content.get("isInternal", False),
        }
        logger.info(f"[SplunkSkill] 索引 '{index_name}' 信息已获取")
        return _ok(info)

    # ──────────────────────────────────────────────────────────────────────────

    def indexes_and_sourcetypes(self) -> Dict[str, Any]:
        """
        返回所有索引及其相关 sourcetype 的映射关系。
        通过执行 tstats SPL 查询实现，需要 tstats 命令执行权限。

        使用的 SPL: | tstats count WHERE index=* BY index, sourcetype

        返回示例:
            {
                "success": True,
                "data": {
                    "total_combinations": 25,
                    "mapping": {
                        "main": ["syslog", "access_combined", ...],
                        "_internal": ["splunkd", "scheduler", ...]
                    }
                }
            }
        """
        spl = "| tstats count WHERE index=* BY index, sourcetype"
        result = self._run_search_job(
            spl,
            earliest_time="-60m",
            latest_time="now",
            max_count=10000,
        )

        if not result["success"]:
            return result

        rows = result["data"]["results"]
        mapping: Dict[str, list] = {}
        for row in rows:
            idx = row.get("index", "")
            st  = row.get("sourcetype", "")
            if idx:
                mapping.setdefault(idx, [])
                if st and st not in mapping[idx]:
                    mapping[idx].append(st)

        logger.info(
            f"[SplunkSkill] 索引-sourcetype 映射完成，"
            f"{len(mapping)} 个索引，{len(rows)} 个组合"
        )
        return _ok({
            "total_combinations": len(rows),
            "mapping": mapping,
        })

    # ──────────────────────────────────────────────────────────────────────────

    def search_splunk(
        self,
        query: str,
        earliest_time: str = "-60m",
        latest_time: str   = "now",
        max_count: int     = 100,
        exec_mode: str     = "async",
    ) -> Dict[str, Any]:
        """
        执行用户提供的 SPL 搜索查询，支持异步和一键同步搜索模式。

        参数:
            query        (str): SPL 查询语句，例如 "index=main | head 20"
            earliest_time(str): 搜索起始时间，默认 "-60m"（支持相对时间和绝对时间）
            latest_time  (str): 搜索结束时间，默认 "now"
            max_count    (int): 最大返回结果数，默认 100
            exec_mode    (str): 执行模式，支持 "async" (大批量) 或 "oneshot" (少量数据等待返回)，默认 "async"

        返回示例:
            {
                "success": True,
                "data": {
                    "sid": "1712345678.1",
                    "count": 20,
                    "results": [{"_raw": "...", "_time": "...", ...}, ...]
                }
            }
        """
        if not query or not query.strip():
            return _err("query 参数不能为空")
        if max_count < 1:
            return _err("max_count 必须大于 0")

        logger.info(f"[SplunkSkill] 执行搜索(模式={exec_mode}): {query[:100]}...")
        if exec_mode == "oneshot":
            return self._run_oneshot_search(
                spl=query,
                earliest_time=earliest_time,
                latest_time=latest_time,
                max_count=max_count,
            )
        else:
            return self._run_search_job(
                spl=query,
                earliest_time=earliest_time,
                latest_time=latest_time,
                max_count=max_count,
            )

    # ──────────────────────────────────────────────────────────────────────────

    def list_saved_searches(self) -> Dict[str, Any]:
        """
        列出 Splunk 实例中所有已保存的搜索，包括 Alert 和 Report。

        端点: GET /services/saved/searches

        返回示例:
            {
                "success": True,
                "data": {
                    "total": 5,
                    "searches": [
                        {
                            "name": "My Alert",
                            "search": "index=main error | stats count",
                            "is_scheduled": True,
                            "cron_schedule": "*/5 * * * *"
                        }, ...
                    ]
                }
            }
        """
        try:
            resp = self._request(
                "GET", "/services/saved/searches",
                params={"output_mode": "json", "count": "0"},
            )
        except Exception as e:
            return _err(f"请求失败: {e}")

        if resp.status_code != 200:
            return _err(f"HTTP {resp.status_code}: {resp.text[:300]}")

        try:
            feed = resp.json()
        except Exception as e:
            return _err(f"解析响应失败: {e}")

        searches = []
        for entry in feed.get("entry", []):
            content = entry.get("content", {})
            searches.append({
                "name":          entry.get("name", ""),
                "search":        content.get("search", ""),
                "description":   content.get("description", ""),
                "is_scheduled":  content.get("is_scheduled", False),
                "cron_schedule": content.get("cron_schedule", ""),
                "is_alert":      bool(content.get("alert_type", "")),
                "dispatch_app":  content.get("request.ui_dispatch_app", ""),
                "author":        (entry["author"] if isinstance(entry.get("author"), str)
                                  else entry.get("author", {}).get("name", "")),  # 兼容 str/dict
            })

        logger.info(f"[SplunkSkill] 共 {len(searches)} 个保存的搜索")
        return _ok({"total": len(searches), "searches": searches})

    # ──────────────────────────────────────────────────────────────────────────

    def list_kvstore_collections(self) -> Dict[str, Any]:
        """
        检索当前 App 命名空间下所有 KV Store 集合。

        端点: GET /servicesNS/nobody/{app}/storage/collections/config

        返回示例:
            {
                "success": True,
                "data": {
                    "total": 3,
                    "collections": [{"name": "my_collection", ...}, ...]
                }
            }
        """
        try:
            resp = self._request(
                "GET",
                f"/servicesNS/nobody/{self.app}/storage/collections/config",
                params={"output_mode": "json", "count": "0"},
            )
        except Exception as e:
            return _err(f"请求失败: {e}")

        if resp.status_code == 404:
            return _err(f"App '{self.app}' 不存在或没有 KV Store 支持")
        if resp.status_code != 200:
            return _err(f"HTTP {resp.status_code}: {resp.text[:300]}")

        try:
            feed = resp.json()
        except Exception as e:
            return _err(f"解析响应失败: {e}")

        collections = []
        for entry in feed.get("entry", []):
            content = entry.get("content", {})
            # 提取 field 定义（key 以 "field." 开头）
            fields = {
                k.replace("field.", ""): v
                for k, v in content.items()
                if k.startswith("field.")
            }
            collections.append({
                "name":        entry.get("name", ""),
                "app":         entry.get("acl", {}).get("app", self.app),
                "owner":       entry.get("acl", {}).get("owner", ""),
                "fields":      fields,
                "accelerated": content.get("accelerated_fields.{}".format(""), {}),
            })

        logger.info(f"[SplunkSkill] 共 {len(collections)} 个 KV Store 集合")
        return _ok({"total": len(collections), "collections": collections})

    # ──────────────────────────────────────────────────────────────────────────

    def create_kvstore_collection(self, collection_name: str) -> Dict[str, Any]:
        """
        在 Splunk 中创建一个新的 KV Store 集合。

        参数:
            collection_name (str): 集合名称，例如 "threat_intel"

        端点: POST /servicesNS/nobody/{app}/storage/collections/config

        返回示例:
            {
                "success": True,
                "data": {"collection_name": "threat_intel", "message": "集合创建成功"}
            }
        """
        if not collection_name or not collection_name.strip():
            return _err("collection_name 参数不能为空")

        try:
            resp = self._request(
                "POST",
                f"/servicesNS/nobody/{self.app}/storage/collections/config",
                data={"name": collection_name.strip()},
            )
        except Exception as e:
            return _err(f"请求失败: {e}")

        if resp.status_code == 409:
            return _err(f"集合 '{collection_name}' 已存在")
        if resp.status_code not in (200, 201):
            return _err(f"HTTP {resp.status_code}: {resp.text[:300]}")

        logger.info(f"[SplunkSkill] KV Store 集合 '{collection_name}' 创建成功")
        return _ok({
            "collection_name": collection_name,
            "message": f"集合 '{collection_name}' 创建成功",
        })

    # ──────────────────────────────────────────────────────────────────────────

    def delete_kvstore_collection(self, collection_name: str) -> Dict[str, Any]:
        """
        从 Splunk 中删除指定的 KV Store 集合。
        需要管理员权限，操作不可逆。

        参数:
            collection_name (str): 要删除的集合名称

        端点: DELETE /servicesNS/nobody/{app}/storage/collections/config/{name}

        返回示例:
            {
                "success": True,
                "data": {"collection_name": "threat_intel", "message": "集合已删除"}
            }
        """
        if not collection_name or not collection_name.strip():
            return _err("collection_name 参数不能为空")

        encoded = urllib.parse.quote(collection_name.strip(), safe="")
        try:
            resp = self._request(
                "DELETE",
                f"/servicesNS/nobody/{self.app}/storage/collections/config/{encoded}",
            )
        except Exception as e:
            return _err(f"请求失败: {e}")

        if resp.status_code == 404:
            return _err(f"集合 '{collection_name}' 不存在")
        if resp.status_code == 403:
            return _err("权限不足：需要管理员权限才能删除集合")
        if resp.status_code not in (200, 201):
            return _err(f"HTTP {resp.status_code}: {resp.text[:300]}")

        logger.info(f"[SplunkSkill] KV Store 集合 '{collection_name}' 已删除")
        return _ok({
            "collection_name": collection_name,
            "message": f"集合 '{collection_name}' 已成功删除",
        })


# ─────────────────────────────────────────────────────────────────────────────
# 内置测试模式（直接运行本脚本时触发）
# ─────────────────────────────────────────────────────────────────────────────

def _print_result(label: str, result: dict):
    """格式化打印测试结果"""
    success = result.get("success", False)
    status  = "✅ 成功" if success else "❌ 失败"
    print(f"\n{'─' * 60}")
    print(f"[{label}] {status}")
    if success:
        data = result.get("data", {})
        if isinstance(data, dict):
            for k, v in data.items():
                val_str = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
                # 长列表截断显示
                if len(val_str) > 200:
                    val_str = val_str[:200] + " ... (截断)"
                print(f"  {k}: {val_str}")
        else:
            print(f"  结果: {data}")
    else:
        print(f"  错误: {result.get('error', '未知错误')}")


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    print("=" * 60)
    print("   splunk-skill — 功能自动测试")
    print(f"   目标: https://{SPLUNK_HOST}:{SPLUNK_PORT}")
    auth_mode = "Bearer Token" if SPLUNK_TOKEN else f"Basic Auth ({SPLUNK_USERNAME})"
    print(f"   认证: {auth_mode}")
    print("=" * 60)

    skill = SplunkSkill()

    # ── 测试 1: 连接检测 ─────────────────────────────────────────────────────
    r = skill.health_check()
    _print_result("health_check — 连接检测", r)
    if not r["success"]:
        print("\n⛔ 连接失败，请检查配置区参数后重试。退出测试。")
        sys.exit(1)

    # ── 测试 2: 当前用户 ─────────────────────────────────────────────────────
    _print_result("current_user — 当前用户", skill.current_user())

    # ── 测试 3: 用户列表 ─────────────────────────────────────────────────────
    _print_result("list_users — 用户列表", skill.list_users())

    # ── 测试 4: 索引列表 ─────────────────────────────────────────────────────
    idx_result = skill.list_indexes()
    _print_result("list_indexes — 索引列表", idx_result)

    # ── 测试 5: 特定索引详情（使用第一个可用索引）──────────────────────────
    first_index = "_internal"  # 默认使用 _internal，几乎所有 Splunk 实例都有
    if idx_result["success"] and idx_result["data"]["indexes"]:
        first_index = idx_result["data"]["indexes"][0]["name"]
    _print_result(
        f"get_index_info — 索引详情 ('{first_index}')",
        skill.get_index_info(first_index),
    )

    # ── 测试 6: 索引与 sourcetype 映射 ───────────────────────────────────────
    print(f"\n⏳ 正在执行 tstats 查询，最长等待 {REQUEST_TIMEOUT} 秒...")
    _print_result("indexes_and_sourcetypes — 索引 sourcetype 映射", skill.indexes_and_sourcetypes())

    print(f"\n⏳ 正在执行 SPL 搜索 (Async)，最长等待 {SEARCH_TIMEOUT} 秒...")
    _print_result(
        "search_splunk (Async) — SPL 搜索 (index=_internal | head 5)",
        skill.search_splunk(
            query="index=_internal | head 5",
            earliest_time="-1h",
            latest_time="now",
            max_count=5,
        ),
    )

    print(f"\n⏳ 正在执行 SPL 搜索 (Oneshot)...")
    _print_result(
        "search_splunk (Oneshot) — SPL 搜索 (index=_internal | head 1)",
        skill.search_splunk(
            query="index=_internal | head 1",
            exec_mode="oneshot",
        ),
    )

    # ── 测试 8: 保存的搜索 ───────────────────────────────────────────────────
    _print_result("list_saved_searches — 保存的搜索", skill.list_saved_searches())

    # ── 测试 9-11: KV Store 操作 ─────────────────────────────────────────────
    test_collection = "skill_test_collection_tmp"

    _print_result("list_kvstore_collections — KV Store 集合列表", skill.list_kvstore_collections())

    print(f"\n⏳ 创建测试集合 '{test_collection}'...")
    create_result = skill.create_kvstore_collection(test_collection)
    _print_result(f"create_kvstore_collection — 创建集合", create_result)

    print(f"\n⏳ 删除测试集合 '{test_collection}'...")
    del_result = skill.delete_kvstore_collection(test_collection)
    _print_result(f"delete_kvstore_collection — 删除集合", del_result)

    # ── 总结 ─────────────────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print("   splunk-skill 功能测试完成！")
    print(f"{'═' * 60}\n")
