# -*- coding: utf-8 -*-
"""YAML对象在模型响应中的解析器。"""
import inspect
import yaml
from copy import deepcopy
from typing import Optional, Any, List, Sequence, Union

from loguru import logger
from pydantic import BaseModel

from agentscope.exception import (
    TagNotFoundError,
    JsonParsingError,
    JsonTypeError,
    RequiredFieldNotFoundError,
)
from agentscope.models import ModelResponse
from agentscope.parsers import ParserBase
from agentscope.parsers.parser_base import DictFilterMixin
from agentscope.utils.tools import _join_str_with_comma_and


class MarkdownYAMLDictParser(ParserBase, DictFilterMixin):
    """用于解析Markdown代码块中的YAML字典对象的类"""

    name: str = "yaml block"
    """解析器的名称。"""

    tag_begin: str = "```yaml"
    """代码块的开始标签。"""

    content_hint: str = "{your_yaml_dictionary}"
    """内容提示。"""

    tag_end: str = "```"
    """代码块的结束标签。"""

    _format_instruction = (
        "Respond a YAML dictionary in a markdown's fenced code block as "
        "follows:\n```yaml\n{content_hint}\n```\n"
        "Important: Ensure all YAML keys and string values are correctly formatted. "
        "When a string value contains special characters, enclose it in quotes. For example:\n"
    )
    """YAML对象格式的指令。"""

    _format_instruction_with_schema = (
        "Respond a YAML dictionary in a markdown's fenced code block as "
        "follows:\n"
        "```yaml\n"
        "{content_hint}\n"
        "```\n"
        "The generated YAML dictionary MUST follow this schema: \n"
        "{schema}\n"
        "Important: Ensure all YAML keys and string values are correctly formatted. "
        "When a string value contains special characters, enclose it in quotes.\n"
    )
    """带有模式的YAML对象格式指令。"""

    required_keys: List[str]
    """YAML字典对象中必需的键列表。如果响应中缺少任何必需的键，将引发RequiredFieldNotFoundError。"""

    def __init__(
        self,
        content_hint: Optional[Any] = None,
        required_keys: List[str] = None,
        keys_to_memory: Optional[Union[str, bool, Sequence[str]]] = True,
        keys_to_content: Optional[Union[str, bool, Sequence[str]]] = True,
        keys_to_metadata: Optional[Union[str, bool, Sequence[str]]] = False,
    ) -> None:
        """
        初始化解析器。

        参数:
            content_hint (Optional[Any], 默认为 None):
                用于提醒LLM在标签之间应填充什么的提示。如果是字符串，将直接用作内容提示。
                如果是字典，将转换为YAML字符串并用作内容提示。如果是Pydantic模型，
                其模式将显示在指令中。
            required_keys (List[str], 默认为 []):
                YAML字典对象中必需的键列表。如果响应中缺少任何必需的键，将引发RequiredFieldNotFoundError。
            keys_to_memory (Optional[Union[str, bool, Sequence[str]]], 默认为 True):
                在 to_memory 方法中要过滤的键或键列表。如果是：
                - False，to_memory 方法将返回 None
                - str，将返回相应的值
                - List[str]，将返回过滤后的字典
                - True，将返回整个字典
            keys_to_content (Optional[Union[str, bool, Sequence[str]]], 默认为 True):
                在 to_content 方法中要过滤的键或键列表。如果是：
                - False，to_content 方法将返回 None
                - str，将返回相应的值
                - List[str]，将返回过滤后的字典
                - True，将返回整个字典
            keys_to_metadata (Optional[Union[str, bool, Sequence[str]]], 默认为 False):
                在 to_metadata 方法中要过滤的键或键列表。如果是：
                - False，to_metadata 方法将返回 None
                - str，将返回相应的值
                - List[str]，将返回过滤后的字典
                - True，将返回整个字典
        """
        self.pydantic_class = None

        # 根据content_hint的类型初始化content_hint
        if inspect.isclass(content_hint) and issubclass(
            content_hint,
            BaseModel,
        ):
            self.pydantic_class = content_hint
            self.content_hint = "{a_YAML_dictionary}"
        elif content_hint is not None:
            if isinstance(content_hint, str):
                self.content_hint = content_hint
            else:
                self.content_hint = yaml.dump(
                    content_hint,
                    allow_unicode=True,
                    default_flow_style=False,
                )

        # 初始化mixin类以允许过滤解析后的响应
        DictFilterMixin.__init__(
            self,
            keys_to_memory=keys_to_memory,
            keys_to_content=keys_to_content,
            keys_to_metadata=keys_to_metadata,
        )

        self.required_keys = required_keys or []

    @property
    def format_instruction(self) -> str:
        """获取YAML对象的格式指令，如果提供了format_example，将用作示例。"""
        if self.pydantic_class is None:
            return self._format_instruction.format(
                content_hint=self.content_hint,
            )
        else:
            return self._format_instruction_with_schema.format(
                content_hint=self.content_hint,
                schema=self.pydantic_class.model_json_schema(),
            )

    def parse(self, response: ModelResponse) -> ModelResponse:
        """
        将响应的文本字段解析为YAML字典对象，将其存储在响应对象的parsed字段中，
        并检查是否存在必需的键。
        """
        # 提取内容并尝试手动修复缺失的标签
        try:
            extract_text = self._extract_first_content_by_tag(
                response,
                self.tag_begin,
                self.tag_end,
            )
        except TagNotFoundError as e:
            # 尝试通过添加标签来修复缺失的标签错误
            try:
                response_copy = deepcopy(response)

                # 修复缺失的标签
                if e.missing_begin_tag:
                    response_copy.text = (
                        self.tag_begin + "\n" + response_copy.text
                    )
                if e.missing_end_tag:
                    response_copy.text = response_copy.text + self.tag_end

                # 再次尝试提取内容
                extract_text = self._extract_first_content_by_tag(
                    response_copy,
                    self.tag_begin,
                    self.tag_end,
                )

                # 用修复后的响应替换原响应
                response.text = response_copy.text

                logger.debug("通过手动添加标签修复了缺失的标签。")

            except TagNotFoundError:
                # 如果缺失的标签无法修复，则引发原始错误
                raise e from None

        # 将内容解析为YAML对象
        try:
            parsed_yaml = yaml.safe_load(extract_text)
            response.parsed = parsed_yaml
        except yaml.YAMLError as e:
            raw_response = f"{self.tag_begin}{extract_text}{self.tag_end}"
            raise JsonParsingError(
                f"{self.tag_begin} 和 {self.tag_end} 之间的内容必须是一个YAML对象。"
                f'解析 "{raw_response}" 时发生错误: {e}',
                raw_response=raw_response,
            ) from None

        if not isinstance(response.parsed, dict):
            # 如果不是字典，则引发错误
            raise JsonTypeError(
                f"需要YAML字典对象，但得到了 {type(response.parsed)}。",
                response.text,
            )

        # 使用Pydantic进行需求检查
        if self.pydantic_class is not None:
            try:
                response.parsed = dict(self.pydantic_class(**response.parsed))
            except Exception as e:
                raise JsonParsingError(
                    message=str(e),
                    raw_response=response.text,
                ) from None

        # 检查是否存在必需的键
        keys_missing = []
        for key in self.required_keys:
            if key not in response.parsed:
                keys_missing.append(key)

        if len(keys_missing) != 0:
            raise RequiredFieldNotFoundError(
                f"YAML字典对象中缺少必需的"
                f"字段{'' if len(keys_missing)==1 else 's'} "
                f"{_join_str_with_comma_and(keys_missing)}。",
                response.text,
            )

        return response