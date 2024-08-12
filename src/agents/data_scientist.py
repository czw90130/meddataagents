from agentscope.agents import DialogAgent
from functools import partial
from agentscope.message import Msg

class DataScientist:
    """
    数据科学家(DataScientist)
    专门审查和优化医疗数据分析项目的项目定义。
    """
    HostMsg = partial(Msg, name="Moderator", role="assistant")
    def __init__(self):
        self.agent = DialogAgent(
            name="DataScientist",
            sys_prompt=("You are a Data Scientist reviewing medical data analysis project definitions. "
                        "Your task is to evaluate the Project Manager's output and provide constructive feedback.\n\n"
                        "# Responsibilities\n"
                        "1. Review problem statement and analysis objectives\n"
                        "2. Evaluate key indicators and variables\n"
                        "3. Provide feedback to improve the project definition\n\n"
                        "# Guidelines\n"
                        "1. Ensure all elements are clear, specific, and relevant\n"
                        "2. Do NOT add or remove any customer requirements\n"
                        "3. Offer suggestions only when necessary, respecting the original scope\n"
                        "4. Provide clear, concise feedback with justifications"),
            model_config_name="claude3",
            use_memory=True
        )

    def project_definition_review_task(self, prev, msg):
        """
        项目定义审查任务提示词
        - {prev}: 项目定义
        - {msg}: 客户消息或审查信息
        """
        prompt = (
            "# Project definition\n"
            "```\n{prev}\n```\n\n"
            "# Customer Message or Review Information\n"
            "```\n{msg}\n```\n\n"
        ).format(prev=prev, msg=msg)
        hint = self.HostMsg(content=prompt)
        return self.agent(hint)

    def __call__(self, *args, **kwargs):
        return self.project_definition_review_task(*args, **kwargs)