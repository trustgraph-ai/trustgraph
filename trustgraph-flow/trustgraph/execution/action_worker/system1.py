
import json
import logging

from . common import ActionHandler, HandlerError

logger = logging.getLogger(__name__)


def _parse_state(value):
    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    return {"text": value}


class ClozeHandler(ActionHandler):

    inputs = {
        "model": {"artifact-type": "TextBlobArtifact"},
        "query": {"artifact-type": "TextBlobArtifact"},
    }
    outputs = {
        "classification": {"artifact-type": "ClassificationArtifact"},
    }

    async def execute(self, inputs, flow):

        model = inputs["model"]["text"]
        query = inputs["query"]["text"]

        if not query:
            raise HandlerError("cloze requires a non-empty 'query'")

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

        return {
            "classification": {
                "label": response.label,
                "confidence": response.confidence,
            }
        }


class DecisionScoringHandler(ActionHandler):

    inputs = {
        "state": {"artifact-type": "TextBlobArtifact"},
        "questions": {"artifact-type": "TextBlobArtifact"},
    }
    outputs = {
        "decision": {"artifact-type": "DecisionArtifact"},
    }

    async def execute(self, inputs, flow):

        state = _parse_state(inputs["state"]["text"])

        questions = json.loads(inputs["questions"]["text"])
        if not isinstance(questions, dict):
            raise HandlerError(
                "'questions' must be a JSON object"
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

        return {
            "decision": {
                "answers": response.answers,
                "model": response.model,
            }
        }


class FieldExtractionHandler(ActionHandler):

    inputs = {
        "state": {"artifact-type": "TextBlobArtifact"},
        "fields": {"artifact-type": "TextBlobArtifact"},
    }
    outputs = {
        "extracted": {"artifact-type": "ExtractedFieldsArtifact"},
    }

    async def execute(self, inputs, flow):

        state = _parse_state(inputs["state"]["text"])

        fields = json.loads(inputs["fields"]["text"])
        if not isinstance(fields, dict):
            raise HandlerError(
                "'fields' must be a JSON object"
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

        return {
            "extracted": {
                "answers": response.answers,
                "model": response.model,
            }
        }
