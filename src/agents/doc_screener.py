import os
import sys
from agentscope.agents import DictDialogAgent
from functools import partial
from agentscope.message import Msg
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agents.tools.yaml_object_parser import MarkdownYAMLDictParser
from agents.tools.doc_read_tools import file2text

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
                "and assess its structure."
            ),
            model_config_name="kuafu3.5",
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
            "<task_overview>\n"
            "Analyze the provided document content and report on:\n"
            "1. Content summary\n"
            "2. Document type\n"
            "3. Document structure\n"
            "</task_overview>\n\n"
            
            "<document_types>\n"
            "Prioritize TABLE types for spreadsheet formats\n"
            "- NONE: Empty/unrecognizable\n"
            "<enums>"
            "- PLAIN_TEXT: Pure text\n"
            "- TEXT_WITH_IMGS, TEXT_WITH_TABLES, TEXT_WITH_IMGS_TABLES: Text with images/tables\n"
            "- UNFORMATTED_TABLE: Tabular data without clear formatting\n"
            "- ROW_HEADER_TABLE: Table with row headers\n"
            "- COL_HEADER_TABLE: Table with column headers\n"
            "- RAW_DATA_LIST: Data list without headers\n"
            "- STRUCTURED_REPORT: Well-structured report\n"
            "- MULTI_SECTION_DOC: Multiple distinct sections\n"
            "- MIXED_CONTENT: Mix of different content types\n"
            "</enums>"
            "</document_types>\n\n"
            
            "<structure_categories>\n"
            "<enums>"
            "- WELL: Clear and readable\n"
            "- UNREADABLE: Cannot be read normally\n"
            "- RECONCILE: Can be reconstructed (e.g., double-column PDF)\n"
            "</enums>"
            "</structure_categories>\n\n"
            
            "<key_points>\n"
            "1. For .xls, .xlsx, .csv files, prioritize TABLE or RAW_DATA_LIST types.\n"
            "2. In Excel-to-markdown conversions, evaluate subtables (marked with '#') separately.\n"
            "3. Consider file extension in type determination.\n"
            "</key_points>\n\n"
        )
            
        suffix_prompt = ("<document_content>\n"
            f"{prepared_content}\n"
            "</document_content>\n\n"
            
            "<instructions>\n"
            "Analyze the above content and provide:\n"
            "1. Concise summary of main points\n"
            "2. Document type (prioritize TABLE/RAW_DATA_LIST for spreadsheets)\n"
            "3. Structure assessment (WELL/UNREADABLE/RECONCILE)\n"
            "Format your response for easy parsing.\n"
            "</instructions>\n"
        )
        
        if content_name is not None:
            suffix_prompt = f"<document_name>{content_name}</document_name>\n\n" + suffix_prompt

        hint = self.HostMsg(content=prompt+suffix_prompt)
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
    from goodrock_model_wrapper import GoodRockModelWrapper
    
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