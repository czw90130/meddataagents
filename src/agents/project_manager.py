from agentscope.agents import DictDialogAgent
from agentscope.parsers.json_object_parser import MarkdownJsonDictParser
from functools import partial
from agentscope.message import Msg

class ProjectManager:
    """
    项目经理(ProjectManager)
    负责领导医疗数据项目的需求分析和问题定义阶段。确保项目范围、目标和关键指标明确定义并与利益相关者需求一致。
    """
    HostMsg = partial(Msg, name="Moderator", role="assistant")
    def __init__(self):
        self.agent = DictDialogAgent(
            name="ProjectManager",
            sys_prompt=("You are a Project Manager specializing in medical data projects. "
                        "Your task is to lead the needs analysis and problem definition phase for data analysis projects. "
                        "You will ensure that the project scope, objectives, "
                        "and key indicators are clearly defined and aligned with stakeholder requirements.\n\n"
                        "# Responsibilities\n\n"
                        "1. Define Problem and Objectives: "
                        "Clearly articulate the specific problem or challenge to be addressed and set clear, "
                        "measurable analysis objectives.\n"
                        "2. Determine Scope: "
                        "Establish the time, geographic, and population range for the analysis\n"
                        "3. Identify Key Indicators: "
                        "Specify the key indicators and variables that are critical to the analysis.\n"
                        "4. Develop Initial Analysis Plan: "
                        "Outline the preliminary analysis methods and expected outcomes.\n"
                        "5. Customer Communication: "
                        "Communicate with the customer to ensure alignment and address any concerns.\n\n"
                        "# Process\n"
                        "1. Problem Definition: "
                        "Collaborate with the Customer or Data Scientist to define the problem statement and analysis objectives. "
                        "If collaborating with the Customer, you can set continue_ask to True if you need more information. "
                        "Always set continue_ask to False if collaborating with others.\n"
                        "2. Scope Determination: "
                        "Determine the appropriate scope for the analysis, including time range, "
                        "geographic range, and population range, within the existing dataset "
                        "and perform an initial screening of the dataset to identify a subset of data "
                        "that meets the project requirements.\n"
                        "3. Key Indicator Identification: "
                        "Identify the most relevant indicators and variables for the analysis.\n"
                        "4. Initial Analysis Planning: "
                        "Develop a preliminary analysis plan, including the methods to be used and the expected outcomes.\n\n"
                        "You will receive content in the following format:"
                        "\n```\n{\"collaborator\":\"/* Customer or others */\", "
                        "\"message\":\"/* Message that the collaborator gives for project_definition. "
                        "Use the same language as the Customer.*/\"}\n```"),
            model_config_name="claude3",
            use_memory=True
        )
        
        """
        项目定义解析器
        - problem_statement: 待解决的具体问题或挑战描述
        - analysis_objectives: 具体分析目标和预期结果
        - scope: 分析的时间范围、地理范围和人群范围
        - key_indicators: 对分析至关重要的关键指标和变量
        - analysis_methods: 初步分析方法和预期结果
        - continue_ask: 是否需要客户提供更多信息
        - message: 如果continue_ask为True，则为向客户提出的问题；否则为其他信息
        """
        self.parser = MarkdownJsonDictParser(
            content_hint={
                "problem_statement": "String. Description of the specific problem or challenge to be addressed.",
                "analysis_objectives": "String. Specific analysis objectives and expected outcomes.",
                "scope": "String. Time range, geographic range, and population range for the analysis.",
                "key_indicators": "String. Key indicators and variables critical to the analysis.",
                "analysis_methods": "String. Preliminary analysis methods and expected outcomes.",
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
            "# Previous Information\n"
            "```\n{prev}\n```\n\n"
            "# Customer Conversation or Review Information\n"
            "```\n{msg}\n```\n\n"
        ).format(prev=prev, msg=msg)
        hint = self.HostMsg(content=prompt)
        return self.agent(hint)

    def __call__(self, *args, **kwargs):
        return self.project_definition_task(*args, **kwargs)