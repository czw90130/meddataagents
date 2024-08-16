import builtins
import contextlib
import io
import os
import platform
import shutil
import subprocess
import sys
import traceback
import signal
import textwrap
from typing import Optional, Union, Dict, Any, Callable

from loguru import logger

try:
    import resource
except (ModuleNotFoundError, ImportError):
    resource = None

from agentscope.utils.common import create_tempdir, timer
from agentscope.service.service_status import ServiceExecStatus
from agentscope.service.service_response import ServiceResponse

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException()

def execute_python_code(
    code: str,
    timeout: Optional[Union[int, float]] = 300,
    maximum_memory_bytes: Optional[int] = None,
    local_objects: Optional[Dict[str, Any]] = None,
    return_var: Optional[str] = None
) -> ServiceResponse:
    # logger.warning(
    #     "Executing code in system environments. There exists a risk of "
    #     "unintended behavior. Please use with caution."
    # )

    output_buffer = io.StringIO()
    error_buffer = io.StringIO()

    try:
        # Fix indentation
        code = textwrap.dedent(code)

        # Store original functions
        original_functions = {
            'rmtree': shutil.rmtree,
            'rmdir': os.rmdir,
            'chdir': os.chdir
        }

        with create_tempdir():
            sys_python_guard(maximum_memory_bytes, original_functions)
            
            with contextlib.redirect_stdout(output_buffer), contextlib.redirect_stderr(error_buffer):
                if timeout and platform.system() != 'Windows':
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(int(timeout))

                try:
                    # Create a new dictionary with both globals and local_objects
                    exec_globals = dict(globals())
                    if local_objects:
                        exec_globals.update(local_objects)
                    
                    exec(code, exec_globals)
                    
                    if timeout and platform.system() != 'Windows':
                        signal.alarm(0)  # Cancel the alarm

                    # Check if the return variable exists and is not None
                    if return_var and return_var in exec_globals:
                        result = exec_globals[return_var]
                    else:
                        result = output_buffer.getvalue()

                except TimeoutException:
                    raise TimeoutException("Execution timed out.")
                except Exception as e:
                    raise RuntimeError(f"Error during code execution: {str(e)}")

        return ServiceResponse(
            status=ServiceExecStatus.SUCCESS,
            content=result,
        )

    except Exception as e:
        error_message = f"An error occurred: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        error_message += f"\n\nStandard Output:\n{output_buffer.getvalue()}"
        error_message += f"\n\nStandard Error:\n{error_buffer.getvalue()}"
        return ServiceResponse(
            status=ServiceExecStatus.ERROR,
            content=error_message,
        )
    finally:
        # Restore original functions
        shutil.rmtree = original_functions['rmtree']
        os.rmdir = original_functions['rmdir']
        os.chdir = original_functions['chdir']

def sys_python_guard(maximum_memory_bytes: Optional[int] = None, 
                     original_functions: Dict[str, Callable] = None) -> None:
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
        # "chdir",  # Don't disable this
        # "rmdir",  # Don't disable this
    ]
    for func_name in os_funcs_to_disable:
        if func_name not in original_functions:
            setattr(os, func_name, None)

    # Disable shutil functions
    shutil_funcs_to_disable = ["move", "chown"]  # Don't disable "rmtree"
    for func_name in shutil_funcs_to_disable:
        if func_name not in original_functions:
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