
"""
ONNX inference engine for Laya decision scoring.
Replaces the torch-based laya.Router with pure ONNX Runtime inference.
"""

import json
import math
import logging
from typing import Any, Dict, List, Optional, Union

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer
from huggingface_hub import hf_hub_download

logger = logging.getLogger(__name__)

DEFAULT_REPO = "onnx-community/laya-multilingual-ONNX"

QTYPES = {"choice": 0, "score": 1, "noul": 2}
QTYPE_NAMES = {v: k for k, v in QTYPES.items()}
TEMP_MIN, TEMP_MAX = 0.5, 5.0


def _clamp_temperature(t):
    try:
        t = float(t)
    except (TypeError, ValueError):
        return 1.0
    if t != t or t in (float("inf"), float("-inf")):
        return 1.0
    return min(TEMP_MAX, max(TEMP_MIN, t))


def _temp_bucket(qtype, k):
    size = "2" if k <= 2 else "3-5" if k <= 5 else "6-10" if k <= 10 else "11+"
    return "%s:%s" % (QTYPE_NAMES[qtype], size)


def _confidence_from_probs(p, k):
    if k < 2:
        return 1.0
    p = p[:k]
    ent = -(p * np.log(np.clip(p, 1e-12, 1.0))).sum()
    return float(np.clip(1.0 - ent / math.log(k), 0.0, 1.0))


def _serialize_state(state):
    if isinstance(state, str):
        return state
    return json.dumps(state, ensure_ascii=False)


def _render_criterion(value):
    if isinstance(value, str):
        return value
    return json.dumps(
        value, ensure_ascii=False, separators=(", ", ": "), default=str,
    )


def _render_options(q):
    t, crit = q["t"], q.get("crit")
    if t == "choice":
        return [
            k if v is None or v == ""
            else "%s: %s" % (k, _render_criterion(v))
            for k, v in crit.items()
        ]
    if t == "score":
        return [
            "level %d: %s" % (i, _render_criterion(c))
            for i, c in enumerate(crit)
        ]
    crit = crit or {}
    false_crit, true_crit = crit.get("false"), crit.get("true")
    return [
        "false: " + (
            _render_criterion(false_crit)
            if false_crit not in (None, "")
            else "no, the statement does not hold"
        ),
        "true: " + (
            _render_criterion(true_crit)
            if true_crit not in (None, "")
            else "yes, the statement holds"
        ),
    ]


def _to_internal(qdef):
    t = qdef["type"]
    crit = qdef.get("criteria")
    if t == "choice" and isinstance(crit, list):
        crit = {c: None for c in crit}
    ins = qdef["instructions"]
    if not isinstance(ins, str):
        ins = json.dumps(ins)
    return {"t": t, "ins": ins, "crit": crit}


