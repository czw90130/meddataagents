import os
import sys
from agentscope.agents import DictDialogAgent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from yaml_object_parser import MarkdownYAMLDictParser
from functools import partial
from agentscope.message import Msg

class AnnotationJudge:
    """
    注释评判员(AnnotationJudge)
    专家评判员，需要对是否采纳审查员的建议并要求注释员优化注释，或忽略审查员的意见直接接受注释员的结果做出最终决定。
    """
    HostMsg = partial(Msg, name="Moderator", role="assistant")
    def __init__(self):
        self.agent = DictDialogAgent(
            name="AnnotationJudge",
            sys_prompt=("You are an expert judge who needs to make a final decision on whether to adopt "
                        "the Reviewer's suggestions and ask the Annotator to optimize the annotations, "
                        "or ignore the Reviewer's opinions and directly accept the Annotator's results."),
            model_config_name="kuafu3.5",
            use_memory=True
        )

        """
        注释评判解析器
        - decision: 是否采纳审查员的建议并要求注释员相应优化注释
        - reason: 决策的简要解释
        """
        self.parser = MarkdownYAMLDictParser(
            content_hint={
                "decision": "Boolean value (True/False). Whether adopt the reviewer's suggestions and ask the annotator to optimize the annotations accordingly.",
                "reason": "String that provide a brief explanation for your decision."
            }
        )
        self.agent.set_parser(self.parser)

    def annotate_judge_task(self, tags, require, info):
        """
        注释评判任务提示词
        - {tags}: JSON医疗实体注释参考
        - {require}: 注释要求或优化建议
        - {info}: 待注释的信息
        """
        prompt = (
            "# Decision Guidelines\n"
            "When making your decision, consider the following guidelines:\n"
            "1. If there are no obvious errors in the annotations, you should consider making a decision of False.\n"
            "2. If the optimization suggestions provided by the Reviewer are not very clear or important, you should consider making a decision of False.\n"
            "3. If the existing annotations are already accurate and complete enough, you should consider making a decision of False.\n\n"
            "Your goal is to ensure that any changes to the annotations are necessary and add significant value.\n\n"
            "Based on the reference and the Reviewer's feedback, you need to make a decision and provide a brief reason."
            "# JSON Reference for Medical Entity Annotation\n"
            "```\n{tags}\n```\n\n"
            "# Annotation Requirements or Optimization Suggestions\n"
            "```\n{require}\n```\n"
            "# Information to be Annotated\n"
            "```\n{info}\n```\n"
        ).format(tags=tags, require=require, info=info)
        hint = self.HostMsg(content=prompt)
        return self.agent(hint)

    def __call__(self, *args, **kwargs):
        return self.annotate_judge_task(*args, **kwargs)