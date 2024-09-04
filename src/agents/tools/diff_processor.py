# -*- coding: utf-8 -*-
import os
import sys
import difflib
from collections import deque
from agentscope.agents import DictDialogAgent
from agentscope.message import Msg
from functools import partial
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from agents.tools.yaml_object_parser import MarkdownYAMLDictParser

class DiffDecision:
    """
    差异决策类
    负责决定是否接受文本差异的变更。
    """
    HostMsg = partial(Msg, name="Moderator", role="assistant")

    def __init__(self):
        self.agent = DictDialogAgent(
            name="DiffDecision",
            sys_prompt=("You are an AI assistant specialized in handling text differences. "
                        "Your primary task is to ensure that modifications align with the intended changes. "
                        "You should be cautious about rejecting changes and only do so when absolutely necessary. "
                        "Your goal is to maintain text quality and consistency while respecting the proposed modifications."),
            model_config_name="kuafu3.5",
            use_memory=True
        )

        self.parser = MarkdownYAMLDictParser(
            {
                "decision": "String. Possible values are 'y' (accept), 'n' (reject), or 's' (subdivide).",
                "reason": "String. One-sentence concise rationale. Include 'preservation-comments' content if relevant."
            }
        )
        self.agent.set_parser(self.parser)

    def make_decision(self, history):
        """
        根据历史记录做出决策。

        :param history: 完整的历史记录
        :return: 元组 (用户选择, 选择原因)
        """
        prompt = (
            "<key_points>\n"
            "1. Ensure modifications align with intended changes\n"
            "2. Be cautious about rejecting changes, but prioritize preserving important existing code\n"
            "3. Review proposed text changes carefully\n"
            "4. Consider impact on overall text quality and consistency\n"
            "5. Decide: Accept (y), Reject (n), or Subdivide (s)\n"
            "6. Provide brief rationale for decision\n"
            "7. Be cautious with 'replace' changes preserving original content\n"
            "8. Handle preservation-comments carefully:\n"
            "   - Identify common preservation-comments (e.g., '# ...', '# ... 现有代码 ...', '# ... keep XXX unchanged ...', '# ... existing code ...', '# ... 实现XXX的逻辑 ...')\n"
            "   - For insertions/replacements with preservation-comments:\n"
            "     * Use Subdivide multiple times to analyze complex changes\n"
            "     * If it's a single-line preservation-comment, reject the insertion\n"
            "     * If it contains a preservation-comment, use Subdivide to isolate it\n"
            "     * If it's a genuine change, consider accepting or rejecting based on its merit\n"
            "   - Maintain original content indicated by preservation-comments\n"
            "   - Note that single-line deletions or insertions cannot be further subdivided\n"
            "9. Use Subdivide for complex changes, but note single-line changes can't be subdivided\n"
            "10. Acceptance guidelines:\n"
            "    - Accept changes unless they clearly violate preservation-comments\n"
            "    - For DELETE operations, carefully evaluate the impact but lean towards accepting unless they clearly violate preservation-comments.\n"
            "    - Accept changes to non-preservation-comments, including any documentation and comments.\n"
            "    - For a insertion with preservation-comments, subdividing to reject them separately.\n"
            "</key_points>\n"
            
            "<decision_chain>\n"
            f"{history}\n"
            "</decision_chain>\n"
            
            "<instructions>\n"
            "Make your decision based on the above key points.\n"
            "Prioritize preserving important existing code, especially those marked by preservation-comments.\n"
            "If you encounter a insertion with preservation-comments, consider subdividing to reject them separately.\n"
            "Be cautious about accepting DELETE operations, and carefully evaluate all changes.\n"
            "Use subdivide for complex changes or when dealing with preservation-comments.\n"
            "</instructions>\n"
        )
        
        hint = self.HostMsg(content=prompt)
        response = self.agent(hint)
        
        return response.content['decision'], response.content['reason']

