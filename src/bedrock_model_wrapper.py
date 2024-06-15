from typing import Union, Any, List, Sequence, Dict
from agentscope.models import ModelWrapperBase, ModelResponse
from agentscope.message import MessageBase
from agentscope.utils.tools import _convert_to_str
import json
from loguru import logger

import boto3

class BedrockCheckModelWrapper(ModelWrapperBase):
    model_type: str = "bedrock_chat"

    def __init__(
        self,
        config_name,
        model_name = None,
        ak: str = "",
        sk: str = "",
        region: str = "",
        client_args: dict = {},
        generate_args = None,
        **kwargs: Any
    ):
        """Initialize the bedrock client.

        Args:
            config_name (`str`):
                The name of the model config.
            model_name (`str`, default `None`):
                The name of the model to use in bedrock API.
            ak (`str`, default `None`):
                The access key id of the bedrock API.
            sk (`str`, default `None`):
                The secret access key of the bedrock API.
            client_args (`dict`, default `None`):
                The extra keyword arguments to initialize the bedrock client.
            generate_args (`dict`, default `None`):
                The extra keyword arguments used in bedrock api generation,
                e.g. `temperature`, `seed`.
            budget (`float`, default `None`):
                The total budget using this model. Set to `None` means no
                limit.
        """
        self.anthropic_version ="bedrock-2023-05-31"
        model_list = {
            "claude3-opus":"anthropic.claude-3-opus-20240229-v1:0",
            "claude3-sonnet":"anthropic.claude-3-sonnet-20240229-v1:0",
            "claude3-haiku":"anthropic.claude-3-haiku-20240229-v1:0",
        }
        
        if model_name is None or model_name not in model_list:
            model_name = model_list['claude3-sonnet']
            logger.warning("model_name is not set, use claude3-sonnet instead.")
        self.modelId = model_list[model_name]
        # 初始化模型实例
        super().__init__(config_name=config_name)
        # ...
        
        self.model_name = model_name
        
        self.max_length = 2048
        self.generate_args = generate_args or {}
        
        self.client = boto3.client(
            service_name='bedrock-runtime',
            aws_access_key_id=ak,
            aws_secret_access_key=sk,
            region_name=region,
            **(client_args or {}),
        )
        
        
        
        # Set monitor accordingly
        self._register_default_metrics()
        
    def _register_default_metrics(self) -> None:
        # Set monitor accordingly
        # TODO: set quota to the following metrics
        self.monitor.register(
            self._metric("call_counter"),
            metric_unit="times",
        )
        self.monitor.register(
            self._metric("prompt_tokens"),
            metric_unit="token",
        )
        self.monitor.register(
            self._metric("completion_tokens"),
            metric_unit="token",
        )
        self.monitor.register(
            self._metric("total_tokens"),
            metric_unit="token",
        )

    def __call__(
        self,
        messages: list,
        **kwargs: Any,
    ) -> ModelResponse:
        # 调用模型实例
        # ...
        # step1: prepare keyword arguments
        kwargs = {**self.generate_args, **kwargs}
        
        # step2: checking messages
        if not isinstance(messages, list):
             raise ValueError(
                "bedrock `messages` field expected type `list`, "
                f"got `{type(messages)}` instead.",
            )
        if not all("role" in msg and "content" in msg for msg in messages):
            raise ValueError(
                "Each message in the 'messages' list must contain a 'role' "
                "and 'content' key for bedrock API.",
            )
            
        # step3: forward to generate response
        body = json.dumps(
            {
                "anthropic_version": self.anthropic_version,
                "max_tokens": self.max_length,
                "messages": messages,
            }
        )
        
        response = self.client.invoke_model(
            body=body,
            modelId=self.modelId,
            **kwargs,
        )
        result = json.loads(response.get("body").read())
        
        # step4: record the api invocation if needed
        self._save_model_invocation(
            arguments={
                "model": self.model_name,
                "messages": messages,
                **kwargs,
            },
            response=result,
        )
        
        # step5: update monitor accordingly
        token_prompt = result["usage"]["input_tokens"]
        token_response = result["usage"]["output_tokens"]
        self.update_monitor(
            call_counter=1,
            completion_tokens=token_response,
            prompt_tokens=token_prompt,
            total_tokens=token_prompt + token_response,
        )
        
        # step6: return response
        output_list = result.get("content", [])
        output_text = ""
        for output in output_list:
            output_text += output['text'] + "\n"
        return ModelResponse(
            text=output_text[:-1],
            raw=result,
        )

    def format(
        self,
        *args: Union[MessageBase, Sequence[MessageBase]],
    ) -> List[dict]:
        """Format the input string and dictionary into the format that
        bedrock Chat API required.

        Args:
            args (`Union[MessageBase, Sequence[MessageBase]]`):
                The input arguments to be formatted, where each argument
                should be a `Msg` object, or a list of `Msg` objects.
                In distribution, placeholder is also allowed.

        Returns:
            `List[dict]`:
                The formatted messages in the format that bedrock Chat API
                required.
        """
        messages = [{"role": "user", "content": []}]

        for arg in args:
            if arg is None:
                continue
            if isinstance(arg, MessageBase):
                # TODO: add _format_msg_with_url to process images
                messages[0]["content"].append(
                    {"type": "text", "text": f"[{arg.role}]{arg.name}:\n{_convert_to_str(arg.content)}\n"}
                )

            elif isinstance(arg, list):
                for sub_arg in arg:
                    if isinstance(sub_arg, MessageBase):
                        messages[0]["content"].append(
                            {"type": "text", "text": f"[{sub_arg.role}]{sub_arg.name}:\n{_convert_to_str(sub_arg.content)}\n"}
                        )
                    else:
                        raise TypeError(
                            f"The input should be a Msg object or alist "
                        )
            else:
                raise TypeError(
                    f"The input should be a Msg object or a list "
                    f"of Msg objects, got {type(arg)}.",
                )
        return messages
        
if "__main__" == __name__:
    bedrock = boto3.client(
            service_name='bedrock-runtime',
            aws_access_key_id='',
            aws_secret_access_key='',
            region_name=''
        )

    prompt = "美国人的预期寿命是多少？"
    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}],
                }
            ],
        }
    
    )

    modelId = 'anthropic.claude-3-opus-20240229-v1:0'

    response = bedrock.invoke_model(
        body=body,
        modelId=modelId,
    )

    # Process and print the response
    result = json.loads(response.get("body").read())
    input_tokens = result["usage"]["input_tokens"]
    output_tokens = result["usage"]["output_tokens"]
    output_list = result.get("content", [])

    print("Invocation details:")
    print(f"- The input length is {input_tokens} tokens.")
    print(f"- The output length is {output_tokens} tokens.")

    print(f"- The model returned {len(output_list)} response(s):")
    for output in output_list:
        print(output["text"])