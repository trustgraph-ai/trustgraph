
"""
Cloze model service. Auto-trains a masked language model from labeled
examples in config, and serves single-label classification with
confidence scores.
"""

import asyncio
import json
import logging
import torch
from functools import partial
from sklearn.model_selection import train_test_split
from dataclasses import dataclass, field

from trustgraph.schema import ClozeRequest, ClozeResponse, ClozeModelInfo, Error
from trustgraph.base import FlowProcessor, ConsumerSpec, ProducerSpec
from trustgraph.base import ParameterSpec

logger = logging.getLogger(__name__)

default_ident = "cloze"
default_model = "distilbert-base-uncased"

TRAINING_CONFIG_TYPE = "cloze-training"

DEFAULT_TEST_SPLIT = 0.2
DEFAULT_EPOCHS = 20
DEFAULT_BATCH_SIZE = 6
DEFAULT_BACKBONE_LR = 2e-5
DEFAULT_HEAD_LR = 1e-4


@dataclass
class TrainedModel:
    model: object = None
    tokenizer: object = None
    tool_tokens: list = field(default_factory=list)
    tool_token_ids: list = field(default_factory=list)
    device: object = None
    accuracy: float | None = None
    train_size: int = 0
    test_size: int = 0


class Processor(FlowProcessor):

    def __init__(self, **params):

        model = params.get("model", default_model)
        concurrency = params.get("concurrency", 2)

        super(Processor, self).__init__(
            **params | {
                "model": model,
                "concurrency": concurrency,
            }
        )

        self.base_model_name = model

        self.register_specification(
            ParameterSpec(name="model")
        )

        self.register_config_handler(
            self.on_training_config, types=[TRAINING_CONFIG_TYPE]
        )

        self.register_specification(
            ConsumerSpec(
                name="request",
                schema=ClozeRequest,
                handler=self.on_request,
                concurrency=concurrency,
            )
        )

        self.register_specification(
            ProducerSpec(
                name="response",
                schema=ClozeResponse,
            )
        )

        # Keyed by model instance name
        self.models = {}

        # Tracks models currently being trained: {(workspace, instance_name)}
        self.training = set()

    async def on_training_config(self, workspace, config, version):

        logger.info(
            f"Loading cloze training configuration version {version} "
            f"for workspace {workspace}"
        )

        if TRAINING_CONFIG_TYPE not in config:
            return

        training_configs = config[TRAINING_CONFIG_TYPE]

        if workspace not in self.models:
            self.models[workspace] = {}

        # Track which instances were updated
        updated = set()

        for instance_name, raw_value in training_configs.items():

            try:
                training_data = json.loads(raw_value)
                training_key = (workspace, instance_name)
                self.training.add(training_key)

                try:
                    loop = asyncio.get_event_loop()
                    trained = await loop.run_in_executor(
                        None,
                        partial(
                            self._train_model, instance_name, training_data,
                        ),
                    )
                finally:
                    self.training.discard(training_key)

                if trained is not None:
                    self.models[workspace][instance_name] = trained
                    updated.add(instance_name)
                    logger.info(
                        f"Model instance '{instance_name}' trained "
                        f"for workspace {workspace}"
                    )

            except Exception as e:
                logger.error(
                    f"Failed to train model instance '{instance_name}' "
                    f"for workspace {workspace}: {e}"
                )

        # Remove instances no longer in config
        for name in list(self.models[workspace].keys()):
            if name not in training_configs:
                del self.models[workspace][name]
                logger.info(
                    f"Removed model instance '{name}' "
                    f"for workspace {workspace}"
                )

    def _train_model(self, instance_name, training_data):

        from transformers import AutoTokenizer, AutoModelForMaskedLM
        from torch.utils.data import Dataset, DataLoader
        from torch.optim import AdamW

        labels = training_data.get("labels", [])
        if not labels:
            logger.warning(
                f"No labels in training data for '{instance_name}'"
            )
            return None

        min_accuracy = training_data.get("min-accuracy")
        test_split = training_data.get("test-split", DEFAULT_TEST_SPLIT)
        epochs = training_data.get("epochs", DEFAULT_EPOCHS)

        # Collect all examples and tool tokens
        tool_tokens = []
        seed_words = {}
        all_train_examples = []
        all_test_examples = []

        for label_def in labels:
            token = label_def["token"]
            seed = label_def["seed"]
            examples = label_def.get("examples", [])

            tool_tokens.append(token)
            seed_words[token] = seed

            if test_split > 0 and len(examples) >= 2:
                train_ex, test_ex = train_test_split(
                    examples, test_size=test_split, random_state=42
                )
            else:
                train_ex = examples
                test_ex = []

            for ex in train_ex:
                all_train_examples.append({"query": ex, "tool": token})
            for ex in test_ex:
                all_test_examples.append({"query": ex, "tool": token})

        if not all_train_examples:
            logger.warning(
                f"No training examples for '{instance_name}'"
            )
            return None

        logger.info(
            f"Training '{instance_name}': {len(all_train_examples)} train, "
            f"{len(all_test_examples)} test examples, "
            f"{len(tool_tokens)} labels"
        )

        # Load base model and tokenizer
        tokenizer = AutoTokenizer.from_pretrained(self.base_model_name)
        model = AutoModelForMaskedLM.from_pretrained(self.base_model_name)

        # Register tool tokens
        tokenizer.add_special_tokens(
            {"additional_special_tokens": tool_tokens}
        )
        model.resize_token_embeddings(len(tokenizer))

        # Warm-start embeddings from seed words
        with torch.no_grad():
            input_embeddings = model.get_input_embeddings().weight
            output_embeddings = (
                model.get_output_embeddings().weight
                if model.get_output_embeddings() is not None
                else input_embeddings
            )

            for tool_token, base_word in seed_words.items():
                tool_id = tokenizer.convert_tokens_to_ids(tool_token)
                base_id = tokenizer.convert_tokens_to_ids(base_word)

                input_embeddings[tool_id] = (
                    input_embeddings[base_id].clone()
                )
                if output_embeddings is not input_embeddings:
                    output_embeddings[tool_id] = (
                        output_embeddings[base_id].clone()
                    )

        # Build datasets
        class ClozeDataset(Dataset):
            def __init__(self, data, tokenizer, max_length=48):
                self.data = data
                self.tokenizer = tokenizer
                self.max_length = max_length

            def __len__(self):
                return len(self.data)

            def __getitem__(self, idx):
                item = self.data[idx]
                prompt = (
                    f"Query: {item['query']} "
                    f"Tool: {self.tokenizer.mask_token}"
                )

                encoding = self.tokenizer(
                    prompt,
                    padding="max_length",
                    truncation=True,
                    max_length=self.max_length,
                    return_tensors="pt"
                )

                input_ids = encoding["input_ids"].squeeze(0)
                attention_mask = encoding["attention_mask"].squeeze(0)

                labels = torch.full_like(input_ids, -100)
                mask_positions = (
                    input_ids == self.tokenizer.mask_token_id
                ).nonzero(as_tuple=True)[0]

                target_token_id = self.tokenizer.convert_tokens_to_ids(
                    item["tool"]
                )
                labels[mask_positions[0]] = target_token_id

                return {
                    "input_ids": input_ids,
                    "attention_mask": attention_mask,
                    "labels": labels,
                }

        device = torch.device(
            "cuda" if torch.cuda.is_available()
            else (
                "mps" if torch.backends.mps.is_available()
                else "cpu"
            )
        )

        model.to(device)

        train_dataset = ClozeDataset(all_train_examples, tokenizer)
        train_loader = DataLoader(
            train_dataset, batch_size=DEFAULT_BATCH_SIZE, shuffle=True
        )

        # Differential learning rates
        backbone_params = [
            p for n, p in model.named_parameters()
            if "vocab" not in n and "embeddings" not in n
        ]
        head_params = [
            p for n, p in model.named_parameters()
            if "vocab" in n or "embeddings" in n
        ]

        optimizer = AdamW([
            {
                "params": backbone_params,
                "lr": DEFAULT_BACKBONE_LR,
                "weight_decay": 0.01,
            },
            {
                "params": head_params,
                "lr": DEFAULT_HEAD_LR,
                "weight_decay": 0.01,
            },
        ])

        # Training loop
        model.train()
        for epoch in range(1, epochs + 1):
            total_loss = 0.0
            for batch in train_loader:
                optimizer.zero_grad()

                input_ids = batch["input_ids"].to(device)
                attention_mask = batch["attention_mask"].to(device)
                labels = batch["labels"].to(device)

                outputs = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels,
                )
                loss = outputs.loss

                loss.backward()
                optimizer.step()
                total_loss += loss.item()

            avg_loss = total_loss / len(train_loader)
            if epoch % 10 == 0 or epoch == 1:
                logger.info(
                    f"  [{instance_name}] Epoch {epoch:02d}/"
                    f"{epochs:02d} - Loss: {avg_loss:.4f}"
                )

        # Evaluate if we have test data
        tool_token_ids = [
            tokenizer.convert_tokens_to_ids(t) for t in tool_tokens
        ]

        accuracy = None

        if all_test_examples:
            model.eval()
            correct = 0

            with torch.no_grad():
                for item in all_test_examples:
                    prompt = (
                        f"Query: {item['query']} "
                        f"Tool: {tokenizer.mask_token}"
                    )
                    inputs = tokenizer(
                        prompt, return_tensors="pt"
                    ).to(device)

                    outputs = model(**inputs)
                    logits = outputs.logits

                    mask_idx = (
                        inputs["input_ids"] == tokenizer.mask_token_id
                    ).nonzero(as_tuple=True)[1][0]
                    mask_logits = logits[0, mask_idx, :]

                    candidate_logits = mask_logits[tool_token_ids]
                    best_tool_idx = torch.argmax(candidate_logits).item()
                    best_tool_token = tool_tokens[best_tool_idx]

                    if best_tool_token == item["tool"]:
                        correct += 1

            accuracy = correct / len(all_test_examples)
            logger.info(
                f"  [{instance_name}] Test accuracy: "
                f"{correct}/{len(all_test_examples)} ({accuracy:.1%})"
            )

            if min_accuracy is not None and accuracy < min_accuracy:
                logger.error(
                    f"  [{instance_name}] Accuracy {accuracy:.1%} below "
                    f"minimum threshold {min_accuracy:.1%}, "
                    f"rejecting model"
                )
                return None

        return TrainedModel(
            model=model,
            tokenizer=tokenizer,
            tool_tokens=tool_tokens,
            tool_token_ids=tool_token_ids,
            device=device,
            accuracy=accuracy,
            train_size=len(all_train_examples),
            test_size=len(all_test_examples),
        )

    async def on_request(self, msg, consumer, flow):

        request = msg.value()
        id = msg.properties()["id"]
        producer = flow("response")

        workspace = flow.workspace
        operation = request.operation or "predict"

        if operation == "list-models":
            response = self._list_models(workspace)
            await producer.send(response, properties={"id": id})
            return

        instance_name = request.model
        query = request.query

        ws_models = self.models.get(workspace, {})
        trained = ws_models.get(instance_name)

        if trained is None:
            if (workspace, instance_name) in self.training:
                error_type = "model-training"
                error_message = (
                    f"Model instance '{instance_name}' is currently "
                    f"training in workspace '{workspace}'"
                )
            else:
                error_type = "model-not-found"
                error_message = (
                    f"No trained model instance '{instance_name}' "
                    f"in workspace '{workspace}'"
                )

            response = ClozeResponse(
                error=Error(
                    type=error_type,
                    message=error_message,
                ),
            )
            await producer.send(response, properties={"id": id})
            return

        try:
            label, confidence = self._predict(trained, query)
            response = ClozeResponse(
                label=label,
                confidence=confidence,
            )

        except Exception as e:
            logger.error(f"Prediction error: {e}")
            response = ClozeResponse(
                error=Error(
                    type="prediction-error",
                    message=str(e),
                ),
            )

        await producer.send(response, properties={"id": id})

    def _list_models(self, workspace):

        models = []

        ws_models = self.models.get(workspace, {})
        for name, trained in ws_models.items():
            models.append(ClozeModelInfo(
                name=name,
                state="ready",
                labels=list(trained.tool_tokens),
                accuracy=trained.accuracy,
                train_size=trained.train_size,
                test_size=trained.test_size,
            ))

        for ws, instance_name in self.training:
            if ws == workspace and instance_name not in ws_models:
                models.append(ClozeModelInfo(
                    name=instance_name,
                    state="training",
                ))

        return ClozeResponse(models=models)

    def _predict(self, trained, query):

        trained.model.eval()

        prompt = (
            f"Query: {query} Tool: {trained.tokenizer.mask_token}"
        )
        inputs = trained.tokenizer(
            prompt, return_tensors="pt"
        ).to(trained.device)

        with torch.no_grad():
            outputs = trained.model(**inputs)
            logits = outputs.logits

            mask_idx = (
                inputs["input_ids"] == trained.tokenizer.mask_token_id
            ).nonzero(as_tuple=True)[1][0]
            mask_logits = logits[0, mask_idx, :]

            candidate_logits = mask_logits[trained.tool_token_ids]
            candidate_probs = torch.softmax(candidate_logits, dim=-1)
            best_idx = torch.argmax(candidate_probs).item()

            label = trained.tool_tokens[best_idx]
            confidence = candidate_probs[best_idx].item()

        return label, confidence

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)

        parser.add_argument(
            '-m', '--model',
            default=default_model,
            help=f'Base model for fine-tuning (default: {default_model})'
        )

def run():

    Processor.launch(default_ident, __doc__)
