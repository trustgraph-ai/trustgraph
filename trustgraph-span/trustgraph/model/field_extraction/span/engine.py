
"""
ONNX inference engine for BIO span extraction.
Loads a span-extraction model from HuggingFace Hub and runs
instruction-based field extraction using BIO tagging.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer
from huggingface_hub import hf_hub_download

logger = logging.getLogger(__name__)

DEFAULT_REPO = "tasksource/UltraBERT-150M-clairic-extraction"
DEFAULT_MAX_LENGTH = 512

O, B, I = 0, 1, 2


def _serialize_state(state):
    if isinstance(state, str):
        return state
    return json.dumps(state, ensure_ascii=False)


def _decode_spans(text, tags, offsets, seq_ids):
    """Extract text spans from BIO tags.

    Only tokens in the text sequence (seq_id=1) are considered.
    """
    spans = []
    start = None

    for i, tag in enumerate(tags):
        in_text = (seq_ids[i] == 1)

        if start is not None and (not in_text or tag != I):
            char_start = offsets[start][0]
            char_end = offsets[i - 1][1]
            span = text[char_start:char_end].strip().rstrip(",;:")
            if span:
                spans.append(span)
            start = None

        if in_text and tag in (B, I) and start is None:
            start = i

    if start is not None:
        char_start = offsets[start][0]
        last = len(tags) - 1
        while last > start and seq_ids[last] != 1:
            last -= 1
        char_end = offsets[last][1]
        span = text[char_start:char_end].strip().rstrip(",;:")
        if span:
            spans.append(span)

    return spans


class OnnxEngine:

    def __init__(
        self,
        repo_id: str = DEFAULT_REPO,
        local_dir: Optional[str] = None,
        max_length: int = DEFAULT_MAX_LENGTH,
    ):
        local_dir = local_dir or "/opt/models/span-extraction"

        logger.info(
            "Downloading span-extraction model from %s ...", repo_id,
        )
        model_path = hf_hub_download(
            repo_id=repo_id, filename="onnx/model_quantized.onnx",
            local_dir=local_dir,
        )
        tokenizer_path = hf_hub_download(
            repo_id=repo_id, filename="tokenizer.json",
            local_dir=local_dir,
        )

        logger.info("Loading ONNX session...")
        self.session = ort.InferenceSession(
            model_path, providers=["CPUExecutionProvider"],
        )
        self.tokenizer = Tokenizer.from_file(tokenizer_path)
        self.tokenizer.no_padding()

        self.max_length = max_length
        self.repo_id = repo_id

        logger.info(
            "Span-extraction engine loaded (max_length=%d)", max_length,
        )

    def predict(
        self,
        state: Union[str, dict, list],
        fields: Dict[str, str],
    ) -> Dict[str, Any]:

        text = _serialize_state(state)

        field_names = list(fields.keys())
        instructions = list(fields.values())

        encodings = [
            self.tokenizer.encode(inst, text) for inst in instructions
        ]

        if self.max_length:
            for enc in encodings:
                enc.truncate(self.max_length)

        max_len = max(len(enc.ids) for enc in encodings)
        pad_id = 0

        all_input_ids = []
        all_attention_mask = []

        for enc in encodings:
            ids = list(enc.ids)
            pad_len = max_len - len(ids)
            all_input_ids.append(ids + [pad_id] * pad_len)
            all_attention_mask.append([1] * len(ids) + [0] * pad_len)

        input_ids = np.array(all_input_ids, dtype=np.int64)
        attention_mask = np.array(all_attention_mask, dtype=np.int64)

        outputs = self.session.run(None, {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
        })

        tags = outputs[0].argmax(axis=-1)

        answers = {}
        for i, name in enumerate(field_names):
            enc = encodings[i]
            n_tokens = len(enc.ids)
            answers[name] = _decode_spans(
                text,
                tags[i][:n_tokens].tolist(),
                enc.offsets,
                enc.sequence_ids,
            )

        return {
            "model": self.repo_id,
            "answers": answers,
        }
