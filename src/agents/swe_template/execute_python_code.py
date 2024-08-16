# -*- coding: utf-8 -*-
"""Service to execute python code."""
import builtins
import contextlib
import io
import multiprocessing
import os
import platform
import shutil
import subprocess
import sys
import traceback
from typing import Optional, Union, Dict, Any

from loguru import logger

try:
    import resource
except (ModuleNotFoundError, ImportError):
    resource = None

from agentscope.utils.common import create_tempdir, timer
from agentscope.service.service_status import ServiceExecStatus
from agentscope.service.service_response import ServiceResponse

def execute_python_code(
    code: str,
    timeout: Optional[Union[int, float]] = 300,
    maximum_memory_bytes: Optional[int] = None,
    local_objects: Optional[Dict[str, Any]] = None,
) -> ServiceResponse:
    """
    Execute a piece of python code.

    This function runs Python code provided in string format directly in the
    host system's environment.

    WARNING: This function executes code in the system environment. There
    exists a risk of unintended behavior. Use with caution, especially with
    untrusted code.

    Args:
        code (str):
            The Python code to be executed.

        timeout (Optional[Union[int, float]], defaults to 300):
            The maximum time (in seconds) allowed for the code to run. If
            the code execution time exceeds this limit, it will be
            terminated. Set to None for no time limit.

        maximum_memory_bytes (Optional[int], defaults to None):
            The memory limit in bytes for the code execution. If not
            specified, there is no memory limit imposed.

        local_objects (Optional[Dict[str, Any]], defaults to None):
            A dictionary of local objects to be made available in the
            execution environment.

    Returns:
        ServiceResponse: A ServiceResponse containing two elements:
        `output` and `error`. Both `output` and `error` are strings that
        capture the standard output and standard error of the code
        execution, respectively.

    Note:
        The argument `timeout` is not available in Windows OS, since
        `signal.setitimer` is only available in Unix.
    """
    logger.warning(
        "Executing code in system environments. There exists a risk of "
        "unintended behavior. Please use with caution."
    )

    manager = multiprocessing.Manager()
    shared_list = manager.list()

    p = multiprocessing.Process(
        target=_sys_execute,
        args=(
            code,
            shared_list,
            maximum_memory_bytes,
            timeout,
            local_objects,
        ),
    )
    p.start()
    p.join(timeout)
    if p.is_alive():
        p.terminate()
        p.join()

    if len(shared_list) == 3:
        output, error, status = shared_list
        if status:
            return ServiceResponse(
                status=ServiceExecStatus.SUCCESS,
                content=output,
            )
        else:
            return ServiceResponse(
                status=ServiceExecStatus.ERROR,
                content=f"{output}\n{error}",
            )
    else:
        return ServiceResponse(
            status=ServiceExecStatus.ERROR,
            content="Execution timed out or failed to complete.",
        )

def _sys_execute(
    code: str,
    shared_list: list,
    maximum_memory_bytes: int,
    timeout: int,
    local_objects: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Executes the given Python code in a controlled environment, capturing
    the output and errors.

    Parameters:
        code (str): The Python code to be executed.
        shared_list (ListProxy): A list proxy managed by a
            multiprocessing.Manager to which the output and error messages
            will be appended, along with a success flag.
        maximum_memory_bytes (int): The maximum amount of memory in bytes
            that the execution is allowed to use.
        timeout (int): The maximum amount of time in seconds that the code
            is allowed to run.
        local_objects (Optional[Dict[str, Any]]): A dictionary of local
            objects to be made available in the execution environment.

    Returns:
        None: This function does not return anything. It appends the results
            to the shared_list.
    """
    is_success = False
    with create_tempdir():
        # These system calls are needed when cleaning up tempdir.
        rmtree = shutil.rmtree
        rmdir = os.rmdir
        chdir = os.chdir

        sys_python_guard(maximum_memory_bytes)
        output_buffer, error_buffer = io.StringIO(), io.StringIO()
        with timer(timeout), contextlib.redirect_stdout(
            output_buffer,
        ), contextlib.redirect_stderr(error_buffer):
            try:
                # Create a new dictionary with both globals and local_objects
                exec_globals = dict(globals())
                if local_objects:
                    exec_globals.update(local_objects)
                
                exec(code, exec_globals)
                is_success = True
            except Exception:
                error_buffer.write(traceback.format_exc())

        # Needed for cleaning up.
        shutil.rmtree = rmtree
        os.rmdir = rmdir
        os.chdir = chdir
    shared_list.extend(
        [output_buffer.getvalue(), error_buffer.getvalue(), is_success],
    )

def sys_python_guard(maximum_memory_bytes: Optional[int] = None) -> None:
    """
    This disables various destructive functions and prevents the generated code
    from interfering with the test (e.g. fork bomb, killing other processes,
    removing filesystem files, etc.)

    The implementation of this function are modified from
    https://github.com/openai/human-eval/blob/master/human_eval/execution.py
    """

    if resource is not None:
        if maximum_memory_bytes is not None:
            resource.setrlimit(
                resource.RLIMIT_AS,
                (maximum_memory_bytes, maximum_memory_bytes),
            )
            resource.setrlimit(
                resource.RLIMIT_DATA,
                (maximum_memory_bytes, maximum_memory_bytes),
            )
            if not platform.uname().system == "Darwin":
                resource.setrlimit(
                    resource.RLIMIT_STACK,
                    (maximum_memory_bytes, maximum_memory_bytes),
                )

    # Disable builtins functions
    builtins_funcs_to_disable = ["exit", "quit"]
    for func_name in builtins_funcs_to_disable:
        setattr(builtins, func_name, None)

    # Disable os functions
    os.environ["OMP_NUM_THREADS"] = "1"
    os_funcs_to_disable = [
        "kill",
        "system",
        "putenv",
        "remove",
        "removedirs",
        "rmdir",
        "fchdir",
        "setuid",
        "fork",
        "forkpty",
        "killpg",
        "rename",
        "renames",
        "truncate",
        "replace",
        "unlink",
        "fchmod",
        "fchown",
        "chmod",
        "chown",
        "chroot",
        "lchflags",
        "lchmod",
        "lchown",
        "getcwd",
        "chdir",
    ]
    for func_name in os_funcs_to_disable:
        setattr(os, func_name, None)

    # Disable shutil functions
    shutil_funcs_to_disable = ["rmtree", "move", "chown"]
    for func_name in shutil_funcs_to_disable:
        setattr(shutil, func_name, None)

    # Disable subprocess functions
    subprocess_funcs_to_disable = ["Popen"]
    for func_name in subprocess_funcs_to_disable:
        setattr(subprocess, func_name, None)

    __builtins__["help"] = None

    # Disable sys modules
    sys_modules_to_disable = [
        "ipdb",
        "joblib",
        "resource",
        "psutil",
        "tkinter",
    ]
    for module_name in sys_modules_to_disable:
        sys.modules[module_name] = None
        
if __name__ == "__main__":
    result = execute_python_code(
        code="print(x + y)",
        timeout=10,
        maximum_memory_bytes=1024*1024*100,  # 100 MB
        local_objects={"x": 10, "y": 20}
    )
    print("Result:")
    print(result)