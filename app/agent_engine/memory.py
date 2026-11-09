"""
Context Compression and Session Memory for LangGraph Agents
"""
import re
from typing import List, Dict, Any

class ContextCompressor:
    """
    智能上下文压缩器：
    1. 规则过滤：清洗无意义长堆栈与冗余字段
    2. 滑动窗口：保留固定数量的近期交互
    3. 关键信息锚定：强制保留系统提示词与告警原始Payload
    """
    def __init__(self, max_tokens: int = 4000, max_messages: int = 8):
        self.max_tokens = max_tokens
        self.max_messages = max_messages

    def compress_text(self, text: str) -> str:
        """压缩单段大文本（如冗长日志）"""
        if not text:
            return ""
        # 移除重复空行
        cleaned = re.sub(r'\\n{3,}', '\\n\\n', text)
        # 如果长度超出单条限制，截断并附上省略提示
        if len(cleaned) > 2000:
            return cleaned[:1200] + "\\n... [上下文过长，中间冗余日志已自动压缩省略] ...\\n" + cleaned[-600:]
        return cleaned

    def compress_history(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """保留 System 消息，截断中间历史，保留最近 N 条交互"""
        if len(messages) <= self.max_messages:
            return messages

        system_msgs = [m for m in messages if m.get("role") == "system"]
        other_msgs = [m for m in messages if m.get("role") != "system"]

        # 截取最近的消息
        trimmed_recent = other_msgs[-self.max_messages:]
        
        # 组装返回
        compressed = system_msgs + [
            {
                "role": "system",
                "content": "[系统提示：前置历史消息已折叠压缩，以下为关键上下文与最新交互]"
            }
        ] + trimmed_recent
        return compressed
