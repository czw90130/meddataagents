# -*- coding: utf-8 -*-
"""An agent class that partially implements the SWE-agent.
SWE-agent is an agent designed for solving github issues.
More details can be found in https://swe-agent.com/.

Here we partially implement and modified the SWE-agent,
try to make it work with wider range of tasks then just fixing github issues.

一个部分实现SWE-agent的代理类。
SWE-agent是一个为解决github问题而设计的代理。
更多详情可以在 https://swe-agent.com/ 找到。

这里我们部分实现并修改了SWE-agent，
尝试使其能够处理比仅仅修复github问题更广泛的任务。
"""

from agentscope.agents import AgentBase
from agentscope.message import Msg
from agentscope.exception import ResponseParsingError
from tools.yaml_object_parser import MarkdownYAMLDictParser
from typing import List, Callable, Optional, Union, Sequence
import yaml
from agentscope.service import (
    ServiceFactory,
    execute_shell_command,
)

from tools.swe_agent_service_func import (
    exec_py_linting,
    write_file,
    read_file,
)

from tools.swe_agent_prompts import (
    get_system_prompt,
    get_context_prompt,
    get_step_prompt,
)


def prepare_func_prompt(function: Callable) -> str:
    """
    准备函数的提示字符串。

    参数:
    function (Callable): 要准备提示的函数。

    返回:
    str: 格式化的函数提示字符串。
    """
    func, desc = ServiceFactory.get(function)
    func_name = desc["function"]["name"]
    func_desc = desc["function"]["description"]
    args_desc = desc["function"]["parameters"]["properties"]

    args_list = [f"{func_name}: {func_desc}"]
    for args_name, args_info in args_desc.items():
        if "type" in args_info:
            args_line = (
                f'\t{args_name} ({args_info["type"]}): '
                f'{args_info.get("description", "")}'
            )
        else:
            args_line = f'\t{args_name}: {args_info.get("description", "")}'
        args_list.append(args_line)

    func_prompt = "\n".join(args_list)
    return func_prompt

# 命令描述字典
# "exit": "exit: 当前任务完成时执行，不需要参数",
# "scroll_up": "scroll_up: 向上滚动当前打开的文件，将显示当前行以上的100行，不需要参数",
# "scroll_down": "scroll_down: 向下滚动当前打开的文件，将显示当前行以下的100行，不需要参数",
# "goto": "goto: 直接跳转到指定行号<line_num>并显示其下方的100行。\n       line_num (int): 要跳转到的行号。",
COMMANDS_DISCRIPTION_DICT = {
    "exit": "exit: Executed when the current task is complete, takes no arguments",  # noqa
    "scroll_up": "scroll_up: Scrolls up the current open file, will scroll up and show you the 100 lines above your current lines, takes no arguments",  # noqa
    "scroll_down": "scroll_down: Scrolls down the current open file, will scroll down and show you the 100 lines below your current lines'takes no arguments",  # noqa
    "goto": "goto: This will take you directly to the line <line_num> and show you the 100 lines below it. \n       line_num (int): The line number to go to.",  # noqa
}

# 为其他命令添加描述
COMMANDS_DISCRIPTION_DICT["write_file"] = prepare_func_prompt(write_file)
COMMANDS_DISCRIPTION_DICT["read_file"] = prepare_func_prompt(read_file)
COMMANDS_DISCRIPTION_DICT["execute_shell_command"] = prepare_func_prompt(
    execute_shell_command,
)
COMMANDS_DISCRIPTION_DICT["exec_py_linting"] = prepare_func_prompt(
    exec_py_linting,
)

# 错误信息提示模板
ERROR_INFO_PROMPT = """
<error_report>
  <description>
    Your response is not a YAML object, and cannot be parsed by `yaml.safe_load` in parse function:
  </description>
  <your_response>
    [YOUR RESPONSE BEGIN]
    {response}
    [YOUR RESPONSE END]
  </your_response>
  <error_details>
    {error_info}
  </error_details>
  <instruction>
    Analyze the reason, and re-correct your response in the correct format.
  </instruction>
</error_report>
"""  # pylint: disable=all  # noqa


