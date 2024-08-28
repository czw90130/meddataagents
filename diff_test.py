# -*- coding: utf-8 -*-
import difflib
import os
from collections import deque

# 初始化一个双端队列,用于存储最近n次的完整历史记录
history_queue = deque(maxlen=5)

def update_history(new_record):
    global history_queue
    history_queue.append(new_record)

def get_full_history():
    return '\n'.join(history_queue)

def get_content(source):
    """
    获取内容,可以是文件路径或直接字符串
    """
    if os.path.isfile(source):
        with open(source, 'r') as f:
            return f.read()
    else:
        return source

def split_diff(original, modified):
    """
    使用difflib比较原始和修改后的内容,生成差异信息
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

def get_context(lines, start, end, context=5, next_change_start=None):
    """
    获取上下文行，避免获取到下一个变更块
    """
    context_start = max(0, start - context)
    context_end = min(len(lines), end + context)
    if next_change_start is not None:
        context_end = min(context_end, next_change_start)
    return lines[context_start:context_end]

def print_line_with_number(line, line_number, prefix=' '):
    """
    打印带行号的行,同时记录到历史
    """
    return f"{prefix}{line_number:4d}|{line.rstrip()}\n"
    
def auto_decision(history):
    """
    根据历史记录自动决定是否接受更改
    :param history: 之前的XML历史记录
    :return: (choice, reason)
    """
    # 这里可以实现您的自动决策逻辑
    # 现在只是一个简单的示例，始终返回 'y'
    return 'y', "Automatic decision: always accept"

def process_change(change_type, content, start_line, end_line, lines_original, lines_modified, subdivide_depth=0, next_change_start=None, master_tag=None, decision_func=None):
    history_record = ""
    
    if master_tag is not None:
        history_record += f"<{master_tag}>\n  <{change_type.upper()}>\n"
    else:
        history_record += f"<{change_type.upper()}>\n"
    
    if change_type == 'insert':
        context_lines = get_context(lines_modified, start_line, end_line, next_change_start=next_change_start)
    else:  # delete
        context_lines = get_context(lines_original, start_line, end_line, next_change_start=next_change_start)
    
    context_start = max(0, start_line - 5)
    for i, line in enumerate(context_lines, start=context_start):
        prefix = '+' if change_type == 'insert' and start_line <= i < end_line else \
                 '-' if change_type == 'delete' and start_line <= i < end_line else ' '
        line_output = print_line_with_number(line, i, prefix)
        history_record += line_output
    
    if master_tag is not None:
        history_record += f"  </{change_type.upper()}>\n</{master_tag}>\n"
    else:
        history_record += f"</{change_type.upper()}>\n"
    
    print(history_record, end='')
    update_history(history_record)
    
    choice, reason = decision_func(get_full_history())
    choice_explanation = {'y': 'accept', 'n': 'reject', 's': 'subdivide'}
    decision_record = f"<DECISION>\n  <CHOICE>{choice} - {choice_explanation.get(choice, 'unknown')}</CHOICE>\n  <REASON>{reason}</REASON>\n</DECISION>\n"
    
    print(decision_record, end='')
    update_history(decision_record)
    
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
        return subdivide_change(change_type, content, start_line, end_line, lines_original, lines_modified, subdivide_depth, None, next_change_start, decision_func)
    
    print("Invalid choice. Treating as 'n'.")
    return False, lines_original, lines_modified

def subdivide_change(change_type, content, start_line, end_line, lines_original, lines_modified, subdivide_depth, mid=None, next_change_start=None, decision_func=None):
    if len(content) == 1:
        print("Cannot subdivide further. This is a single line.")
        return process_change(change_type, content, start_line, end_line, lines_original, lines_modified, subdivide_depth, next_change_start, decision_func=decision_func)

    if mid is None:
        mid = len(content) // 2
    else:
        mid = mid // 2

    if subdivide_depth == 0:
        # 只在最外层执行实际的处理
        first_half = content[:mid]
        second_half = content[mid:]
        
        # 处理第一半
        first_half_end = start_line + mid if change_type == 'delete' else start_line + len(first_half)
        
        if change_type == 'delete':
            temp_lines_original = lines_original[:start_line] + first_half + lines_original[end_line:]
            accepted, temp_lines_original, lines_modified = process_change(change_type, first_half, start_line, first_half_end, temp_lines_original, lines_modified, subdivide_depth + 1, next_change_start, 'SUBDIVIDED', decision_func)
            if accepted:
                lines_original = temp_lines_original[:first_half_end] + second_half + temp_lines_original[first_half_end:]
            else:
                lines_original = lines_original[:start_line] + second_half + lines_original[end_line:]
        else:  # insert
            temp_lines_modified = lines_modified[:start_line] + first_half + lines_modified[end_line:]
            accepted, lines_original, temp_lines_modified = process_change(change_type, first_half, start_line, first_half_end, lines_original, temp_lines_modified, subdivide_depth + 1, next_change_start, 'SUBDIVIDED', decision_func)
            if accepted:
                lines_modified = temp_lines_modified[:first_half_end] + second_half + temp_lines_modified[first_half_end:]
            else:
                lines_modified = lines_modified[:start_line] + second_half + lines_modified[end_line:]
    else:
        # 在嵌套调用中，只是进一步缩小范围
        return subdivide_change(change_type, content, start_line, end_line, lines_original, lines_modified, subdivide_depth - 1, mid, next_change_start, decision_func)
    
    return accepted, lines_original, lines_modified

def compare_content(content_original, content_modified, decision_func):
    """
    比较原始内容和修改后的内容
    """
    lines_original = content_original.splitlines(keepends=True)
    lines_modified = content_modified.splitlines(keepends=True)
    
    while True:
        diff = list(split_diff(lines_original, lines_modified))
        changes_made = False
        for i, item in enumerate(diff):
            if item['type'] == 'equal':
                continue

            next_change_start = None
            if i + 1 < len(diff):
                next_item = diff[i + 1]
                if next_item['type'] != 'equal':
                    next_change_start = next_item['start_original'] if item['type'] == 'delete' else next_item['start_modified']

            if item['type'] in ['delete', 'insert']:
                accepted, lines_original, lines_modified = process_change(
                    item['type'], 
                    item['content'], 
                    item['start_original'] if item['type'] == 'delete' else item['start_modified'],
                    item['end_original'] if item['type'] == 'delete' else item['end_modified'],
                    lines_original, 
                    lines_modified,
                    next_change_start=next_change_start,
                    decision_func=decision_func
                )
                if accepted or (item['type'] == 'insert' and not accepted):
                    changes_made = True
                    break

            elif item['type'] == 'replace':
                history_record = "<REPLACE>\n"
                history_record += "  <OLD>\n"
                
                for i, line in enumerate(get_context(lines_original, item['start_original'], item['end_original'], next_change_start=next_change_start), start=max(0, item['start_original'] - 5)):
                    prefix = '-' if item['start_original'] <= i < item['end_original'] else ' '
                    history_record += print_line_with_number(line, i, prefix)
                history_record += "  </OLD>\n"
                history_record += "  <NEW>\n"
                for i, line in enumerate(get_context(lines_modified, item['start_modified'], item['end_modified'], next_change_start=next_change_start), start=max(0, item['start_modified'] - 5)):
                    prefix = '+' if item['start_modified'] <= i < item['end_modified'] else ' '
                    history_record += print_line_with_number(line, i, prefix)
                history_record += "  </NEW>\n"
                history_record += "</REPLACE>\n"
                
                print(history_record, end='')
                update_history(history_record)
                
                choice, reason = decision_func(get_full_history())
                choice_explanation = {'y': 'accept', 'n': 'reject', 's': 'subdivide'}
                decision_record = f"<DECISION>\n  <CHOICE>{choice} - {choice_explanation.get(choice, 'unknown')}</CHOICE>\n  <REASON>{reason}</REASON>\n</DECISION>\n"
                print(decision_record, end='')  
                update_history(decision_record)

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
                    
                    accepted, lines_original, temp_lines_modified = process_change(
                        'delete', 
                        item['content_original'], 
                        item['start_original'], 
                        item['end_original'], 
                        lines_original, 
                        temp_lines_modified,
                        next_change_start=next_change_start,
                        master_tag="REPLACE_SUBDIVIDED",
                        decision_func=decision_func
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

# 主程序
if __name__ == "__main__":
    import sys
    
    def manual_decision(history):
        print_history = input("是否打印历史记录？(y/n): ").lower().strip()
        if print_history == 'y':
            print("\n========== 历史记录 ==========")
            print(history)
            print("====== 历史记录打印结束 ======\n\n")
        choice = input(f"\nAccept this change? (y/n/s for subdivide): ").lower().strip()
        return choice, "Manually confirmation"

    if len(sys.argv) >= 3:
        content1 = get_content(sys.argv[1])
        content2 = get_content(sys.argv[2])
    else:
        content1 = DEFAULT_ORIGINAL
        content2 = DEFAULT_MODIFIED

    updated_content = compare_content(content1, content2, manual_decision)

    print("\n==== Updated Content ====")
    print(updated_content)

    save = input("--> Do you want to save the updated content to a file? (y/n): ").lower().strip()
    if save == 'y':
        filename = input("Enter filename to save: ")
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        print(f"==== Updated content has been saved to '{filename}' ====")