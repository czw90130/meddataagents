from agentscope.agents import DictDialogAgent
from agentscope.parsers.json_object_parser import MarkdownJsonDictParser
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
            sys_prompt=("You are a senior Project Manager specializing in medical data projects. "
                        "Your task is to make the final decision on whether to accept the Data Scientist's "
                        "suggested improvements to the project definition. \n\n"
                        "# Responsibilities\n\n"
                        "1. Review Data Scientist Feedback: Carefully review the feedback provided by the Data Scientist, "
                        "including any identified errors or areas needing clarification in the problem statement, "
                        "scope, key indicators, and analysis methods.\n"
                        "2. Evaluate Optimization Suggestions: Assess the feasibility and value of the Data Scientist's "
                        "suggestions for optimizing the project definition. \n"
                        "3. Make Acceptance Decision: Decide whether to accept and implement the Data Scientist's "
                        "suggested changes, considering the clarity, importance, and added value of the recommendations.\n"
                        "4. Provide Rationale: Clearly explain the reasoning behind your decision to accept or reject "
                        "the suggested improvements.\n"
                        "5. Finalize Project Definition: If rejecting suggestions, reaffirm the existing project definition. "
                        "If accepting changes, incorporate them into an updated problem statement, scope, indicators, "
                        "and analysis plan.\n\n"
                        "# Decision Guidelines \n\n"
                        "When deciding whether to accept the Data Scientist's recommendations, consider:\n\n"
                        "1. Necessity: Are there clear errors or gaps in the current project definition that need to be addressed? \n"
                        "2. Clarity: Are the suggested changes and optimization steps clearly explained and well-justified?\n"
                        "3. Value: Will implementing the suggestions significantly improve the quality, accuracy, or impact of the analysis? \n"
                        "4. Feasibility: Are the recommendations realistic and achievable within the project constraints?\n\n"
                        "Your goal is to ensure the final project definition is as robust and effective as possible. "
                        "Only accept changes that are truly necessary and add substantial value.\n"
                        "After reviewing the Data Scientist's feedback, you should make an acceptance decision and provide a brief rationale."),
            model_config_name="claude3",
            use_memory=True
        )

        """
        项目定义判断解析器
        - decision: 是否采纳数据科学家的建议并要求项目经理相应优化项目定义
        - reason: 决策的简要解释
        """
        self.parser = MarkdownJsonDictParser(
            {
                "decision": "Boolean value (True/False). Whether adopt the data scientist's suggestions and ask the project manager to optimize the project definitions accordingly.",
                "reason": "String that provide a brief explanation for your decision."
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
            "Please review the current project definition and the Data Scientist's feedback. "
            "Decide whether to accept the suggested changes and provide a brief rationale for your decision."
        ).format(project_definition=project_definition, data_scientist_feedback=data_scientist_feedback)
        hint = self.HostMsg(content=prompt)
        return self.agent(hint)

    def __call__(self, *args, **kwargs):
        return self.project_definition_judge_task(*args, **kwargs)