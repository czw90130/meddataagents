# -*- coding: utf-8 -*-
"""Model wrapper for Amazon Bedrock models"""
from typing import Union, Any, List, Sequence, Dict
import json

from loguru import logger

from agentscope.models import ModelWrapperBase, ModelResponse
from agentscope.message import Msg
from agentscope.utils.tools import _convert_to_str

try:
    import boto3
except ImportError:
    boto3 = None


class BedrockModelWrapper(ModelWrapperBase):
    """The model wrapper for Amazon Bedrock API."""

    model_type: str = "bedrock_chat"

    def __init__(
        self,
        config_name: str,
        model_name: str = None,
        ak: str = "",
        sk: str = "",
        region: str = "",
        client_args: dict = None,
        generate_args: dict = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Amazon Bedrock client.

        Args:
            config_name (`str`):
                The name of the model config.
            model_name (`str`, default `None`):
                The name of the model to use in Bedrock API.
            ak (`str`, default `""`):
                The access key id of the Bedrock API.
            sk (`str`, default `""`):
                The secret access key of the Bedrock API.
            region (`str`, default `""`):
                The AWS region for the Bedrock API.
            client_args (`dict`, default `None`):
                The extra keyword arguments to initialize the Bedrock client.
            generate_args (`dict`, default `None`):
                The extra keyword arguments used in Bedrock API generation,
                e.g. `temperature`, `max_tokens`.
        """
        self.anthropic_version = "bedrock-2023-05-31"
        model_list = {
            "claude3-opus": "anthropic.claude-3-opus-20240229-v1:0",
            "claude3-sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
            "claude3-haiku": "anthropic.claude-3-haiku-20240229-v1:0",
            "claude3.5-sonnet": "anthropic.claude-3-5-sonnet-20240620-v1:0",
        }

        if model_name is None or model_name not in model_list:
            model_name = "claude3-sonnet"
            logger.warning("model_name is not set, use claude3-sonnet instead.")
        self.modelId = model_list[model_name]

        super().__init__(config_name=config_name, model_name=model_name)

        self.generate_args = generate_args or {}

        if boto3 is None:
            raise ImportError(
                "Cannot find boto3 package, please install it by "
                "`pip install boto3`",
            )

        self.client = boto3.client(
            service_name='bedrock-runtime',
            aws_access_key_id=ak,
            aws_secret_access_key=sk,
            region_name=region,
            **(client_args or {}),
        )

        # Set the max length of Bedrock model
        self.max_length = 4096  # This might need to be adjusted based on the specific model

    def __call__(
        self,
        messages: list,
        **kwargs: Any,
    ) -> ModelResponse:
        """Process a list of messages and generate a response using the Bedrock API.

        Args:
            messages (`list`):
                A list of messages to process.
            **kwargs (`Any`):
                Additional keyword arguments for the Bedrock API call.

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
                f"Bedrock `messages` field expected type `list`, "
                f"got `{type(messages)}` instead.",
            )
        if not all("role" in msg and "content" in msg for msg in messages):
            raise ValueError(
                "Each message in the 'messages' list must contain a 'role' "
                "and 'content' key for Bedrock API.",
            )

        # Prepare the request body
        body = json.dumps(
            {
                "anthropic_version": self.anthropic_version,
                "max_tokens": self.max_length,
                "messages": messages,
            }
        )

        try:
            # Call the Bedrock API
            response = self.client.invoke_model(
                body=body,
                modelId=self.modelId,
                **kwargs,
            )
            result = json.loads(response.get("body").read())
        except Exception as e:
            logger.error(f"Error calling Bedrock API: {e}")
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
        token_prompt = result["usage"]["input_tokens"]
        token_response = result["usage"]["output_tokens"]
        self.monitor.update_text_and_embedding_tokens(
            model_name=self.model_name,
            prompt_tokens=token_prompt,
            completion_tokens=token_response,
        )

        # Process and return the response
        output_list = result.get("content", [])
        output_text = "".join(output["text"] for output in output_list)

        return ModelResponse(
            text=output_text,
            raw=result,
        )

    def format(
        self,
        *args: Union[Msg, Sequence[Msg]],
    ) -> List[dict]:
        """Format the input messages into the format required by the Bedrock Chat API.

        Args:
            args (`Union[Msg, Sequence[Msg]]`):
                The input arguments to be formatted, where each argument
                should be a `Msg` object, or a list of `Msg` objects.

        Returns:
            `List[dict]`:
                The formatted messages in the format that Bedrock Chat API requires.
        """
        messages = [{"role": "user", "content": []}]

        for arg in args:
            if arg is None:
                continue
            if isinstance(arg, Msg):
                messages[0]["content"].append(
                    {"type": "text", "text": f"[{arg.role}]{arg.name}:\n{_convert_to_str(arg.content)}\n"}
                )
            elif isinstance(arg, list):
                for sub_arg in arg:
                    if isinstance(sub_arg, Msg):
                        messages[0]["content"].append(
                            {"type": "text", "text": f"[{sub_arg.role}]{sub_arg.name}:\n{_convert_to_str(sub_arg.content)}\n"}
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