def count_file_lines(file_path: str) -> int:
    """
    计算文件的行数。

    参数:
    file_path (str): 文件路径。

    返回:
    int: 文件的总行数。
    """
    with open(file_path, "r") as file:
        lines = file.readlines()
    return len(lines)


class SWEAgent(AgentBase):
    """
    The SWE-agent
    SWE-agent类，继承自AgentBase。
    """

    def __init__(
        self,
        name: str,
        model_config_name: str,
    ) -> None:
        """
        初始化SWEAgent。

        参数:
        name (str): 代理的名称。
        model_config_name (str): 模型配置的名称。
        """
        super().__init__(
            name=name,
            model_config_name=model_config_name,
        )

        self.memory_window = 6  # 记忆窗口大小
        self.max_retries = 2  # 最大重试次数
        self.running_memory: List[str] = []  # 运行时记忆
        self.cur_file: str = ""  # 当前文件
        self.cur_line: int = 0  # 当前行号
        self.cur_file_content: str = ""  # 当前文件内容

        self.main_goal = ""  # 主要目标
        self.commands_prompt = ""  # 命令提示
        self.parser = MarkdownYAMLDictParser()  # YAML解析器
        self.get_commands_prompt()  # 获取命令提示

    def get_current_file_content(self) -> None:
        """
        Get the current file content.
        获取当前文件的内容。
        """
        if self.cur_file == "":
            return
        start_line = self.cur_line - 50
        if start_line < 0:
            start_line = 0
        end_line = self.cur_line + 50
        if end_line > count_file_lines(self.cur_file):
            end_line = -1
        read_res = read_file(self.cur_file, start_line, end_line)
        self.cur_file_content = read_res.content

    def step(self) -> Msg:
        """
        Step the SWE-agent.
        执行SWE-agent的一个步骤。

        返回:
        Msg: 包含代理响应的消息对象。
        """
        message_list = []

        # construct system prompt
        # 构造系统提示
        system_prompt = get_system_prompt(self.commands_prompt)
        message_list.append(Msg("user", system_prompt, role="system"))

        # construct context prompt, i.e. previous actions
        # 构造上下文提示，即之前的操作
        context_prompt = get_context_prompt(
            self.running_memory,
            self.memory_window,
        )
        message_list.append(Msg("user", context_prompt, role="user"))

        # construct step prompt for this instance
        # 构造此实例的步骤提示
        self.get_current_file_content()
        step_prompt = get_step_prompt(
            self.main_goal,
            self.cur_file,
            self.cur_line,
            self.cur_file_content,
        )
        message_list.append(Msg("user", step_prompt, role="user"))

        # get response from agent
         # 从代理获取响应
        try:
            in_prompt = self.model.format(message_list)
            res = self.model(
                in_prompt,
                parse_func=self.parser.parse,
                max_retries=1,
            )

        except ResponseParsingError as e:
            response_msg = Msg(self.name, e.raw_response, "assistant")
            self.speak(response_msg)

            # Re-correct by model itself
            # 模型自我纠正
            error_msg = Msg(
                name="system",
                content={
                    "action": {"name": "error"},
                    "error_msg": ERROR_INFO_PROMPT.format(
                        parse_func=self.parser.parse,
                        error_info=e.message,
                        response=e.raw_response,
                    ),
                },
                role="system",
            )
            self.speak(error_msg)
            # continue 继续
            self.running_memory.append(error_msg)
            return error_msg

        msg_res = Msg(self.name, res.parsed, role="assistant")

        self.speak(
            Msg(self.name, yaml.dump(res.parsed, indent=2), role="assistant"),
        )

        # parse and execute action
        # 解析并执行动作
        action = res.parsed.get("action")

        obs = self.prase_command(res.parsed["action"])
        self.speak(
            Msg(self.name, "\n====Observation====\n" + obs, role="assistant"),
        )

        # add msg to context windows
        # 将消息添加到上下文窗口
        self.running_memory.append(str(action) + str(obs))
        return msg_res

    def reply(self, x: Optional[Union[Msg, Sequence[Msg]]] = None) -> Msg:
        """
        回复输入消息。

        参数:
        x (Optional[Union[Msg, Sequence[Msg]]]): 输入消息。

        返回:
        Msg: 最终的回复消息。
        """
        action_name = None
        self.main_goal = x.content
        while not action_name == "exit":
            msg = self.step()
            action_name = msg.content["action"]["name"]
        return msg

    def prase_command(self, command_call: dict) -> str:
        """
        解析并执行命令。

        参数:
        command_call (dict): 包含命令名称和参数的字典。

        返回:
        str: 命令执行的结果或观察。
        """
        command_name = command_call["name"]
        command_args = command_call["arguments"]
        if command_name == "exit":
            return "Current task finished, exitting."
        if command_name in ["goto", "scroll_up", "scroll_down"]:
            if command_name == "goto":
                line = command_call["arguments"]["line_num"]
                command_str = f"Going to {self.cur_file} line \
                    {command_args['line_mum']}."
                command_failed_str = f"Failed to go to {self.cur_file} \
                    line {command_args['line_num']}"
            if command_name == "scroll_up":
                line = self.cur_line - 100
                if line < 0:
                    line = 0
                command_str = (
                    f"Scrolling up from file {self.cur_file} to line {line}."
                )
                command_failed_str = (
                    f"Failed to scroll up {self.cur_file} to line {line}"
                )
            if command_name == "scroll_down":
                line = self.cur_line + 100
                if line > count_file_lines(self.cur_file):
                    line = count_file_lines(self.cur_file)
                command_str = (
                    f"Scrolling down from file {self.cur_file} to line {line}."
                )
                command_failed_str = (
                    f"Failed to scrool down {self.cur_file} to line {line}"
                )
            read_status = read_file(self.cur_file, line, line + 100)
            if read_status.status == "success":
                self.cur_line = line
                obs = read_status.content
                return f"{command_str}. Observe file content: {obs}"
            else:
                return command_failed_str
        if command_name == "execute_shell_command":
            return execute_shell_command(**command_args).content
        if command_name == "write_file":
            self.cur_file = command_args["file_path"]
            self.cur_line = command_args.get("start_line", 0)
            write_status = write_file(**command_args)
            return write_status.content
        if command_name == "read_file":
            self.cur_file = command_args["file_path"]
            self.cur_line = command_args.get("start_line", 0)
            read_status = read_file(**command_args)
            return read_status.content
        if command_name == "exec_py_linting":
            return exec_py_linting(**command_args).content
        return "No such command"

    def get_commands_prompt(self) -> None:
        """
        获取并设置命令提示。
        """
        for name, desc in COMMANDS_DISCRIPTION_DICT.items():
            self.commands_prompt += f"{name}: {desc}\n"