class DiffProcessor:
    """
    处理文本差异的类。
    
    这个类用于比较两个文本内容，识别它们之间的差异，并允许用户交互式地决定是否接受这些变更。
    """

    CHOICE_EXPLANATION = {'y': 'accept', 'n': 'reject', 's': 'subdivide'}

    def __init__(self, decision_func=None, history_maxlen=7, context_lines=5, only_process_replace=True):
        """
        初始化 DiffProcessor 实例。

        :param decision_func: 用于决定是否接受变更的函数，默认为 manual_decision
        :param history_maxlen: 历史记录队列的最大长度
        :param context_lines: 显示变更上下文的行数
        :param only_process_replace: 是否只处理 replace 类型的变更，默认为 False
        """
        self.decision_func = decision_func or self.manual_decision
        self.history_queue = deque(maxlen=history_maxlen)
        self.subdivide_depth = 0  # 细分深度，用于跟踪递归细分的层级
        self.context_lines = context_lines
        self.next_change_start = None  # 下一个变更的起始位置
        self.only_process_replace = only_process_replace

    def update_history(self, new_record):
        """
        更新历史记录队列。

        :param new_record: 新的历史记录
        """
        self.history_queue.append(new_record)

    def get_full_history(self):
        """
        获取完整的历史记录。

        :return: 包含完整历史记录的字符串
        """
        return '\n'.join(self.history_queue)

    def manual_decision(self, history):
        """
        手动决定是否接受变更。

        :param history: 完整的历史记录
        :return: 元组 (用户选择, 选择原因)
        """
        while True:
            choice = input(f"\n接受这个更改吗？(y/n/s 细分/h 打印历史记录): ").lower().strip()
            if choice == 'h':
                print("\n========== 历史记录 ==========")
                print(history)
                print("====== 历史记录打印结束 ======\n")
            elif choice in ['y', 'n', 's']:
                return choice, "Manual confirmation"
            else:
                print("无效的选择，请重新输入。")

    def split_diff(self, original, modified):
        """
        使用difflib比较原始和修改后的内容,生成差异信息

        :param original: 原始文本内容
        :param modified: 修改后的文本内容
        :return: 生成器，产生差异信息字典
        """
        s = difflib.SequenceMatcher(None, original, modified)
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            if tag == 'equal':
                yield {'type': 'equal', 'content': original[i1:i2], 'start_original': i1, 'end_original': i2, 'start_modified': j1, 'end_modified': j2}
            elif tag == 'delete':
                yield {'type': 'delete', 'content': original[i1:i2], 'start_original': i1, 'end_original': i2, 'start_modified': j1, 'end_modified': j1}
            elif tag == 'insert':
                yield {'type': 'insert', 'content': modified[j1:j2], 'start_original': i1, 'end_original': i1, 'start_modified': j1, 'end_modified': j2}
            elif tag == 'replace':
                yield {'type': 'replace', 'content_original': original[i1:i2], 'content_modified': modified[j1:j2], 
                       'start_original': i1, 'end_original': i2, 'start_modified': j1, 'end_modified': j2}

    def get_context(self, lines, start, end):
        """
        获取指定范围的上下文行。

        :param lines: 文本行列表
        :param start: 起始行号
        :param end: 结束行号
        :return: 包含上下文的文本行列表
        """
        context_start = max(0, start - self.context_lines)
        context_end = min(len(lines), end + self.context_lines)
        if self.next_change_start is not None:
            context_end = min(context_end, self.next_change_start)
        return lines[context_start:context_end]

    def print_line_with_number(self, line, line_number, prefix=' '):
        """
        打印带行号的行,同时记录到历史

        :param line: 文本行
        :param line_number: 行号
        :param prefix: 行前缀
        :return: 带行号的文本行
        """
        return f"{prefix}{line_number:4d}|{line.rstrip()}\n"
    
    def process_change(self, change_type, content, start_line, end_line, lines_original, lines_modified, master_tag=None):
        """
        处理单个变更。

        :param change_type: 变更类型（'insert' 或 'delete'）
        :param content: 变更的内容
        :param start_line: 变更的起始行
        :param end_line: 变更的结束行
        :param lines_original: 原始文本行列表
        :param lines_modified: 修改后的文本行列表
        :param master_tag: 主标签，用于细分时的标记
        :return: 元组 (是否接受变更, 更新后的原始行列表, 更新后的修改行列表)
        """
        history_record = ""
        
        if master_tag is not None:
            history_record += f"<{master_tag}>\n  <{change_type.upper()}>\n"
        else:
            history_record += f"<{change_type.upper()}>\n"
        
        if change_type == 'insert':
            context_lines = self.get_context(lines_modified, start_line, end_line)
        else:  # delete
            context_lines = self.get_context(lines_original, start_line, end_line)
        
        context_start = max(0, start_line - self.context_lines)
        for i, line in enumerate(context_lines, start=context_start):
            prefix = '+' if change_type == 'insert' and start_line <= i < end_line else \
                     '-' if change_type == 'delete' and start_line <= i < end_line else ' '
            line_output = self.print_line_with_number(line, i, prefix)
            history_record += line_output
        
        if master_tag is not None:
            history_record += f"  </{change_type.upper()}>\n</{master_tag}>\n"
        else:
            history_record += f"</{change_type.upper()}>\n"
        
        print(history_record, end='')
        self.update_history(history_record)
        
        choice, reason = self.decision_func(self.get_full_history())
        decision_record = f"<DECISION>\n  <CHOICE>{self.CHOICE_EXPLANATION.get(choice, 'unknown')}</CHOICE>\n  <REASON>\n{reason}</REASON>\n</DECISION>\n"
        
        print(decision_record, end='')
        self.update_history(decision_record)
        
        if choice == 'y':
            if change_type == 'delete':
                lines_original = lines_original[:start_line] + lines_original[end_line:]
            elif change_type == 'insert':
                lines_original = lines_original[:start_line] + content + lines_original[start_line:]
            return True, lines_original, lines_modified
        elif choice == 'n':
            if change_type == 'insert':
                lines_modified = lines_modified[:start_line] + lines_modified[end_line:]
            return False, lines_original, lines_modified
        elif choice == 's':
            return self.subdivide_change(change_type, content, start_line, end_line, lines_original, lines_modified)
        
        print("Invalid choice. Treating as 'n'.")
        return False, lines_original, lines_modified

    def subdivide_change(self, change_type, content, start_line, end_line, lines_original, lines_modified, mid=None):
        """
        细分变更，将大的变更分割成更小的部分。

        :param change_type: 变更类型
        :param content: 变更的内容
        :param start_line: 变更的起始行
        :param end_line: 变更的结束行
        :param lines_original: 原始文本行列表
        :param lines_modified: 修改后的文本行列表
        :param mid: 变更内容的中间位置索引，默认为 None
        :return: 元组 (是否接受变更, 更新后的原始行列表, 更新后的修改行列表)
        """
        if len(content) == 1:
            history_record = "\n<WARNING>\nCannot subdivide further. This is a single line.\n</WARNING>\n"
            print(history_record, end='')
            self.update_history(history_record)
            return self.process_change(change_type, content, start_line, end_line, lines_original, lines_modified)

        if mid is None:
            mid = len(content) // 2
        else:
            mid = mid // 2

        if self.subdivide_depth == 0:
            # 只在最外层执行实际的处理
            first_half = content[:mid]
            second_half = content[mid:]
            
            # 处理第一半
            first_half_end = start_line + mid if change_type == 'delete' else start_line + len(first_half)
            
            if change_type == 'delete':
                temp_lines_original = lines_original[:start_line] + first_half + lines_original[end_line:]
                self.subdivide_depth += 1
                accepted, temp_lines_original, lines_modified = self.process_change(change_type, first_half, start_line, first_half_end, temp_lines_original, lines_modified, 'SUBDIVIDED')
                self.subdivide_depth -= 1
                if accepted:
                    lines_original = temp_lines_original[:first_half_end] + second_half + temp_lines_original[first_half_end:]
                else:
                    lines_original = lines_original[:start_line] + second_half + lines_original[end_line:]
            else:  # insert
                temp_lines_modified = lines_modified[:start_line] + first_half + lines_modified[end_line:]
                self.subdivide_depth += 1
                accepted, lines_original, temp_lines_modified = self.process_change(change_type, first_half, start_line, first_half_end, lines_original, temp_lines_modified, 'SUBDIVIDED')
                self.subdivide_depth -= 1
                if accepted:
                    lines_modified = temp_lines_modified[:first_half_end] + second_half + temp_lines_modified[first_half_end:]
                else:
                    lines_modified = lines_modified[:start_line] + second_half + lines_modified[end_line:]
        else:
            # 在嵌套调用中，只是进一步缩小范围
            self.subdivide_depth -= 1
            result = self.subdivide_change(change_type, content, start_line, end_line, lines_original, lines_modified, mid)
            self.subdivide_depth += 1
            return result
        
        return accepted, lines_original, lines_modified

    def compare_content(self, content_original, content_modified):
        """
        比较原始内容和修改后的内容

        :param content_original: 原始文本内容
        :param content_modified: 修改后的文本内容
        :return: 更新后的文本内容
        """
        self.subdivide_depth = 0  # 初始化 subdivide_depth
        lines_original = content_original.splitlines(keepends=True)
        lines_modified = content_modified.splitlines(keepends=True)
        
        while True:
            diff = list(self.split_diff(lines_original, lines_modified))
            changes_made = False
            for i, item in enumerate(diff):
                if item['type'] == 'equal':
                    continue

                self.next_change_start = None
                if i + 1 < len(diff):
                    next_item = diff[i + 1]
                    if next_item['type'] != 'equal':
                        self.next_change_start = next_item['start_original'] if item['type'] == 'delete' else next_item['start_modified']

                if item['type'] in ['delete', 'insert']:
                    if self.only_process_replace:
                        # 如果只处理 replace，则自动接受 insert 和 delete
                        if item['type'] == 'delete':
                            lines_original = lines_original[:item['start_original']] + lines_original[item['end_original']:]
                        elif item['type'] == 'insert':
                            lines_original = lines_original[:item['start_original']] + item['content'] + lines_original[item['start_original']:]
                        changes_made = True
                    else:
                        accepted, lines_original, lines_modified = self.process_change(
                            item['type'], 
                            item['content'], 
                            item['start_original'] if item['type'] == 'delete' else item['start_modified'],
                            item['end_original'] if item['type'] == 'delete' else item['end_modified'],
                            lines_original, 
                            lines_modified
                        )
                        if accepted or (item['type'] == 'insert' and not accepted):
                            changes_made = True
                    if changes_made:
                        break

                elif item['type'] == 'replace':
                    history_record = "<REPLACE>\n"
                    history_record += "  <OLD>\n"
                    
                    for i, line in enumerate(self.get_context(lines_original, item['start_original'], item['end_original']), start=max(0, item['start_original'] - self.context_lines)):
                        prefix = '-' if item['start_original'] <= i < item['end_original'] else ' '
                        history_record += self.print_line_with_number(line, i, prefix)
                    history_record += "  </OLD>\n"
                    history_record += "  <NEW>\n"
                    for i, line in enumerate(self.get_context(lines_modified, item['start_modified'], item['end_modified']), start=max(0, item['start_modified'] - self.context_lines)):
                        prefix = '+' if item['start_modified'] <= i < item['end_modified'] else ' '
                        history_record += self.print_line_with_number(line, i, prefix)
                    history_record += "  </NEW>\n"
                    history_record += "</REPLACE>\n"
                    
                    print(history_record, end='')
                    self.update_history(history_record)
                    
                    choice, reason = self.decision_func(self.get_full_history())
                    decision_record = f"<DECISION>\n  <CHOICE>{self.CHOICE_EXPLANATION.get(choice, 'unknown')}</CHOICE>\n  <REASON>{reason}</REASON>\n</DECISION>\n"
                    print(decision_record, end='')  
                    self.update_history(decision_record)

                    if choice == 'y':
                        lines_original = lines_original[:item['start_original']] + item['content_modified'] + lines_original[item['end_original']:]
                        changes_made = True
                    elif choice == 'n':
                        lines_modified = lines_modified[:item['start_modified']] + item['content_original'] + lines_modified[item['end_modified']:]
                        changes_made = True
                    elif choice == 's':
                        # 创建临时的 modified lines，先删除要插入的内容
                        temp_lines_modified = lines_modified[:item['start_modified']] + lines_modified[item['end_modified']:]
                        del_lines_modified = lines_modified[item['start_modified']:item['end_modified']]
                        
                        accepted, lines_original, temp_lines_modified = self.process_change(
                            'delete', 
                            item['content_original'], 
                            item['start_original'], 
                            item['end_original'], 
                            lines_original, 
                            temp_lines_modified,
                            master_tag="REPLACE_SUBDIVIDED"
                        )
                        
                        if accepted:
                            # 如果接受了删除，在删除的位置插入新内容
                            insert_position = item['start_original']
                            lines_modified = temp_lines_modified[:insert_position] + del_lines_modified + temp_lines_modified[insert_position:]
                        else:
                            # 如果不接受删除，在原始位置插入新内容
                            insert_position = item['start_modified']
                            del_lines_original = lines_original[item['start_original']:item['end_original']]
                            lines_modified = temp_lines_modified[:insert_position] + del_lines_original + del_lines_modified + temp_lines_modified[insert_position:]
                        
                        changes_made = True
                    break

            if not changes_made:
                return ''.join(lines_original)



