
import json
import logging

from . common import (
    HandlerError, get_param, get_input_artifact, parse_param_json,
)

logger = logging.getLogger(__name__)


def _parse_state(value):
    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    return {"text": value}


class ClozeHandler:

    async def execute(self, params, input_artifacts, flow):

        model = get_param(params, "model")

        text_artifact = get_input_artifact(
            input_artifacts, "TextBlobArtifact",
        )
        if text_artifact:
            query = text_artifact.get("text", "")
        else:
            query = get_param(params, "query")

        if not query:
            raise HandlerError(
                "cloze requires a 'query' parameter or "
                "TextBlobArtifact input"
            )

        logger.info(
            f"Cloze classification: model={model}, "
            f"query={query[:80]}..."
        )

        cloze = flow("cloze-request")
        response = await cloze.predict(
            model=model,
            query=query,
            timeout=300,
        )

        return "ClassificationArtifact", {
            "label": response.label,
            "confidence": response.confidence,
        }


class DecisionScoringHandler:

    async def execute(self, params, input_artifacts, flow):

        text_artifact = get_input_artifact(
            input_artifacts, "TextBlobArtifact",
        )
        if text_artifact:
            state = text_artifact.get("text", "")
        else:
            state = get_param(params, "state", required=False)

        if not state:
            raise HandlerError(
                "decision-scoring requires a 'state' parameter or "
                "TextBlobArtifact input"
            )

        if isinstance(state, str):
            state = _parse_state(state)

        questions = parse_param_json(params, "questions", dict)
        if not questions:
            raise HandlerError(
                "decision-scoring requires a 'questions' parameter "
                "(JSON object)"
            )

        logger.info(
            f"Decision scoring: {len(questions)} questions"
        )

        scoring = flow("decision-scoring-request")
        response = await scoring.score(
            state=state,
            questions=questions,
            timeout=300,
        )

        return "DecisionArtifact", {
            "answers": response.answers,
            "model": response.model,
        }


class FieldExtractionHandler:

    async def execute(self, params, input_artifacts, flow):

        text_artifact = get_input_artifact(
            input_artifacts, "TextBlobArtifact",
        )
        if text_artifact:
            state = text_artifact.get("text", "")
        else:
            state = get_param(params, "state", required=False)

        if not state:
            raise HandlerError(
                "field-extraction requires a 'state' parameter or "
                "TextBlobArtifact input"
            )

        if isinstance(state, str):
            state = _parse_state(state)

        fields = parse_param_json(params, "fields", dict)
        if not fields:
            raise HandlerError(
                "field-extraction requires a 'fields' parameter "
                "(JSON object)"
            )

        logger.info(
            f"Field extraction: {len(fields)} fields"
        )

        extraction = flow("field-extraction-request")
        response = await extraction.extract(
            state=state,
            fields=fields,
            timeout=300,
        )

        return "ExtractedFieldsArtifact", {
            "answers": response.answers,
            "model": response.model,
        }
