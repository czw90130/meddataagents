from agentscope.agents import DialogAgent
from functools import partial
from agentscope.message import Msg

class Annotator:
    """
    注释员(Annotator)
    专业的医疗数据注释员，根据"JSON医疗注释参考"和一系列"注释要求"对"信息"进行注释。
    """
    HostMsg = partial(Msg, name="Moderator", role="assistant")
    def __init__(self):
        self.agent = DialogAgent(
            name="Annotator",
            sys_prompt=("You are a professional medical data annotator. You need to annotate a piece of \"information\" "
                        "based on a \"YAML Medical Annotation Reference\" and a series of \"annotation requirements\"."),
            model_config_name="kuafu3.5",
            use_memory=True
        )

    def annotate_task(self, tags, require, info):
        """
        注释任务提示词
        - {tags}: JSON医疗实体注释参考
        - {require}: 注释要求或优化建议
        - {info}: 待注释的信息
        """
        pre_prompt = (
            "You will receive content in the following format:\n\n"
            "# YAML Medical Annotation Reference\n"
            "```\n"
            "/* The format of the YAML reference table for medical entity annotation is: */\n"
            "/*\"{tag}\":\"{name}|{description}|{example}\"*/\n"
            "```\n\n"
            "# Annotation Requirements\n"
            "```\n"
            "/* Specific annotation requirements OR review result. */\n"
            "```\n\n"
            "# Information to be Annotated\n"
            "```\n"
            "/* If the information to be annotated already has annotation tags, it needs to be optimized "
            "or re-annotated according to the latest \"YAML Medical Annotation Reference\" and \"annotation requirements\". */\n"
            "```\n"
            "Additionally, ensure that the annotated content, excluding the tags themselves, matches the original text exactly. "
            "This includes all characters, numbers, and punctuation marks, and any spelling errors must be preserved as they are in the original text."
        )
        prompt = (
            "# YAML Reference for Medical Entity Annotation\n"
            "```\n{tags}\n```\n\n"
            "# Annotation Requirements or Optimization Suggestions\n"
            "```\n{require}\n```\n"
            "# Information to be Annotated\n"
            "```\n{info}\n```\n"
            "Return the results with annotations DIRECTLY, without any markdown or json format.\n"
        ).format(tags=tags, require=require, info=info)
        hint = self.HostMsg(content=pre_prompt+prompt)
        return self.agent(hint)

    def __call__(self, *args, **kwargs):
        return self.annotate_task(*args, **kwargs)