def _build_sequence(
    tokenizer, state, q, mask_token, mask_id, cls_id, sep_id,
    max_len=512, head_max_len=192,
):
    opts = _render_options(q)
    ins = str(q["ins"]).replace(mask_token, " ")

    head_text = "%s question: %s" % (q["t"], ins)
    head_ids = tokenizer.encode(head_text, add_special_tokens=False).ids

    opt_ids = []
    for opt in opts:
        opt_text = " " + opt.replace(mask_token, " ")
        opt_tokens = tokenizer.encode(
            opt_text, add_special_tokens=False,
        ).ids[:48]
        opt_ids.append([mask_id] + opt_tokens)

    opt_budget = head_max_len - sum(len(o) for o in opt_ids)
    if opt_budget < 16:
        per = max(4, (head_max_len - 16) // max(1, len(opt_ids)))
        opt_ids = [o[:per] for o in opt_ids]
        opt_budget = head_max_len - sum(len(o) for o in opt_ids)
    head_ids = head_ids[:max(8, opt_budget)]

    ids = [cls_id] + head_ids + [sep_id]
    markers = []
    for o in opt_ids:
        markers.append(len(ids))
        ids.extend(o)
    ids.append(sep_id)

    room = max(0, max_len - len(ids) - 1)
    state_text = _serialize_state(state).replace(mask_token, " ")
    state_ids = tokenizer.encode(
        state_text, add_special_tokens=False,
    ).ids[:room]
    ids = ids + state_ids + [sep_id]

    return ids[:max_len], [m for m in markers if m < max_len]


class OnnxEngine:

    def __init__(
        self,
        repo_id: str = DEFAULT_REPO,
        local_dir: Optional[str] = None,
        variant: str = "fp32",
    ):
        local_dir = local_dir or "/opt/models/laya"

        onnx_file = (
            "onnx/model_fp16.onnx" if variant == "fp16"
            else "onnx/model.onnx"
        )
        data_file = onnx_file + "_data"

        logger.info("Downloading Laya ONNX model from %s ...", repo_id)
        model_path = hf_hub_download(
            repo_id=repo_id, filename=onnx_file, local_dir=local_dir,
        )
        hf_hub_download(
            repo_id=repo_id, filename=data_file, local_dir=local_dir,
        )
        tokenizer_path = hf_hub_download(
            repo_id=repo_id, filename="tokenizer.json", local_dir=local_dir,
        )
        config_path = hf_hub_download(
            repo_id=repo_id, filename="config.json", local_dir=local_dir,
        )

        logger.info("Loading ONNX session...")
        self.session = ort.InferenceSession(
            model_path, providers=["CPUExecutionProvider"],
        )
        self.tokenizer = Tokenizer.from_file(tokenizer_path)

        with open(config_path) as f:
            config = json.load(f)

        self.cls_id = config["cls_token_id"]
        self.sep_id = config["sep_token_id"]
        self.mask_id = config["mask_token_id"]
        self.pad_id = config["pad_token_id"]
        self.mask_token = (
            self.tokenizer.id_to_token(self.mask_id) or "<mask>"
        )

        laya_cfg = config.get("laya", {})
        self.max_len = laya_cfg.get("max_len", 512)
        self.head_max_len = laya_cfg.get("head_max_len", 192)

        temp_raw = laya_cfg.get("temperature", [1.0, 1.0, 1.0])
        temp_by_opts_raw = laya_cfg.get("temperature_by_options", {})
        self.temperatures = [_clamp_temperature(t) for t in temp_raw]
        self.temp_by_options = {
            k: _clamp_temperature(v) for k, v in temp_by_opts_raw.items()
        }

        logger.info("Laya ONNX engine loaded (variant=%s)", variant)

    def predict(
        self,
        state: Union[str, dict, list],
        questions: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:

        qids = list(questions.keys())
        items: List[Dict] = []

        for qid in qids:
            q = _to_internal(questions[qid])
            seq, markers = _build_sequence(
                self.tokenizer, state, q,
                self.mask_token, self.mask_id, self.cls_id, self.sep_id,
                max_len=self.max_len, head_max_len=self.head_max_len,
            )
            opts = _render_options(q)
            if len(markers) != len(opts):
                raise ValueError(
                    "Question %r options exceed head_max_len=%d"
                    % (qid, self.head_max_len)
                )
            items.append({
                "ids": seq, "markers": markers,
                "qtype": QTYPES[q["t"]], "q": q,
            })

        n = len(items)
        max_seq = max(len(it["ids"]) for it in items)
        max_k = max(len(it["markers"]) for it in items)

        input_ids = np.full((n, max_seq), self.pad_id, dtype=np.int64)
        attention_mask = np.zeros((n, max_seq), dtype=np.int64)
        marker_pos = np.zeros((n, max_k), dtype=np.int64)
        marker_mask = np.zeros((n, max_k), dtype=bool)
        qtype = np.array([it["qtype"] for it in items], dtype=np.int64)

        for i, it in enumerate(items):
            sl = len(it["ids"])
            input_ids[i, :sl] = it["ids"]
            attention_mask[i, :sl] = 1
            k = len(it["markers"])
            marker_pos[i, :k] = it["markers"]
            marker_mask[i, :k] = True

        outputs = self.session.run(None, {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "marker_pos": marker_pos,
            "marker_mask": marker_mask,
            "qtype": qtype,
        })

        logits = outputs[0]
        act_out = outputs[1]

        act_probs = np.exp(act_out - act_out.max(axis=-1, keepdims=True))
        act_probs = act_probs / act_probs.sum(axis=-1, keepdims=True)

        answers = {}

        for r, qid in enumerate(qids):
            q = items[r]["q"]
            k = len(items[r]["markers"])
            qt = items[r]["qtype"]

            bucket = _temp_bucket(qt, k)
            t_scale = self.temp_by_options.get(
                bucket, self.temperatures[qt],
            )

            z = logits[r, :k] / t_scale
            p = np.exp(z - z.max())
            p = p / p.sum()

            conf = round(_confidence_from_probs(p, k), 4)
            act = {"act_probability": round(float(act_probs[r, 0]), 4)}

            if q["t"] == "choice":
                keys = list(q["crit"].keys())
                answers[qid] = {
                    "type": "choice",
                    "choice": keys[int(p.argmax())],
                    "probabilities": {
                        kk: round(float(v), 4)
                        for kk, v in zip(keys, p)
                    },
                    "confidence": conf,
                    "action": act,
                }

            elif q["t"] == "score":
                exp_score = float((np.arange(k) * p).sum())
                answers[qid] = {
                    "type": "score",
                    "score": round(exp_score, 4),
                    "legend": {
                        str(i): c for i, c in enumerate(q["crit"])
                    },
                    "probabilities": {
                        str(i): round(float(v), 4)
                        for i, v in enumerate(p)
                    },
                    "confidence": conf,
                    "action": act,
                }

            else:
                answers[qid] = {
                    "type": "noul",
                    "noul": round(float(p[1]), 4),
                    "confidence": round(
                        max(float(p[1]), 1.0 - float(p[1])), 4,
                    ),
                    "action": act,
                }

        return {
            "model": "laya-multilingual-onnx",
            "answers": answers,
            "routing": {"model": "laya-multilingual-onnx"},
            "usage": {
                "input_tokens": int(attention_mask.sum()),
                "output_tokens": 0,
            },
        }
