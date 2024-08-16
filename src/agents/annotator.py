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
            "/*\"%tag%\":\"%name%|%description%|%example%\"*/\n"
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
            "```\n1.标注的正确性：\n  确保标签对应正确,不能创造\"YAML reference for medical entity annotation\"以外的标签。\n  确保所有相关的实体类型都已使用，特别是在涉及到具体检查和诊断的地方。\n  不要对没有明确意义的名字进行标注。\n   错误标注举例：现为进一步<pro-trt>治疗</pro-trt>，... /*“治疗”并不具体*/\n   正确标注举例：现为进一步治疗，... /*该句不需要任何标签*/\n   错误标注举例：<thp-sur>术后</thp-sur>发现 ... /*“术后”并无法指代具体的治疗措施，应该去除thp-sur标签*/\n    正确标注举例：术后发现，.../*该句不需要任何标签*/\n2.嵌套结构：\n  标签不应该包含两个及以上的句子，跨句（包括逗号分割的停顿）需要分别标注。\n  注意避免嵌套错误，确保每个标签的闭合顺序正确。\n  正确标注举例：<sym-sym><bod-bdp>左眉弓上皮肤</bod-bdp>裂伤有<bod-sub>少量血液</bod-sub>流出</sym-sym>。\n  错误标注举例：<bod-bdp>左眉弓</bod-bdp>上<sym-sym>皮肤裂伤</sym-sym><bod-sub>有少量血液流出</bod-sub>。\n3.确保标注前后内文本内容完全一致。\n4.时间标注：\n  确保标注  tim明确表示绝对时间点或一个相对的时间，不应该标注没有时间点的事件。\n  错误标注举例：<tim>专科情况：</tim>... （不含时间点）\n  正确标注举例：专科情况：... （该句不需要任何标签）\n5.简写识别和分段：\n  确保简写的内容也能够被正确的标注，注意数字分段的分割。\n  正确标注举例：1 患者<pin-bas>男</pin-bas><pin-bas>53岁</pin-bas> 2<pin-pmh>既往体健</pin-pmh>3 缘于<tim>2小时前</tim>患者与人发生口角 ... ...\n  错误标注举例：1 患者男53岁2既往体健3 缘于<tim>2小时前</tim>患者与人发生口角 ... ...\n```\n"
            "# Information to be Annotated\n"
            "```\n{info}\n```\n"
            "Return the results with annotations DIRECTLY, without any markdown or json format.\n"
        ).format(tags=tags, require=require, info=info)
        hint = self.HostMsg(content=pre_prompt+prompt)
        return self.agent(hint)

    def __call__(self, *args, **kwargs):
        return self.annotate_task(*args, **kwargs)