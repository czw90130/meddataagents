# -*- coding: utf-8 -*-
# pylint: disable=C0301
"""
Tools for swe-agent, such as checking files with linting and formatting,
writing and reading files by lines, etc.
为swe-agent提供的工具函数，包括对文件进行代码质量检查和格式化、
按行读写文件等功能。
"""
import subprocess
import os

from agentscope.service.service_response import ServiceResponse
from agentscope.service.service_status import ServiceExecStatus


def exec_py_linting(file_path: str) -> ServiceResponse:
    """
    Executes flake8 linting on the given .py file with specified checks and
    returns the linting result.

    Args:
        file_path (`str`): The path to the Python file to lint.

    Returns:
        ServiceResponse: Contains either the output from the flake8 command as
        a string if successful, or an error message including the error type.
    """
    command = f"flake8 --isolated --select=F821,F822,F831,E111,E112,E113,E999,E902 {file_path}"

    try:
        # 执行flake8命令
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        # 如果执行成功，返回输出结果或"未发现代码质量问题"的消息
        return ServiceResponse(
            status=ServiceExecStatus.SUCCESS,
            content=result.stdout.strip()
            if result.stdout
            else "No lint errors found.",
        )
    except subprocess.CalledProcessError as e:  
        # 如果执行过程中出现错误，返回错误信息
        error_message = (
            e.stderr.strip()
            if e.stderr
            else "An error occurred while linting the file."
        )
        return ServiceResponse(
            status=ServiceExecStatus.ERROR,
            content=error_message,
        )
    except Exception as e:
        # 捕获其他可能的异常，并返回错误信息
        return ServiceResponse(
            status=ServiceExecStatus.ERROR,
            content=str(e),
        )


def write_file(
    file_path: str,
    content: str,
    start_line: int = 0,
    end_line: int = -1,
) -> ServiceResponse:
    """
    Write content to a file by replacing the current lines between <start_line> and <end_line> with <content>. Default start_line = 0 and end_line = -1. Calling this with no <start_line> <end_line> args will replace the whole file, so besure to use this with caution when writing to a file that already exists.

    Args:
        file_path (`str`): The path to the file to write to.
        content (`str`): The content to write to the file.
        start_line (`Optional[int]`, defaults to `0`): The start line of the file to be replace with <content>.
        end_line (`Optional[int]`, defaults to `-1`): The end line of the file to be replace with <content>. end_line = -1 means the end of the file, otherwise it should be a positive integer indicating the line number.
    """  # noqa
    try:
        # 确定文件打开模式
        mode = "w" if not os.path.exists(file_path) else "r+"
        # 将内容分割成行
        insert = content.split("\n")
        with open(file_path, mode, encoding="utf-8") as file:
            if mode != "w":
                # 如果文件已存在，读取所有行
                all_lines = file.readlines()
                # 构建新的文件内容
                new_file = [""] if start_line == 0 else all_lines[:start_line]
                new_file += [i + "\n" for i in insert]
                last_line = end_line + 1
                new_file += [""] if end_line == -1 else all_lines[last_line:]
            else:
                # 如果是新文件，直接使用插入的内容
                new_file = insert

            # 将文件指针移到开头，写入新内容，并截断文件
            file.seek(0)
            file.writelines(new_file)
            file.truncate()
            # 构建操作描述
            obs = f'WRITE OPERATION:\nYou have written to "{file_path}" \
                on these lines: {start_line}:{end_line}.'
            # 返回成功响应
            return ServiceResponse(
                status=ServiceExecStatus.SUCCESS,
                content=obs + "".join(new_file),
            )
    except Exception as e:
        # 捕获并返回任何异常
        error_message = f"{e.__class__.__name__}: {e}"
        return ServiceResponse(
            status=ServiceExecStatus.ERROR,
            content=error_message,
        )


def read_file(
    file_path: str,
    start_line: int = 0,
    end_line: int = -1,
) -> ServiceResponse:
    """
    Shows a given file's contents starting from <start_line> up to <end_line>. Default: start_line = 0, end_line = -1. By default the whole file will be read.

    Args:
        file_path (`str`): The path to the file to read.
        start_line (`Optional[int]`, defaults to `0`): The start line of the file to be read.
        end_line (`Optional[int]`, defaults to `-1`): The end line of the file to be read.
    """  # noqa
    # 确保start_line不小于0
    start_line = max(start_line, 0)
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            if end_line == -1:
                if start_line == 0:
                    # 如果start_line为0且end_line为-1，读取整个文件
                    code_view = file.read()
                else:
                    # 否则，从start_line开始读取到文件末尾
                    all_lines = file.readlines()
                    code_slice = all_lines[start_line:]
                    code_view = "".join(code_slice)
            else:
                # 如果指定了end_line，读取指定范围的行
                all_lines = file.readlines()
                num_lines = len(all_lines)
                begin = max(0, min(start_line, num_lines - 2))
                end_line = (
                    -1 if end_line > num_lines else max(begin + 1, end_line)
                )
                code_slice = all_lines[begin:end_line]
                code_view = "".join(code_slice)
        # 返回成功响应
        return ServiceResponse(
            status=ServiceExecStatus.SUCCESS,
            content=f"{code_view}",
        )
    except Exception as e:
        error_message = f"{e.__class__.__name__}: {e}"
        print("Error reading file: ")
        print(error_message)
        return ServiceResponse(
            status=ServiceExecStatus.ERROR,
            content=error_message,
        )
