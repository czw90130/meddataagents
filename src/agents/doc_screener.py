import os
import sys
from agentscope.agents import DictDialogAgent
from functools import partial
from agentscope.message import Msg
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from yaml_object_parser import MarkdownYAMLDictParser
from doc_read_tools import file2text

class DocScreener:
    """
    文档初筛员(DocScreener)
    专门负责分析和总结各种类型的文档。其任务是审查文档内容，提供摘要，
    确定文档类型，并评估其结构。
    """
    HostMsg = partial(Msg, name="Moderator", role="assistant")
    
    def __init__(self):
        self.agent = DictDialogAgent(
            name="DocScreener",
            sys_prompt=(
                "You are a Document Screener specialized in analyzing and summarizing various types of documents. "
                "Your task is to review document content, provide a summary, determine the document type, "
                "and assess its structure.\n\n"
                "# Responsibilities\n\n"
                "1. Analyze Document Content: Review the content provided.\n"
                "2. Summarize Document: Provide a concise summary of the document's main points.\n"
                "3. Determine Document Type: Classify the document into one of the specified categories.\n"
                "4. Assess Document Structure: Evaluate the structure of the document and categorize it as WELL, UNREADABLE, or RECONCILE.\n\n"
                "# Document Types\n"
                "- NONE: Empty or unrecognizable content\n"
                "- PLAIN_TEXT: Pure text without any formatting\n"
                "- TEXT_WITH_IMGS, TEXT_WITH_TABLES, or TEXT_WITH_IMGS_TABLES: Text with embedded images, tables, or both\n"
                "- UNFORMATTED_TABLE: Tabular data without clear formatting\n"
                "- ROW_HEADER_TABLE: Table with headers for each row\n"
                "- COL_HEADER_TABLE: Table with headers for each column\n"
                "- RAW_DATA_LIST: List of data without headers\n"
                "- STRUCTURED_REPORT: Well-structured report with clear sections\n"
                "- MULTI_SECTION_DOC: Document with multiple distinct sections\n"
                "- MIXED_CONTENT: Document with a mix of different content types\n\n"
                "# Document Structure Categories\n"
                "- WELL: The structure is clear and easy to read\n"
                "- UNREADABLE: The structure cannot be read normally\n"
                "- RECONCILE: The structure can be reconstructed (e.g., double-column structure common in PDFs)\n\n"
                "# Important Notes\n"
                "1. When analyzing files with extensions such as .xls, .xlsx, .csv, or similar table formats, "
                "prioritize classifying them as TABLE types (e.g., UNFORMATTED_TABLE, COL_HEADER_TABLE, "
                "ROW_HEADER_TABLE) or RAW_DATA_LIST instead of TEXT types. This applies "
                "even if the content has been converted to a markdown format.\n\n"
                "2. For Excel files converted to markdown, pay attention to subtable headers marked with '#'. "
                "Each subtable should be evaluated separately.\n\n"
                "3. Consider the file extension when determining the document type. For example, .xlsx or .csv "
                "files should typically be classified as COL_HEADER_TABLE or ROW_HEADER_TABLE unless the content "
                "clearly indicates otherwise.\n\n"
            ),
            model_config_name="claude3",
            use_memory=False
        )

        self.parser = MarkdownYAMLDictParser(
            content_hint={
                "summary": "A concise summary of the document's main points.",
                "doc_type": "The document type based on the given categories. Prioritize TABLE types for spreadsheet formats.",
                "structure": "The structure category of the document (WELL, UNREADABLE, or RECONCILE[...]). If RECONCILE, include specific reconstruction methods in [...].",
                "reasoning": "Explanation for the document type and structure assessment choices."
            },
            keys_to_content="summary",
            keys_to_metadata=True
        )
        self.agent.set_parser(self.parser)

    def prepare_content(self, text_content, content_name=None, max_length=8000):
        """
        准备文档内容，如果超过最大长度则进行截取
        claude3 可设置 max_length=100000
        qwen 可设置 max_length=8000
        """
        if content_name:
            prepared_content = f"CONTENT_NAME: {content_name}\nCONTENT:\n```\n"
        else:
            prepared_content = "```\n"

        if len(text_content) > max_length:
            half_length = max_length // 2
            omitted_words = len(text_content) - max_length
            prepared_content += (
                f"{text_content[:half_length]}\n"
                f"```\n\n... ... ({omitted_words} WORDS ARE OMITTED HERE) ... ...\n\n```\n"
                f"{text_content[-half_length:]}"
            )
        else:
            prepared_content += text_content

        prepared_content += "\n```"
        return prepared_content

    def doc_screen_task(self, text_content, content_name=None):
        """
        DocScreener任务
        - text_content: 文档内容
        - content_name: 文档名称（可选）
        """
        prepared_content = self.prepare_content(text_content, content_name)
        
        prompt = (
            "# Document Content\n"
            f"{prepared_content}\n\n"
            "Please analyze the above document content and provide the following information:\n"
            "1. A concise summary of the document's main points.\n"
            "2. The document type based on the given categories. Remember to prioritize TABLE or RAW_DATA_LIST types for spreadsheet formats.\n"
            "3. An assessment of the document's structure (WELL, UNREADABLE, or RECONCILE[...]).\n"
            "Ensure your response follows the specified format for easy parsing."
        )
        if content_name is not None:
            prompt = f"# Document Name: {content_name}\n\n" + prompt

        hint = self.HostMsg(content=prompt)
        return self.agent(hint)

    def __call__(self, input_data, tmp_dir=None):
        """
        处理输入数据，可以是文本内容、文件路径或带有文件名的元组
        """
        if isinstance(input_data, str):
            if os.path.isfile(input_data):
                # 输入是文件路径
                content, files, md_path = file2text(input_data, tmp_dir)
                result = self.doc_screen_task(content, os.path.basename(input_data))

                result.metadata['input_file_path'] = os.path.abspath(input_data)
                result.metadata['md_file_path'] = md_path
                result.metadata['associated_files'] = files
                
                return result
            else:
                # 输入是文本内容
                return self.doc_screen_task(input_data)
        elif isinstance(input_data, tuple) and len(input_data) == 2:
            # 输入是 (text_content, content_name) 元组
            return self.doc_screen_task(input_data[0], input_data[1])
        else:
            raise ValueError("Invalid input. Expected a string (file path or text content) or a tuple (text_content, content_name).")
    
if __name__ == "__main__":
    import os
    import sys
    from pathlib import Path
    import agentscope
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from bedrock_model_wrapper import BedrockCheckModelWrapper
    
    agentscope.init(
        model_configs="../configs/model_configs.json"
    )

    # 创建 DocScreener 实例
    doc_screener = DocScreener()

    # 检查是否提供了文件路径参数
    if len(sys.argv) < 2:
        print("请提供要分析的文件路径作为命令行参数。")
        sys.exit(1)

    # 调用 DocScreener
    # 使用文件路径
    result = doc_screener(sys.argv[1])

    # 打印结果
    print("DocScreener 结果:")
    print(result.metadata)

    # 从解析结果中访问特定字段
    print("\n解析后的结果:")
    print(f"摘要: {result.metadata['summary']}")
    print(f"文档类型: {result.metadata['doc_type']}")
    print(f"结构: {result.metadata['structure']}")
    print(f"推理: {result.metadata['reasoning']}")