if __name__ == "__main__":
    import os
    import sys
    import agentscope
    from agentscope.message import Msg
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from goodrock_model_wrapper import GoodRockModelWrapper
    
    agentscope.init(
        model_configs="../configs/model_configs.json"
    )
    
    from tools.execute_python_code import execute_python_code
    from annotator import Annotator
    
    code_str = """
# Test content
# Perform annotation
# result = annotator.annotate_task(yaml_tags, test_info)
with open("../.gitignore", "r") as f:
    result = f.read()
"""

    # YAML format of the tags
    yaml_tags = """
tim: "Time|记录患者病程中的关键时间点|患者缘于<tim>1周前</tim><sym-sym>无明显诱因，出现腹痛伴腹胀，以<bod-bdp>上腹部</bod-bdp>为主</sym-sym>。"
dis-dis: "Disease|具体的疾病或综合征，如糖尿病、阿尔茨海默病等|初步诊断为：1.<dis-dis>脑梗死</dis-dis>2.<dis-pos>脑出血后遗症</dis-pos>3.<dis-dis>高血压病2级很高危组</dis-dis>4.<dis-dis>陈旧性脑梗死</dis-dis>5.<dis-dis>慢性阻塞性肺疾病</dis-dis><dis-dis>肺大泡</dis-dis>。"
dis-inj: "Injury|由于外界因素导致的中毒或身体损伤，如食物中毒、骨折等|<tim>昨日</tim>患者工作时不慎从3米高的梯子上摔下，致<dis-inj>左小腿开放性骨折</dis-inj>伴<sym-sig>大量出血</sym-sig>。"
dis-dam: "Damage|器官或细胞的损伤，如肝损伤、神经损伤等|该患者<tim>2年前</tim>因<dis-dam>肝损伤</dis-dam>在<ins-hos>省人民医院</ins-hos>行<thp-sur><bod-bdp>肝左外叶</bod-bdp>切除术</thp-sur>。"
dis-pos: "Post-treatment Status|描述手术后或其他治疗后的疾病状态，如直肠癌术后、化疗后状态等|患者<dis-pos>甲状腺癌术后</dis-pos><thp-fup>定期随访</thp-fup>。"
sym-sym: "Symptom|患者主观感受到的不适或异常，如头痛、恶心等|患者自发病以来，<sym-sym>精神可</sym-sym>，<sym-sym>饮食差</sym-sym>，<sym-sym>睡眠可</sym-sym>，<sym-sym><bod-sub>尿</bod-sub>量正常</sym-sym>，<sym-sym>偶排<bod-sub>稀便</bod-sub></sym-sym>。"
sym-sig: "Sign|体征，医生通过检查发现的客观异常，如高血压、黄疸等|体检发现<sym-sig><bod-bdp>双下肢</bod-bdp>轻度水肿</sym-sig>，<ite-phy>血压160/100mmHg</ite-phy>。"
ite-phy: "Physical|体格检查，对患者身体进行的全面检查，如身高体重测量等|体格检查：<ite-phy>T37.2℃</ite-phy>，<ite-phy>P82次/分</ite-phy>，<ite-phy>R18次/分</ite-phy>，<ite-phy>BP120/80mmHg</<ite-phy>。"
ite-lab: "Laboratory|在实验室进行的各种检查，如血液、尿液等|血常规检查示<ite-lab>中性粒细胞比例0.85</ite-lab>，<ite-lab>血红蛋白120g/L</ite-lab>。<ite-lab>酮体-</ite-lab>，<ite-lab>潜血-</ite-lab>，<ite-lab>尿蛋白-</ite-lab>，<ite-lab>白细胞1+</ite-lab>，<ite-lab>尿糖-</ite-lab>。"
ite-img: "Imaging|使用影像技术进行的检查，如X射线、CT、MRI等|患者<tim>10月余前</tim>因<dis-dis>双肾结石</dis-dis><tim>8月余</tim>，<dis-pos><thp-sur><bod-bdp>左肾</bod-bdp>造瘘术</thp-sur>后<tim>25天</tim></dis-pos>就诊于<ins-hos>*****医院</ins-hos>，<ite-img>KUB示<dis-dis>右肾多发结石</dis-dis></ite-img>。"
ite-end: "Endoscopy|使用内窥镜进行的检查，如胃镜、肠镜等|患者<sym-sym>进食后出现<bod-bdp>上腹</bod-bdp>不适</sym-sym>，<ite-end>胃镜检查发现<dis-dis>慢性胃炎</dis-dis></ite-end>。"
ite-fnc: "Functional|评估器官或系统功能的检查，如心电图检查等|<ite-fnc>肺功能检查提示<dis-dis>阻塞性通气功能障碍</dis-dis></ite-fnc>，<ite-fnc>FEV1/FVC为65%</ite-fnc>。"
ite-pat: "Pathology|通过组织或细胞样本进行的显微镜检查，如活检等|<ite-pat>肠镜活检病理示<dis-dis>溃疡性结肠炎</dis-dis></ite-pat>，炎症较前减轻。"
ite-gen: "Genetic|检测遗传信息和分子特征的检查，如基因检测、PCR等|患儿<pin-bas>2岁</pin-bas>，<ite-gen>染色体核型分析示21三体综合征</ite-gen>。"
bod-sub: "Substance|身体中的物质，如血液、尿液等|患者于<tim>3天前</tim>无明显诱因出现<sym-sym>咳嗽，咳<bod-sub>白色粘痰</bod-sub></sym-sym>，<sym-sym>伴发热，最高体温38.5℃</sym-sym>。"
bod-bdp: "Body part|疾病、症状和体征发生的人体解剖学部位，如心脏、肝脏、皮肤、黏膜、双下肢等|体格检查：<sym-sig><bod-bdp>双肺</bod-bdp>呼吸音粗，<bod-bdp>右下肺</bod-bdp>可闻及湿啰音</sym-sig>。"
ins-dep: "Department|医疗机构中的具体科室，如内科、外科等|建议患者<thp-fup><tim>明日</tim>至<ins-dep>心内科</ins-dep>门诊复诊</thp-fup>。"
ins-hos: "Hospital|提供综合医疗服务的机构|患者<tim>1周前</tim>因<dis-dis>急性阑尾炎</dis-dis>于<ins-hos>武警总医院</ins-hos>行<thp-sur>阑尾切除术</thp-sur>。"
ins-cli: "Clinic|提供门诊医疗服务的机构|<tim>2022年8月15日</tim>患者于<ins-cli>滨海新区xx诊所</ins-cli>就诊，<ite-lab>血常规示白细胞计数15.0*10^9/L</ite-lab>。"
ins-hom: "Home|患者的家庭或居住地|患儿父母述患儿于<ins-hom>家中</ins-hom>不慎<dis-inj>被开水烫伤</dis-inj>，<sym-sig>伤处出现大片水疱</sym-sig>。"
ins-myi: "My Institution|指代当前的医疗机构或部门|患者<tim>2小时前</tim>呼吸急促，意识不清，由家属拨打<ins-ems>120</ins-ems>送至<ins-myi>我院</ins-myi><ins-dep>急诊科</ins-dep>，... ，后转入<ins-myi>我科</ins-myi>"
ins-ems: "Emergency Services|提供紧急医疗服务或救助的机构，如120，999等|患者于<tim>凌晨2点</tim>突发<sym-sym>胸痛、大汗淋漓</sym-sym>，家属即拨打<ins-ems>急救电话</ins-ems>。"
ins-oth: "Other Institutions|包括非医疗社会机构、政府机构等，如养老院等|<tim>1个月前</tim>患者因生活不能自理转入<ins-oth>松江区敬老院</ins-oth>。"
pin-bas: "Basic Info|包括年龄、性别、身高、体重等|患者，<pin-bas>男</pin-bas>，<pin-bas>68岁</pin-bas>，<pin-bas>汉族</pin-bas>，<pin-bas>已婚</pin-bas>，<pin-ohs>退休工人</pin-ohs>。"
pin-lst: "Lifestyle|包括吸烟史、饮酒史及其他生活习惯等|<pin-lst>吸烟30年，平均1包/日</pin-lst>，<pin-lst>饮酒20年，平均100g/日</pin-lst>。"
pin-pmh: "Past Medical History|患者的既往病史，如糖尿病史等|患者<pin-pmh>既往有<dis-dis>高血压病</dis-dis>史<tim>10余年</tim></pin-pmh>，<ite-phy>血压最高达180/100mmHg</ite-phy>。"
pin-fmh: "Family Medical History|患者的家族病史|患者<pin-fmh>父亲<dis-dis>肝癌</dis-dis>去世</pin-fmh>，<pin-fmh>母亲有<dis-dis>2型糖尿病</dis-dis>史</pin-fmh>。"
pin-ohs: "Occupational History|患者的职业及职业病史|患者<pin-ohs>矿工，接触粉尘<tim>20余年</tim></pin-ohs>。"
pin-alh: "Allergy History|患者的过敏史|患者<pin-alh>青霉素过敏史</pin-alh>，<sym-sym>用药后出现皮疹、呼吸困难</sym-sym>。"
thp-sur: "Surgery|通过手术手段进行的治疗|患者于<tim>上周</tim>在<ins-myi>本院</ins-myi>行<thp-sur><bod-bdp>甲状腺</bod-bdp>全切术</thp-sur>。"
thp-mdt: "Medication Therapy|使用药物进行的治疗，包括放疗、化疗、免疫治疗和基因治疗等|给予<thp-mdt>阿司匹林抗血小板聚集</thp-mdt>、<thp-mdt>阿托伐他汀抗动脉粥样硬化</thp-mdt>、<thp-mdt>硝苯地平缓释片降压</thp-mdt>等药物治疗，患者病情明显好转。"
thp-rpt: "Rehabilitation & Physical Therapy|帮助患者恢复功能的治疗，包括康复治疗和物理治疗等|<dis-pos>股骨颈骨折内固定术后</dis-pos>，嘱患者<thp-rpt>卧床休息，定期行下肢关节功能锻炼</thp-rpt>。"
thp-prc: "Prevention|预防疾病或并发症的程序，如疫苗接种、健康宣教等|嘱患者<thp-prc>戒烟</thp-prc>，建议<thp-prc>接种流感疫苗</thp-prc>。"
thp-fup: "Follow-up & Regular Activities|包括定期随访、定期治疗、定期检查等活动等|嘱患者<thp-fup>2周后门诊复查<ite-lab>甲功五项</ite-lab></thp-fup>，<thp-fup>必要时调整药物剂量</thp-fup>。"
"""

    test_info = """1.患者老年女性，88岁；2.既往体健，否认药物过敏史。3.患者缘于5小时前不慎摔伤，伤及右髋部。伤后患者自感伤处疼痛，呼我院120接来我院，查左髋部X光片示：左侧粗隆间骨折。给予补液等对症治疗。患者病情平稳，以左侧粗隆间骨折介绍入院。患者自入院以来，无发热，无头晕头痛，无恶心呕吐，无胸闷心悸，饮食可，小便正常，未排大便。4.查体：T36.1C，P87次/分，R18次/分，BP150/93mmHg,心肺查体未见明显异常，专科情况：右下肢短缩畸形约2cm，右髋部外旋内收畸形，右髋部压痛明显，叩击痛阳性,右髋关节活动受限。右足背动脉波动好，足趾感觉运动正常。5.辅助检查：本院右髋关节正位片：右侧股骨粗隆间骨折。"""

    # Initialize the Annotator
    annotator = Annotator()
    
    result = execute_python_code(
        code=code_str,
        timeout=60,
        maximum_memory_bytes=1024*1024*100,  # 100 MB
        local_objects={"annotator": annotator, "yaml_tags": yaml_tags, "test_info": test_info},
        return_var="result"
    )
    print("Result:")
    print(result)
    

    # # 创建 SWEAgent 实例
    # agent = SWEAgent("SWE-Agent", "kuafu3.5")

    # # 定义 GCD 算法开发任务
    # task = """
    # <task>
    #     <description>
    #         Develop a Python script that implements the Euclidean algorithm to find the Greatest Common Divisor (GCD) of two numbers.
    #         Save this script as 'gcd_algorithm.py' in the current directory.
    #     </description>
    #     <requirements>
    #         1. Implement the GCD function using the Euclidean algorithm.
    #         2. The function should take two positive integers as input.
    #         3. Include proper error handling for invalid inputs (e.g., negative numbers or non-integers).
    #         4. Add comments to explain the algorithm and important steps.
    #         5. Include a main section that demonstrates the usage of the GCD function with at least two examples.
    #     </requirements>
    #     <steps>
    #         1. Create a new file named 'gcd_algorithm.py'
    #         2. Implement the GCD function using the Euclidean algorithm
    #         3. Add error handling and input validation
    #         4. Write comments to explain the code
    #         5. Create a main section with example usage
    #         6. Save the file
    #         7. Execute the Python script to verify it works
    #     </steps>
    # </task>
    # """

    # # 创建任务消息
    # task_msg = Msg("user", task, role="user")

    # # 让 agent 执行任务
    # response = agent.reply(task_msg)

    # # 打印 agent 的最终响应
    # print("Agent's final response:")
    # print(response.content)

    # # 验证结果
    # print("\nVerifying the result:")
    # os.system("python gcd_algorithm.py")

    # # 显示生成的代码
    # print("\nGenerated GCD algorithm code:")
    # with open("gcd_algorithm.py", "r") as file:
    #     print(file.read())