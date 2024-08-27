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

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agentscope.agents import AgentBase
from agentscope.message import Msg
from agentscope.exception import ResponseParsingError
from agents.tools.yaml_object_parser import MarkdownYAMLDictParser
from typing import List, Callable, Optional, Union, Sequence
import yaml
import traceback
from agentscope.service.service_status import ServiceExecStatus

from agentscope.service import (
    ServiceFactory,
    execute_shell_command,
)

from agents.tools.swe_agent_service_func import (
    exec_py_linting,
    write_file,
    read_file,
)

from agents.tools.swe_agent_prompts import (
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
    with open(file_path, "r", encoding="utf-8") as file:
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
        window_size: int = 200
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
            use_memory=True,
        )
        self.window_size = window_size
        
        self.memory_window = 6  # 记忆窗口大小
        self.max_retries = 2  # 最大重试次数
        self.running_memory: List[str] = []  # 运行时记忆
        self.cur_file: str = ""  # 当前文件
        self.cur_line: int = 0  # 当前行号
        self.cur_file_content: str = ""  # 当前文件内容

        self.main_goal = ""  # 主要目标
        self.commands_prompt = ""  # 命令提示
        self.parser = MarkdownYAMLDictParser(fix_model_config_name=model_config_name)  # YAML解析器
        
        self.commands_description_dict = {
            "exit": "exit: Executed when the current task is complete. Arguments:\n    force (bool, optional): If True, exit without linting. If False or not provided, perform linting before exit.",
            f"scroll_up": "scroll_up: Scrolls up the current open file, will scroll up and show you the {self.window_size} lines above your current lines, takes no arguments",
            f"scroll_down": "scroll_down: Scrolls down the current open file, will scroll down and show you the {self.window_size} lines below your current lines'takes no arguments",
            f"goto": "goto: This will take you directly to the line <line_num> and show you the {self.window_size} lines below it. \n       line_num (int): The line number to go to.",
        }

        # 为其他命令添加描述
        self.commands_description_dict["write_file"] = prepare_func_prompt(write_file)
        self.commands_description_dict["read_file"] = prepare_func_prompt(read_file)
        self.commands_description_dict["execute_shell_command"] = prepare_func_prompt(
            execute_shell_command,
        )
        self.commands_description_dict["exec_py_linting"] = prepare_func_prompt(
            exec_py_linting,
        )
        
        self.get_commands_prompt()  # 获取命令提示

        self.last_executed_command = None
        self.repeated_command_count = 0
        self.max_repeated_commands = 5  # 允许重复执行同一命令的最大次数

    def add_command_func(self, name: str, func: Callable, instance=None) -> None:
        if instance:
            # 如果提供了实例,创建一个绑定方法
            bound_func = func.__get__(instance, instance.__class__)
            self.commands_description_dict[name] = bound_func
        else:
            self.commands_description_dict[name] = func
        # 更新命令提示
        self.commands_prompt += f"{name}: {prepare_func_prompt(func)}\n"

    def get_current_file_content(self) -> None:
        """
        Get the current file content.
        获取当前文件的内容。
        """
        if self.cur_file == "":
            return
        start_line = self.cur_line - self.window_size//2
        if start_line < 0:
            start_line = 0
        end_line = self.cur_line + self.window_size//2
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
        system_prompt = get_system_prompt(self.commands_prompt, self.window_size)
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
            self.window_size,
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

        # 检查是否重复执行相同的命令
        if action == self.last_executed_command:
            self.repeated_command_count += 1
            if self.repeated_command_count >= self.max_repeated_commands:
                # 如果重复次数超过限制，强制执行 exit 命令
                action = {"name": "exit", "arguments": {"force": False}}
                obs = self.parse_command(action)
                return Msg(self.name, {"action": action, "observation": obs}, role="assistant"), obs
        else:
            self.repeated_command_count = 0
        
        self.last_executed_command = action
        
        obs = self.parse_command(res.parsed["action"])
        
        # 将动作和观察结果添加到运行记忆中
        self.running_memory.append(f"Action: {action}")
        self.running_memory.append(f"Observation: {obs}")
        
        self.speak(
            Msg(self.name, "\n<observation>\n" + obs + "\n</observation>", role="assistant"),
        )
        # # add msg to context windows
        # # 将消息添加到上下文窗口
        # self.running_memory.append(str(action) + str(obs))
        
        # 如果运行记忆超过了记忆窗口大小，移除最旧的条目
        while len(self.running_memory) > self.memory_window * 2:
            self.running_memory.pop(0)
        return msg_res, obs

    def reply(self, x: Optional[Union[Msg, Sequence[Msg]]] = None) -> Msg:
        """
        回复输入消息。

        参数:
        x (Optional[Union[Msg, Sequence[Msg]]]): 输入消息。

        返回:
        Msg: 最终的回复消息。
        """
        self.main_goal = x.content
        self.last_executed_command = None  # 重置最后执行的命令
        self.repeated_command_count = 0  # 重置重复计数
        while True:
            msg, obs = self.step()
            action_name = msg.content["action"]["name"]
            if action_name == "exit":
                if "<status>continue</status>" in obs:
                    continue
                else:
                    break
        return msg

    def parse_command(self, command_call: dict) -> str:
        """
        解析并执行命令。

        参数:
        command_call (dict): 包含命令名称和参数的字典。

        返回:
        str: 包含 XML 格式的命令执行结果或观察。
        """
        command_name = command_call["name"]
        command_args = command_call["arguments"]

        try:
            if command_name == "exit":
                force = command_args.get("force", False)
                if not force:
                    # 执行 linting
                    lint_result = exec_py_linting(self.cur_file)
                    if lint_result.status == ServiceExecStatus.SUCCESS:
                        if "No lint errors found." in lint_result.content or "" == lint_result.content.strip():
                            return ("<cmd_result><status>exit</status><message>Linting passed. Exiting.</message></cmd_result>")
                        else:
                            return (
                            "<cmd_result>\n"
                            "    <status>continue</status>\n"
                            "    <message>Linting failed. Please fix the following issues before exiting:</message>\n"
                            f"    <lint_output>{lint_result.content}</lint_output>\n"
                            "</cmd_result>\n"
                        )
                    else:
                        return (
                        "<cmd_result>\n"
                        "    <status>error</status>\n"
                        f"    <message>Error during linting: {lint_result.content}</message>\n"
                        "</cmd_result>\n"
                        )
                else:
                    return ("<cmd_result><status>exit</status><message>Force exit. Exiting without linting.</message></cmd_result>")

            if command_name in ["goto", "scroll_up", "scroll_down"]:
                total_lines = count_file_lines(self.cur_file)
                if command_name == "scroll_up":
                    if self.cur_line == 0:
                        return "<cmd_result><status>error</status><message>Already at the top of the file.</message></cmd_result>"
                    line = max(0, self.cur_line - self.window_size)
                    command_str = f"Scrolling up from file {self.cur_file} from line {self.cur_line} to line {line}."
                elif command_name == "scroll_down":
                    if self.cur_line >= total_lines - self.window_size:
                        return "<cmd_result><status>error</status><message>Already at the bottom of the file.</message></cmd_result>"
                    line = min(total_lines, self.cur_line + self.window_size)
                    command_str = f"Scrolling down from file {self.cur_file} from line {self.cur_line} to line {line}."
                else:  # goto
                    line = command_args["line_num"]
                    if line < 0 or line >= total_lines:
                        return f"<cmd_result><status>error</status><message>Invalid line number. File has {total_lines} lines.</message></cmd_result>"
                    command_str = f"Going to {self.cur_file} from line {self.cur_line} to line {line}."

                read_status = read_file(self.cur_file, line, line + self.window_size)
                if read_status.status == ServiceExecStatus.SUCCESS:
                    self.cur_line = line
                    return (
                        "<cmd_result>\n"
                        "    <status>success</status>\n"
                        f"    <action>{command_str}</action>\n"
                        "    <file_content>\n"
                        f"        {read_status.content}\n"
                        "    </file_content>\n"
                        "</cmd_result>\n"
                    )
                else:
                    return (
                        "<cmd_result>\n"
                        "    <status>error</status>\n"
                        f"    <message>Failed to {command_name} {self.cur_file} from {self.cur_line} to line {line}</message>\n"
                        "</cmd_result>\n"
                    )

            if command_name == "execute_shell_command":
                result = execute_shell_command(**command_args).content
                return (
                "<cmd_result>\n"
                "    <status>success</status>\n"
                "    <shell_output>\n"
                f"        {result}\n"
                "    </shell_output>\n"
                "</cmd_result>\n"
                )

            if command_name == "write_file":
                self.cur_file = command_args["file_path"]
                self.cur_line = command_args.get("start_line", 0)
                write_status = write_file(**command_args)
                return (
                "<cmd_result>\n"
                f"    <status>{'success' if write_status.status == ServiceExecStatus.SUCCESS else 'error'}</status>\n"
                f"    <message>{write_status.content}</message>\n"
                "</cmd_result>\n"
                )

            if command_name == "read_file":
                self.cur_file = command_args["file_path"]
                self.cur_line = command_args.get("start_line", 0)
                read_status = read_file(**command_args)
                return (
                "<cmd_result>\n"
                f"    <status>{'success' if read_status.status == ServiceExecStatus.SUCCESS else 'error'}</status>\n"
                "    <file_content>\n"
                f"        {read_status.content}\n"
                "    </file_content>\n"
                "</cmd_result>\n"
                )

            if command_name == "exec_py_linting":
                lint_result = exec_py_linting(**command_args).content
                return (
                "<cmd_result>\n"
                "    <status>success</status>\n"
                "    <lint_output>\n"
                f"        {lint_result}\n"
                "    </lint_output>\n"
                "</cmd_result>\n"
                )

            if command_name in self.commands_description_dict:
                func = self.commands_description_dict[command_name]
                result = func(**command_args)
                return (
                "<cmd_result>\n"
                "    <status>success</status>\n"
                "    <output>\n"
                f"        {str(result)}\n"
                "    </output>\n"
                "</cmd_result>\n"
                )

            return (
            "<cmd_result>\n"
            "    <status>error</status>\n"
            f"    <message>No such command: {command_name}</message>\n"
            "</cmd_result>\n"
            )

        except Exception as e:
            error_msg = f"Error executing command '{command_name}':\n"
            error_msg += f"Exception: {str(e)}\n"
            error_msg += "Traceback:\n"
            error_msg += traceback.format_exc()
            return (
                "<cmd_result>\n"
                "    <status>error</status>\n"
                "    <error_details>\n"
                f"        {error_msg}\n"
                "    </error_details>\n"
                "</cmd_result>\n"
            )

    def get_commands_prompt(self) -> None:
        """
        获取并设置命令提示。
        """
        self.commands_prompt = ""
        for name, desc in self.commands_description_dict.items():
            self.commands_prompt += f"{name}: {desc}\n"

if __name__ == "__main__":
    import agentscope
    from agentscope.message import Msg
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
    print("====== Agent's final response: ======")
    print(response.content)

    # 验证结果
    print("\n  the result:")
    os.system("python gcd_algorithm.py")

    # 显示生成的代码
    print("\nGenerated GCD algorithm code:")
    with open("gcd_algorithm.py", "r") as file:
        print(file.read())