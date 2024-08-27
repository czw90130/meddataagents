# -*- coding: utf-8 -*-
# pylint: disable=C0301
"""The SWE-agent relay heavily on it's prompts.
This file contains the neccessary prompts for the SWE-agent.
Some prompts are taken and modified from the original SWE-agent repo
or the SWE-agent implementation from Open-Devin.
这个文件包含了SWE-agent所需的必要提示。
一些提示来自原始SWE-agent仓库或Open-Devin的SWE-agent实现,并进行了修改。
SWE-agent非常依赖于这些提示来完成任务。
"""

def get_system_prompt(command_prompt: str, window_size: int) -> str:
    """
    获取SWE-agent的系统提示。
    Get the system prompt for SWE-agent.
    
    参数:
    command_prompt (str): 包含可用命令的提示字符串
    
    返回:
    str: 完整的系统提示字符串
    """
    
    return f"""
<system_prompt>
<role_definition>
You are an autonomous coding agent designed to perform various programming tasks.
You have access to a variety of tools and commands to solve problems efficiently.
</role_definition>

<environment_description>
You're working in a command line interface with a file editor that shows {window_size} lines at a time.
</environment_description>

<available_commands>
{command_prompt}
</available_commands>

<important_notes>
- Ensure proper indentation when using the WRITE command.
- Submit commands one at a time.
- You can use standard bash commands in addition to the special commands listed.
- Do not use interactive session commands (e.g., vim, python).
- Generate complete and executable code without abbreviations or omissions.
- Avoid excessive editing and know when to consider a task complete.
</important_notes>

{RESPONSE_FORMAT_PROMPT}
</system_prompt>
"""  # noqa

# 定义响应格式提示,指导agent如何格式化输出
RESPONSE_FORMAT_PROMPT = """
<response_format>
<instruction>
Respond with a YAML object in the following format:
</instruction>
<example>
<yaml>
thought: >
  Your thought process here.
action:
  name: command_name
  arguments:
    arg1: value1
    arg2: |
      Multi-line
      value here
</yaml>
</example>
<important_note>
OUTPUT ONLY THE YAML FORMAT. Ensure your response is a valid YAML string.
</important_note>
</response_format>
"""  # noqa


def get_step_prompt(
    task: str,
    file: str,
    line: int,
    current_file_content: str,
    window_size: int
) -> str:
    """
    获取SWE-agent的每一步提示。
    Get the step prompt for SWE-agent.
    
    参数:
    task (str): 当前任务描述
    file (str): 当前打开的文件名
    line (int): 当前所在行号
    current_file_content (str): 当前文件内容
    
    返回:
    str: 完整的步骤提示字符串
    """
    
    return f"""
<step_prompt>
    <task_description>
    Current task: {task}
    </task_description>

    <current_state>
    <open_file>
        File: {file}
        Line: {line}
    </open_file>
    <file_content>
        {current_file_content}
    </file_content>
    </current_state>

    <navigation_commands>
    scroll_up, scroll_down, goto %line%
    </navigation_commands>

    <instructions>
    - If a command fails, try a different one.
    - Use 'goto' for quick navigation to specific lines.
    - Check the current file and working directory before actions.
    - Verify code after editing for correct line numbers and indentation.
    - Use 'exec_py_linting' to check for errors in Python files.
    - Ensure generated or modified code is complete and executable.
    - Avoid excessive editing; know when to consider a task complete.
    - Avoid repeating the same command multiple times in a row.
    - If you find yourself stuck, try a different approach or consider completing the task.
    </instructions>

    <important_note>
    This environment does not support interactive session commands (e.g., vim, python).
    Use 'exec_py_linting' to check Python file validity.
    </important_note>
</step_prompt>
"""  # noqa


def get_context_prompt(memory: list, window: int) -> str:
    """
    获取给定记忆和窗口大小的上下文提示。
    Get the context prompt for the given memory and window.
    
    参数:
    memory (list): 包含之前操作记忆的列表
    window (int): 要显示的记忆窗口大小
    
    返回:
    str: 格式化的上下文提示字符串
    """

    res = f"<previous_actions>\n"
    res += f"<description>Your past {window} actions:</description>\n"
    for idx, mem in enumerate(memory[-window:]):
        res += f"<memory id='{idx}'>\n{mem}\n</memory>\n"
    res += "</previous_actions>\n"
    res += "<instruction>Use these memories for context. Remember, you've already completed these steps.</instruction>"
    return res