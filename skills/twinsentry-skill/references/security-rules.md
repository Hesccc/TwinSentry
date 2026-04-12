# 安全规范与操作约束 (Security Rules)

在此强调，任何对接给 TwinSentry 业务使用的自动化 Action/Disposition Agent 都被赋予了一定的业务处置操作权（如拦截防火墙策略、关闭网络连接甚至阻断服务器等）。正因如此，所有的开发和使用都应当具备最高等级的安全防范红线意识。

## 1. 凭据的零信任原则 (No Hardcoded Secrets)
- **绝对禁止**将云主机的 `AK/SK`、或者 TwinSentry 的 `ACTION_AGENT_KEY` 以明文的形式写死并且在 GitHub 或者是局域网代码仓库中流通。
- Agent 在开发之初，有且仅有的唯一通道应当使用 `python-dotenv` 或等效的主机加载工具从受保护的 `.env` 中调出凭据。

## 2. 对不可逆破坏性动作实施二次复核 (Human In The Loop)
在编写处置 Action Agent 的执行逻辑代码时：
- 常规安全管控（屏蔽异常 IP、限制僵尸网络访问、对设备实施断网隔离）可以直接走自动化程序链路。
- 但如果面临 **大面积删除容器**、**Drop/清空业务数据库** 等存在极端操作风险的高危阻断场景，决不能任由大模型幻觉直接向远端发起执行代码。必须要在 Agent 内设置拦截点，使用微信/钉钉或邮件下发“二次复核授权卡片”，收到安全专家亲手操作的 "Approve" 确认信号之后再予以触发。

## 3. 防止日志二次回传引发核心泄密 (Log Sanitization)
- **极度注意日志脱敏**：在构造待展示给用户的 `action_log` 或者 `analysis_log` 文本时，假设这期间系统交互使用到了你个人的 OAuth Token 或其他网关 Session 参数，切勿把含有此类敏感请求 Header 的 Response 结果原封不动的打包反馈进 TwinSentry。
- 所有的 Agent 日志都会进入并长期存储在 TwinSentry 中控后台的审计与数据大盘里。

## 4. 防范告警载荷中引发注入攻击 (Injection & ReDOS Reflection)
- 不要轻易相信并原生执行从告警原文 `raw_text` 或者 `text_lines` 传过来的字段！
- 攻击者的原始网络包载荷中极大可能具备特意构造的 XSS HTML 以及反向 Shell 指令，如果直接未作校验和提取拼接传给本地的 `subprocess.run` 或 `os.system`，或者不做净化直接推给 LLM，将会有致命的安全隐患！
- 强烈杜绝任何意义上的 `eval()` 函数读取执行行为。避免将系统大门暴露在反向命令注入漏洞中。
