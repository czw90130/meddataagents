from agentscope.agents import DictDialogAgent
from agentscope.parsers.json_object_parser import MarkdownJsonDictParser
from functools import partial
from agentscope.message import Msg
class DocScreener:
    """
    文档初筛员(DocScreener)
    专门负责分析和总结各种类型的文档。其任务是审查文档内容，提供摘要，
    确定文档类型，评估其结构，并评估其是否适合导入SQL数据库。
    """
    HostMsg = partial(Msg, name="Moderator", role="assistant")
    def __init__(self):
        self.agent = DictDialogAgent(
            name="DocScreener",
            sys_prompt=("You are a Document Screener specialized in analyzing and summarizing various types of documents. "
                        "Your task is to review document content, provide a summary, determine the document type, "
                        "assess its structure, and evaluate its suitability for SQL import.\n\n"
                        "# Responsibilities\n\n"
                        "1. Analyze Document Content: Review the content provided.\n"
                        "2. Summarize Document: Provide a concise summary of the document's main points.\n"
                        "3. Determine Document Type: Classify the document into one of the specified categories.\n"
                        "4. Assess Document Structure: Evaluate the structure of the document and categorize it as WELL, UNREADABLE, or RECONCILE.\n"
                        "5. Assess SQL Import Suitability: Evaluate whether the document can be imported into SQL and provide appropriate recommendations.\n\n"
                        "# Document Types\n"
                        "- NONE: Empty or unrecognizable content\n"
                        "- PLAIN_TEXT: Pure text without any formatting\n"
                        "- TEXT_WITH_IMAGES: Text with embedded images\n"
                        "- TEXT_WITH_TABLES: Text with tables\n"
                        "- TEXT_WITH_IMAGES_AND_TABLES: Text with both images and tables\n"
                        "- UNFORMATTED_TABLE: Unformatted tabular data\n"
                        "- FULL_HEADER_TABLE: Table with both row and column headers\n"
                        "- ROW_HEADER_TABLE: Table with only row headers\n"
                        "- COL_HEADER_TABLE: Table with only column headers\n"
                        "- RAW_DATA_LIST: List of data without headers\n"
                        "- STRUCTURED_REPORT: Well-structured report with clear sections\n"
                        "- MULTI_SECTION_DOC: Document with multiple distinct sections\n"
                        "- MIXED_CONTENT: Document with a mix of different content types\n\n"
                        "# Document Structure Categories\n"
                        "- WELL: The structure is clear and easy to read\n"
                        "- UNREADABLE: The structure cannot be read normally\n"
                        "- RECONCILE: The structure can be reconstructed (e.g., double-column structure common in PDFs)\n\n"
                        "# SQL Import Suitability\n"
                        "- NULL: Not applicable (non-tabular data)\n"
                        "- NO: Cannot be imported into SQL\n"
                        "- TRANS: Can be imported after specific transformations (describe in detail)\n"
                        "- YES: Can be directly imported using process_file function\n\n"
                        "Your goal is to provide accurate and helpful information for further processing of the document."),
            model_config_name="claude3",
            use_memory=False
        )

        self.parser = MarkdownJsonDictParser(
            content_hint={
                "summary": "A concise summary of the document's main points.",
                "doc_type": "The document type based on the given categories.",
                "structure": "The structure category of the document (WELL, UNREADABLE, or RECONCILE[{...}]). If RECONCILE, include specific reconstruction methods in {...}.",
                "sql_import": "Assessment of suitability for SQL import (NULL, NO, TRANS, or YES).",
                "reasoning": "Explanation for the document type, structure assessment, and SQL import suitability choices."
            },
            keys_to_content="summary",
            keys_to_metadata=True
        )
        self.agent.set_parser(self.parser)

    def prepare_content(self, text_content, content_name=None, max_length=8000):
        """
        准备文档内容，如果超过最大长度则进行截取
        claude3 可设置 max_length=100000
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
            "2. The document type based on the given categories.\n"
            "3. An assessment of the document's structure (WELL, UNREADABLE, or RECONCILE[{...}]).\n"
            "4. An assessment of its suitability for SQL import.\n"
            "Ensure your response follows the specified format for easy parsing."
        )
        hint = self.HostMsg(content=prompt)
        return self.agent(hint)

    def __call__(self, text_content, content_name=None):
        return self.doc_screen_task(text_content, content_name)