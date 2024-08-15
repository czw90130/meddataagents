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
from yaml_object_parser import MarkdownYAMLDictParser
from typing import List, Callable, Optional, Union, Sequence
import yaml
from agentscope.service import (
    ServiceFactory,
    execute_shell_command,
)

from swe_agent_service_func import (
    exec_py_linting,
    write_file,
    read_file,
)

from swe_agent_prompts import (
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

    # 创建 SWEAgent 实例
    agent = SWEAgent("SWE-Agent", "kuafu3.5")

    # 定义 GCD 算法开发任务
    task = """
    <task>
        <description>
            Develop a Python script that implements the Euclidean algorithm to find the Greatest Common Divisor (GCD) of two numbers.
            Save this script as 'gcd_algorithm.py' in the current directory.
        </description>
        <requirements>
            1. Implement the GCD function using the Euclidean algorithm.
            2. The function should take two positive integers as input.
            3. Include proper error handling for invalid inputs (e.g., negative numbers or non-integers).
            4. Add comments to explain the algorithm and important steps.
            5. Include a main section that demonstrates the usage of the GCD function with at least two examples.
        </requirements>
        <steps>
            1. Create a new file named 'gcd_algorithm.py'
            2. Implement the GCD function using the Euclidean algorithm
            3. Add error handling and input validation
            4. Write comments to explain the code
            5. Create a main section with example usage
            6. Save the file
            7. Execute the Python script to verify it works
        </steps>
    </task>
    """

    # 创建任务消息
    task_msg = Msg("user", task, role="user")

    # 让 agent 执行任务
    response = agent.reply(task_msg)

    # 打印 agent 的最终响应
    print("Agent's final response:")
    print(response.content)

    # 验证结果
    print("\nVerifying the result:")
    os.system("python gcd_algorithm.py")

    # 显示生成的代码
    print("\nGenerated GCD algorithm code:")
    with open("gcd_algorithm.py", "r") as file:
        print(file.read())