# 主程序
if __name__ == "__main__":
    # 默认的比较字符串
    DEFAULT_ORIGINAL = '''# This is a complex Python script to demonstrate different changes

import os
import sys
from datetime import datetime

def calculate_sum(a, b):
    """Calculate the sum of two numbers"""
    return a + b

def calculate_product(a, b):
    """Calculate the product of two numbers"""
    return a * b

class MathOperations:
    def __init__(self):
        self.operations = {
            'add': calculate_sum,
            'multiply': calculate_product
        }
    
    def perform_operation(self, operation, x, y):
        if operation in self.operations:
            return self.operations[operation](x, y)
        else:
            raise ValueError(f"Unsupported operation: {operation}")

def process_file(filename):
    if not os.path.exists(filename):
        print(f"File {filename} does not exist.")
        return
    
    with open(filename, 'r') as f:
        content = f.read()
        print(f"File content: {content}")

def main():
    math_ops = MathOperations()
    x, y = 10, 5
    
    print(f"Sum of {x} and {y}: {math_ops.perform_operation('add', x, y)}")
    print(f"Product of {x} and {y}: {math_ops.perform_operation('multiply', x, y)}")
    
    process_file('example.txt')
    
    print(f"Current date and time: {datetime.now()}")

if __name__ == "__main__":
    main()
'''

    DEFAULT_MODIFIED = '''# This is a modified complex Python script to demonstrate various changes

import os
import sys
from datetime import datetime
import random  # New import

def calculate_sum(a, b):
    """Calculate the sum of two numbers"""
    return a + b

def calculate_product(a, b):
    """Calculate the product of two numbers"""
    return a * b

def calculate_difference(a, b):  # New function
    """Calculate the difference between two numbers"""
    return a - b

class MathOperations:
    def __init__(self):
        self.operations = {
            'add': calculate_sum,
            'multiply': calculate_product,
            'subtract': calculate_difference  # New operation
        }
    
    def perform_operation(self, operation, x, y):
        if operation in self.operations:
            return self.operations[operation](x, y)
        else:
            raise ValueError(f"Unsupported operation: {operation}")

def process_file(filename):
    # 前面实现，保持不变
    with open(filename, 'a') as f:
        f.write(f"\\nRandom number: {random.randint(1, 100)}")

def main():
    math_ops = MathOperations()
    x, y = 10, 5
    
    # 文件处理保持不变
    
    print(f"Python version: {sys.version}")
    print(f"Operating system: {os.name}")

if __name__ == "__main__":
    main()
'''
    import agentscope
    from goodrock_model_wrapper import GoodRockModelWrapper
    
    agentscope.init(
        model_configs="../../configs/model_configs.json"
    )

    
    def get_content(source):
        """
        获取内容,可以是文件路径或直接字符串

        :param source: 文件路径或直接字符串
        :return: 文本内容
        """
        if os.path.isfile(source):
            with open(source, 'r') as f:
                return f.read()
        else:
            return source
        
    if len(sys.argv) >= 3:
        content1 = get_content(sys.argv[1])
        content2 = get_content(sys.argv[2])
    else:
        content1 = DEFAULT_ORIGINAL
        content2 = DEFAULT_MODIFIED

    diff_decision = DiffDecision()
    only_process_replace = True  # 或 False，根据需要设置
    diff_processor = DiffProcessor(decision_func=diff_decision.make_decision, only_process_replace=only_process_replace)
    # diff_processor = DiffProcessor()
    
    updated_content = diff_processor.compare_content(content1, content2)

    print("\n==== Updated Content ====")
    print(updated_content)

    save = input("--> Do you want to save the updated content to a file? (y/n): ").lower().strip()
    if save == 'y':
        filename = input("Enter filename to save: ")
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        print(f"==== Updated content has been saved to '{filename}' ====")