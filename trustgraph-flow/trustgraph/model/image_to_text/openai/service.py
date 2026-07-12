
"""
Simple image-to-text service, describes images using the OpenAI vision
API.  Input is base64-encoded image, MIME type and prompt, output is
image description.
"""

from openai import OpenAI, RateLimitError, InternalServerError
import os
import logging

from .... exceptions import TooManyRequests, LlmError
from .... base import ImageToTextService, ImageDescriptionResult

# Module logger
logger = logging.getLogger(__name__)

default_ident = "image-to-text"

default_model = 'gpt-5-mini'
default_max_output = 4096
default_api_key = os.getenv("OPENAI_TOKEN")
default_base_url = os.getenv("OPENAI_BASE_URL")
default_prompt = 'Describe this image'

if default_base_url is None or default_base_url == "":
    default_base_url = "https://api.openai.com/v1"

class Processor(ImageToTextService):

    def __init__(self, **params):

        model = params.get("model", default_model)
        api_key = params.get("api_key", default_api_key)
        base_url = params.get("url", default_base_url)
        max_output = params.get("max_output", default_max_output)

        if not api_key:
            api_key = "not-set"

        super(Processor, self).__init__(
            **params | {
                "model": model,
                "max_output": max_output,
                "base_url": base_url,
            }
        )

        self.default_model = model
        self.max_output = max_output

        if base_url:
            self.openai = OpenAI(base_url=base_url, api_key=api_key)
        else:
            self.openai = OpenAI(api_key=api_key)

        logger.info("OpenAI image-to-text service initialized")

    async def describe_image(
        self, image, mime_type, prompt, system, model=None,
    ):

        model_name = model or self.default_model

        logger.debug(f"Using model: {model_name}")

        if not prompt:
            prompt = default_prompt

        if system:
            prompt = system + "\n\n" + prompt

        try:

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image}"
                            }
                        }
                    ]
                }
            ]

            resp = self.openai.chat.completions.create(
                model=model_name,
                messages=messages,
                max_completion_tokens=self.max_output,
            )

            inputtokens = resp.usage.prompt_tokens
            outputtokens = resp.usage.completion_tokens

            content = resp.choices[0].message.content

            logger.debug(f"Image description: {content}")
            logger.info(f"Input Tokens: {inputtokens}")
            logger.info(f"Output Tokens: {outputtokens}")

            resp = ImageDescriptionResult(
                text = content,
                in_token = inputtokens,
                out_token = outputtokens,
                model = model_name
            )

            return resp

        except RateLimitError as e:
            try:
                body = getattr(e, 'body', {})
                if isinstance(body, dict):
                    code = body.get('error', {}).get('code')
                    if code in ('insufficient_quota', 'invalid_api_key', 'account_deactivated'):
                        raise RuntimeError(f"OpenAI unrecoverable error: {code} - {body['error'].get('message', '')}")
            except (ValueError, KeyError, TypeError, AttributeError):
                pass
            # Leave rate limit retries to the base handler
            raise TooManyRequests()

        except InternalServerError:
            # Treat 503 as a retryable LlmError
            raise LlmError()

        except Exception as e:

            # Apart from rate limits, treat all exceptions as unrecoverable

            logger.error(f"OpenAI image-to-text exception ({type(e).__name__}): {e}", exc_info=True)
            raise e

    @staticmethod
    def add_args(parser):

        ImageToTextService.add_args(parser)

        parser.add_argument(
            '-m', '--model',
            default=default_model,
            help=f'Vision model (default: {default_model})'
        )

        parser.add_argument(
            '-k', '--api-key',
            default=default_api_key,
            help=f'OpenAI API key'
        )

        parser.add_argument(
            '-u', '--url',
            default=default_base_url,
            help=f'OpenAI service base URL'
        )

        parser.add_argument(
            '-x', '--max-output',
            type=int,
            default=default_max_output,
            help=f'Vision model max output tokens (default: {default_max_output})'
        )

def run():

    Processor.launch(default_ident, __doc__)
