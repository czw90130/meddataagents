import os
import sys
from agentscope.agents import DictDialogAgent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from yaml_object_parser import MarkdownYAMLDictParser
from functools import partial
from agentscope.message import Msg

class ProjectManager:
    """
    项目经理(ProjectManager)
    负责医疗数据项目的需求分析和问题定义阶段。
    """
    HostMsg = partial(Msg, name="Moderator", role="assistant")
    def __init__(self):
        self.agent = DictDialogAgent(
            name="ProjectManager",
            sys_prompt = (
                "You are a Project Manager for medical data projects, leading the needs analysis and problem definition phase. "
                "Your goal is to ensure project objectives are clearly defined and aligned with stakeholder requirements."),
            model_config_name="kuafu3.5",
            use_memory=True
        )
        
        self.parser = MarkdownYAMLDictParser(
            content_hint={
                "problem_statement": "String. Description of the specific problem or challenge to be addressed.",
                "analysis_objectives": "String. Specific analysis objectives and expected outcomes.",
                "key_indicators": "String. ALL key indicators, variables, data items, and keys provided by the Customer, including those found in long text.",
                "continue_ask": "Boolean value (True/False). Whether need Customer give more infomation.",
                "message": "String. questions for Customer if continue_ask==True else other infomation."
            },
            keys_to_content="message",
            keys_to_metadata=True
        )
        self.agent.set_parser(self.parser)

    def project_definition_task(self, prev, msg):
        """
        项目定义任务提示词
        - {prev}: 先前的项目信息
        - {msg}: 客户对话或审查信息
        """
        prompt = (
            "<key_responsibilities>\n"
                "1. Define the problem statement and analysis objectives based on input.\n"
                "2. Identify and document ALL key indicators, including their possible values or ranges when provided.\n"
                "3. Analyze all information, including long texts, to extract relevant data points.\n"
                "4. Determine if additional information is needed from the input.\n"
            "</key_responsibilities>\n"
            
            "<important_guidelines>\n"
                "1. Preserve input requirements exactly as stated unless explicitly permitted to modify.\n"
                "2. Process all provided information, including lengthy texts, as they may contain crucial details.\n"
                "3. For each key indicator, record both its name and associated value options or ranges if available.\n"
                "4. Include all identified indicators, even if specific values are not provided.\n"
                "5. Maintain a comprehensive and detailed approach to data collection and analysis.\n"
            "</important_guidelines>\n"
            
            "<instructions>\n"
                "Remember to set continue_ask to True if more information is needed from the input, otherwise False.\n"
                "Provide clear, concise responses that align with the parser's expected structure.\n"
            "</instructions>\n"
        )
                
        if prev:
            prompt += f"<previous_information>\n{prev}\n</previous_information>\n"
        prompt += f"<input>\n{msg}\n</input>\n"
        
        hint = self.HostMsg(content=prompt)
        return self.agent(hint)

    def __call__(self, *args, **kwargs):
        return self.project_definition_task(*args, **kwargs)