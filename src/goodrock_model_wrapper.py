# -*- coding: utf-8 -*-
"""Model wrapper for Kuafu models"""
from typing import Union, Any, List, Sequence, Dict
import json
import requests

from loguru import logger

from agentscope.models import ModelWrapperBase, ModelResponse
from agentscope.message import Msg
from agentscope.utils.tools import _convert_to_str

class GoodRockModelWrapper(ModelWrapperBase):
    """The model wrapper for Kuafu API."""

    model_type: str = "goodrock_chat"

    def __init__(
        self,
        config_name: str,
        model_name: str = "kuafu-max-v3.5",
        api_key: str = "",
        api_base: str = "http://localhost:8000",
        generate_args: dict = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Kuafu client.

        Args:
            config_name (`str`):
                The name of the model config.
            model_name (`str`, default `"kuafu-max-v3.5"`):
                The name of the model to use in Kuafu API.
            api_key (`str`, default `""`):
                The API key for the Kuafu API.
            api_base (`str`, default `"http://localhost:8000"`):
                The base URL for the Kuafu API.
            generate_args (`dict`, default `None`):
                The extra keyword arguments used in Kuafu API generation,
                e.g. `temperature`, `max_tokens`.
        """
        super().__init__(config_name=config_name, model_name=model_name)

        self.api_key = api_key
        self.api_base = api_base
        self.generate_args = generate_args or {}
        

        # Set the max length of Kuafu model
        self.max_length = 4096  # This might need to be adjusted based on the specific model

    def __call__(
        self,
        messages: list,
        **kwargs: Any,
    ) -> ModelResponse:
        """Process a list of messages and generate a response using the Kuafu API.

        Args:
            messages (`list`):
                A list of messages to process.
            **kwargs (`Any`):
                Additional keyword arguments for the Kuafu API call.

        Returns:
            `ModelResponse`:
                The response text in the text field, and the raw response in
                the raw field.
        """

        # Prepare keyword arguments
        kwargs = {**self.generate_args, **kwargs}

        # Check messages
        if not isinstance(messages, list):
            raise ValueError(
                f"Kuafu `messages` field expected type `list`, "
                f"got `{type(messages)}` instead.",
            )
        if not all("role" in msg and "content" in msg for msg in messages):
            raise ValueError(
                "Each message in the 'messages' list must contain a 'role' "
                "and 'content' key for Kuafu API.",
            )
        

        # Extract system prompt and format messages
        # TODO: Text Only 
        # system_prompt = "You are a helpful assistant."
        formatted_messages = ""
        for msg in messages:
            # if msg["role"] == "system":
            #     system_prompt = msg["content"]
            # else:
            formatted_messages += f"{msg['role']}:\n {msg['content']}\n\n"
        
        formatted_messages = [{"role": "user", "content": formatted_messages[:-2]}]

        # Prepare the request body
        body = {
            "llm_model": self.model_name,
            "system_prompt": "",
            "messages": formatted_messages,
            "max_tokens": self.max_length,
            # "params": kwargs
        }

        headers = {
            # "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }

        try:
            # Call the Kuafu API
            response = requests.post(f"{self.api_base}/generate_message", json=body, headers=headers)
            response.raise_for_status()
            result = response.json()
        except Exception as e:
            logger.error(f"Error calling Kuafu API: {e}")
            logger.error(f"Response content: {response.text}")  # 打印完整的响应内容
            raise

        # Record the API invocation
        self._save_model_invocation(
            arguments={
                "model": self.model_name,
                "messages": messages,
                **kwargs,
            },
            response=result,
        )

        # Update monitor
        token_prompt = result["token_usage"]["input_tokens"]
        token_response = result["token_usage"]["output_tokens"]
        self.monitor.update_text_and_embedding_tokens(
            model_name=self.model_name,
            prompt_tokens=token_prompt,
            completion_tokens=token_response,
        )

        # Process and return the response
        output_text = result["response"]["content"][0]["text"]

        return ModelResponse(
            text=output_text,
            raw=result,
        )

    def format(
        self,
        *args: Union[Msg, Sequence[Msg]],
    ) -> List[dict]:
        """Format the input messages into the format required by the Kuafu Chat API.

        Args:
            args (`Union[Msg, Sequence[Msg]]`):
                The input arguments to be formatted, where each argument
                should be a `Msg` object, or a list of `Msg` objects.

        Returns:
            `List[dict]`:
                The formatted messages in the format that Kuafu Chat API requires.
        """
        messages = []

        for arg in args:
            if arg is None:
                continue
            if isinstance(arg, Msg):
                messages.append(
                    {"role": arg.role.lower(), "content": _convert_to_str(arg.content)}
                )
            elif isinstance(arg, list):
                for sub_arg in arg:
                    if isinstance(sub_arg, Msg):
                        messages.append(
                            {"role": sub_arg.role.lower(), "content": _convert_to_str(sub_arg.content)}
                        )
                    else:
                        raise TypeError(
                            f"The input should be a Msg object or a list of Msg objects, got {type(sub_arg)}."
                        )
            else:
                raise TypeError(
                    f"The input should be a Msg object or a list of Msg objects, got {type(arg)}."
                )

        return messages