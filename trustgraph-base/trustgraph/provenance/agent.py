"""
Helper functions to build PROV-O triples for agent provenance.

Agent provenance tracks the reasoning trace of ReAct agent sessions:
- Question: The root activity with query and timestamp
- Analysis: Each think/act/observe cycle
- Conclusion: The final answer
"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any

from .. schema import Triple, Term, IRI, LITERAL

from . namespaces import (
    RDF_TYPE, RDFS_LABEL,
    PROV_ACTIVITY, PROV_ENTITY, PROV_WAS_DERIVED_FROM,
    PROV_WAS_GENERATED_BY, PROV_STARTED_AT_TIME,
    TG_QUERY, TG_THOUGHT, TG_ACTION, TG_ARGUMENTS, TG_OBSERVATION,
    TG_QUESTION, TG_ANALYSIS, TG_CONCLUSION, TG_DOCUMENT,
    TG_ANSWER_TYPE, TG_REFLECTION_TYPE, TG_THOUGHT_TYPE, TG_OBSERVATION_TYPE,
    TG_AGENT_QUESTION,
)


def _iri(uri: str) -> Term:
    """Create an IRI term."""
    return Term(type=IRI, iri=uri)


def _literal(value) -> Term:
    """Create a literal term."""
    return Term(type=LITERAL, value=str(value))


def _triple(s: str, p: str, o_term: Term) -> Triple:
    """Create a triple with IRI subject and predicate."""
    return Triple(s=_iri(s), p=_iri(p), o=o_term)


def agent_session_triples(
    session_uri: str,
    query: str,
    timestamp: Optional[str] = None,
) -> List[Triple]:
    """
    Build triples for an agent session start (Question).

    Creates:
    - Activity declaration with tg:Question type
    - Query text and timestamp

    Args:
        session_uri: URI of the session (from agent_session_uri)
        query: The user's query text
        timestamp: ISO timestamp (defaults to now)

    Returns:
        List of Triple objects
    """
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat() + "Z"

    return [
        _triple(session_uri, RDF_TYPE, _iri(PROV_ACTIVITY)),
        _triple(session_uri, RDF_TYPE, _iri(TG_QUESTION)),
        _triple(session_uri, RDF_TYPE, _iri(TG_AGENT_QUESTION)),
        _triple(session_uri, RDFS_LABEL, _literal("Agent Question")),
        _triple(session_uri, PROV_STARTED_AT_TIME, _literal(timestamp)),
        _triple(session_uri, TG_QUERY, _literal(query)),
    ]


def agent_iteration_triples(
    iteration_uri: str,
    question_uri: Optional[str] = None,
    previous_uri: Optional[str] = None,
    action: str = "",
    arguments: Dict[str, Any] = None,
    thought_uri: Optional[str] = None,
    thought_document_id: Optional[str] = None,
    observation_uri: Optional[str] = None,
    observation_document_id: Optional[str] = None,
) -> List[Triple]:
    """
    Build triples for one agent iteration (Analysis - think/act/observe cycle).

    Creates:
    - Entity declaration with tg:Analysis type
    - wasGeneratedBy link to question (if first iteration)
    - wasDerivedFrom link to previous iteration (if not first)
    - Action and arguments metadata
    - Thought sub-entity (tg:Reflection, tg:Thought) with librarian document
    - Observation sub-entity (tg:Reflection, tg:Observation) with librarian document

    Args:
        iteration_uri: URI of this iteration (from agent_iteration_uri)
        question_uri: URI of the question activity (for first iteration)
        previous_uri: URI of the previous iteration (for subsequent iterations)
        action: The tool/action name
        arguments: Arguments passed to the tool (will be JSON-encoded)
        thought_uri: URI for the thought sub-entity
        thought_document_id: Document URI for thought in librarian
        observation_uri: URI for the observation sub-entity
        observation_document_id: Document URI for observation in librarian

    Returns:
        List of Triple objects
    """
    if arguments is None:
        arguments = {}

    triples = [
        _triple(iteration_uri, RDF_TYPE, _iri(PROV_ENTITY)),
        _triple(iteration_uri, RDF_TYPE, _iri(TG_ANALYSIS)),
        _triple(iteration_uri, RDFS_LABEL, _literal(f"Analysis: {action}")),
        _triple(iteration_uri, TG_ACTION, _literal(action)),
        _triple(iteration_uri, TG_ARGUMENTS, _literal(json.dumps(arguments))),
    ]

    if question_uri:
        triples.append(
            _triple(iteration_uri, PROV_WAS_GENERATED_BY, _iri(question_uri))
        )
    elif previous_uri:
        triples.append(
            _triple(iteration_uri, PROV_WAS_DERIVED_FROM, _iri(previous_uri))
        )

    # Thought sub-entity
    if thought_uri:
        triples.extend([
            _triple(iteration_uri, TG_THOUGHT, _iri(thought_uri)),
            _triple(thought_uri, RDF_TYPE, _iri(TG_REFLECTION_TYPE)),
            _triple(thought_uri, RDF_TYPE, _iri(TG_THOUGHT_TYPE)),
            _triple(thought_uri, RDFS_LABEL, _literal("Thought")),
            _triple(thought_uri, PROV_WAS_GENERATED_BY, _iri(iteration_uri)),
        ])
        if thought_document_id:
            triples.append(
                _triple(thought_uri, TG_DOCUMENT, _iri(thought_document_id))
            )

    # Observation sub-entity
    if observation_uri:
        triples.extend([
            _triple(iteration_uri, TG_OBSERVATION, _iri(observation_uri)),
            _triple(observation_uri, RDF_TYPE, _iri(TG_REFLECTION_TYPE)),
            _triple(observation_uri, RDF_TYPE, _iri(TG_OBSERVATION_TYPE)),
            _triple(observation_uri, RDFS_LABEL, _literal("Observation")),
            _triple(observation_uri, PROV_WAS_GENERATED_BY, _iri(iteration_uri)),
        ])
        if observation_document_id:
            triples.append(
                _triple(observation_uri, TG_DOCUMENT, _iri(observation_document_id))
            )

    return triples


def agent_final_triples(
    final_uri: str,
    question_uri: Optional[str] = None,
    previous_uri: Optional[str] = None,
    document_id: Optional[str] = None,
) -> List[Triple]:
    """
    Build triples for an agent final answer (Conclusion).

    Creates:
    - Entity declaration with tg:Conclusion and tg:Answer types
    - wasGeneratedBy link to question (if no iterations)
    - wasDerivedFrom link to last iteration (if iterations exist)
    - Document reference to librarian

    Args:
        final_uri: URI of the final answer (from agent_final_uri)
        question_uri: URI of the question activity (if no iterations)
        previous_uri: URI of the last iteration (if iterations exist)
        document_id: Librarian document ID for the answer content

    Returns:
        List of Triple objects
    """
    triples = [
        _triple(final_uri, RDF_TYPE, _iri(PROV_ENTITY)),
        _triple(final_uri, RDF_TYPE, _iri(TG_CONCLUSION)),
        _triple(final_uri, RDF_TYPE, _iri(TG_ANSWER_TYPE)),
        _triple(final_uri, RDFS_LABEL, _literal("Conclusion")),
    ]

    if question_uri:
        triples.append(
            _triple(final_uri, PROV_WAS_GENERATED_BY, _iri(question_uri))
        )
    elif previous_uri:
        triples.append(
            _triple(final_uri, PROV_WAS_DERIVED_FROM, _iri(previous_uri))
        )

    if document_id:
        triples.append(_triple(final_uri, TG_DOCUMENT, _iri(document_id)))

    return triples
