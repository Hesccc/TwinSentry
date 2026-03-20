"""
TwinSentry LangChain Tool Wrapper 示例
展示如何将 Python 技能包转换为标准的 LangChain BaseTool，供 LangChain Agent 直接使用。
"""
from typing import Optional, Type, Dict, Any
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

# 导入原生提供的 SDK
from analysis_agent_skill import TwinSentryAnalysisSkill

class SubmitAnalysisInput(BaseModel):
    """TwinSentry 提交分析结论的输入 Schema 定义"""
    alert_id: int = Field(..., description="TwinSentry 告警 ID（在上下文中获取）")
    analysis_log: str = Field(..., description="LLM 对该告警的最终分析结论和判定日志")
    enrichment_data: Optional[Dict[str, Any]] = Field(None, description="从告警中提取的任何有助于后续规则匹配的 JSON 键值对")

class TwinSentrySubmitAnalysisTool(BaseTool):
    name = "twinsentry_submit_analysis"
    description = "将你对告警的分析结论通过该工具提交给 TwinSentry 系统"
    args_schema: Type[BaseModel] = SubmitAnalysisInput
    
    # 将 SDK 实例绑定到工具上
    skill_client: TwinSentryAnalysisSkill = TwinSentryAnalysisSkill()

    def _run(self, alert_id: int, analysis_log: str, enrichment_data: Optional[Dict[str, Any]] = None) -> str:
        """同步执行工具操作"""
        success = self.skill_client.submit_result(
            alert_id=alert_id,
            analysis_log=analysis_log,
            enrichment_data=enrichment_data
        )
        if success:
            return f"成功提交告警 {alert_id} 的分析结论！"
        else:
            return f"提交告警 {alert_id} 结论失败，请检查连接或参数。"
            
    async def _arun(self, alert_id: int, analysis_log: str, enrichment_data: Optional[Dict[str, Any]] = None) -> str:
        """异步执行，可根据需要实现 Async 客户端"""
        raise NotImplementedError("本工具暂不支持异步调取。")

# --- Agent 组装思路如下 ---
# from langchain.agents import AgentExecutor, create_openai_functions_agent
# tools = [TwinSentrySubmitAnalysisTool()]
# ... 
