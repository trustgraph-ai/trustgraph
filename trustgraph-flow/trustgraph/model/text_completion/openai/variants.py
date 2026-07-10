"""
OpenAI API variant profiles.

Different providers expose OpenAI-compatible APIs with subtle differences
in parameter names, thinking/reasoning support, and temperature handling.
Each variant encapsulates those quirks so the processor doesn't need
provider-specific conditionals.
"""

import re
import logging

logger = logging.getLogger(__name__)


class Variant:
    """Base variant — defines the interface all variants implement."""

    name = None
    token_param = "max_completion_tokens"
    temperature_with_thinking = False

    def completion_kwargs(self, max_output, temperature, thinking):
        """Build provider-specific kwargs for chat.completions.create().

        Parameters
        ----------
        max_output : int
            Configured max output tokens.
        temperature : float
            Configured temperature.
        thinking : str
            Thinking effort level: "off", "low", "medium", "high".

        Returns
        -------
        dict
            Extra kwargs to spread into the API call.
        """
        kwargs = {self.token_param: max_output}

        if thinking != "off":
            kwargs.update(self.thinking_kwargs(thinking))
            if not self.temperature_with_thinking:
                kwargs["temperature"] = 1.0
            else:
                kwargs["temperature"] = temperature
        else:
            kwargs["temperature"] = temperature

        return kwargs

    def thinking_kwargs(self, effort):
        """Return kwargs to enable thinking at the given effort level."""
        return {}

    def extract_thinking(self, message):
        """Extract thinking/reasoning content from a response message."""
        return getattr(message, "reasoning_content", None)

    def extract_thinking_stream(self, delta):
        """Extract thinking content from a streaming delta."""
        return getattr(delta, "reasoning_content", None)

    def supports_top_level_array(self):
        """Whether this provider accepts a top-level array JSON schema."""
        return True

    def create_completion(self, client, model, messages, **kwargs):
        """Call the completions API. Override for non-standard SDKs."""
        return client.chat.completions.create(
            model=model, messages=messages, **kwargs,
        )

    async def create_completion_stream(self, client, model, messages, **kwargs):
        """Call the streaming completions API. Override for non-standard SDKs."""
        for chunk in client.chat.completions.create(
            model=model, messages=messages, stream=True,
            stream_options={"include_usage": True}, **kwargs,
        ):
            yield chunk


class OpenAIVariant(Variant):
    """Standard OpenAI API (GPT-4o, o1, o3, etc.)."""

    name = "openai"
    token_param = "max_completion_tokens"
    temperature_with_thinking = False

    def supports_top_level_array(self):
        return False

    def thinking_kwargs(self, effort):
        return {"reasoning_effort": effort}


class DeepSeekVariant(Variant):
    """DeepSeek API (R1, V3, etc.)."""

    name = "deepseek"
    token_param = "max_completion_tokens"
    temperature_with_thinking = True

    def completion_kwargs(self, max_output, temperature, thinking):
        enabled = "enabled" if thinking != "off" else "disabled"
        kwargs = {
            self.token_param: max_output,
            "temperature": temperature,
            "extra_body": {
                "thinking": {"type": enabled},
            },
        }
        return kwargs

    def thinking_kwargs(self, effort):
        return {}


class DashScopeVariant(Variant):
    """Alibaba Cloud DashScope API (Qwen models)."""

    name = "dashscope"
    token_param = "max_completion_tokens"
    temperature_with_thinking = True

    def completion_kwargs(self, max_output, temperature, thinking):
        enabled = thinking != "off"
        return {
            self.token_param: max_output,
            "temperature": temperature,
            "extra_body": {
                "enable_thinking": enabled,
            },
        }

    def thinking_kwargs(self, effort):
        return {}


class QwenVariant(DashScopeVariant):
    """Qwen — alias for DashScope."""

    name = "qwen"


class MistralVariant(Variant):
    """Mistral API (Mistral Large, etc.)."""

    name = "mistral"
    token_param = "max_tokens"
    temperature_with_thinking = False

    def thinking_kwargs(self, effort):
        return {"reasoning_effort": effort}


class GlmVariant(Variant):
    """GLM / Zhipu AI API (GLM-4, GLM-4.7, etc.)."""

    name = "glm"
    token_param = "max_tokens"
    temperature_with_thinking = True

    def completion_kwargs(self, max_output, temperature, thinking):
        enabled = "enabled" if thinking != "off" else "disabled"
        kwargs = {
            self.token_param: max_output,
            "temperature": temperature,
            "extra_body": {
                "thinking": {"type": enabled},
            },
        }
        return kwargs

    def thinking_kwargs(self, effort):
        return {}


class LlamaVariant(Variant):
    """Llama models via OpenAI-compatible servers (vLLM, Ollama, etc.).

    Thinking is typically always-on or always-off depending on the model.
    When present, thinking appears inline as <think>...</think> tags.
    """

    name = "llama"
    token_param = "max_tokens"
    temperature_with_thinking = True

    def thinking_kwargs(self, effort):
        return {}

    def extract_thinking(self, message):
        content = message.content or ""
        match = re.search(r"<think>(.*?)</think>", content, re.DOTALL)
        return match.group(1).strip() if match else None

    def extract_content(self, message):
        """Strip think tags from visible content."""
        content = message.content or ""
        return re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()


class VllmVariant(LlamaVariant):
    """vLLM via OpenAI-compatible API. Supports full structured output."""

    name = "vllm"


VARIANTS = {
    "openai": OpenAIVariant,
    "deepseek": DeepSeekVariant,
    "qwen": QwenVariant,
    "mistral": MistralVariant,
    "dashscope": DashScopeVariant,
    "glm": GlmVariant,
    "llama": LlamaVariant,
    "vllm": VllmVariant,
}

DEFAULT_VARIANT = "openai"


def get_variant(name):
    """Look up a variant by name, raising ValueError if unknown."""
    cls = VARIANTS.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown variant {name!r}. "
            f"Available: {', '.join(sorted(VARIANTS))}"
        )
    return cls()
