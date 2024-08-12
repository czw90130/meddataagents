import os
import sys
from agentscope.agents import DictDialogAgent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from yaml_object_parser import MarkdownYAMLDictParser
from functools import partial
from agentscope.message import Msg

class ProjectMaster:
    """
    项目主管(ProjectMaster)
    作为高级项目经理，负责决定是否接受数据科学家对项目定义的改进建议。
    """
    HostMsg = partial(Msg, name="Moderator", role="assistant")
    def __init__(self):
        self.agent = DictDialogAgent(
            name="ProjectMaster",
            sys_prompt=("You are a senior Project Manager for medical data projects. "
                        "Your task is to decide whether to accept the Data Scientist's suggested improvements. "
                        "Your primary goal is to ensure the project progresses quickly.\n\n"
                        "# Key Points\n"
                        "1. Prioritize rapid project approval\n"
                        "2. Only accept changes that are absolutely necessary and significantly valuable\n"
                        "3. Maintain the original project scope and customer requirements\n"
                        "4. Provide a brief rationale for your decision"),
            model_config_name="claude3",
            use_memory=True
        )

        self.parser = MarkdownYAMLDictParser(
            {
                "decision": "Boolean value (True/False). Whether to adopt the Data Scientist's suggestions.",
                "reason": "String. Brief explanation for your decision."
            }
        )
        self.agent.set_parser(self.parser)

    def project_definition_judge_task(self, project_definition, data_scientist_feedback):
        """
        项目定义判断任务提示词
        - {project_definition}: 当前的项目定义
        - {data_scientist_feedback}: 数据科学家的反馈
        """
        prompt = (
            "# Current Project Definition\n"
            "```\n{project_definition}\n```\n\n"
            "# Data Scientist's Feedback\n"
            "```\n{data_scientist_feedback}\n```\n\n"
            "Review the project definition and feedback. Decide whether to accept changes."
        ).format(project_definition=project_definition, data_scientist_feedback=data_scientist_feedback)
        hint = self.HostMsg(content=prompt)
        return self.agent(hint)

    def __call__(self, *args, **kwargs):
        return self.project_definition_judge_task(*args, **kwargs)