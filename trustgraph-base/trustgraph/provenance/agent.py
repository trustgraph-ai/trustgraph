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
    PROV_ACTIVITY, PROV_ENTITY, PROV_WAS_DERIVED_FROM, PROV_STARTED_AT_TIME,
    TG_QUERY, TG_THOUGHT, TG_ACTION, TG_ARGUMENTS, TG_OBSERVATION, TG_ANSWER,
    TG_QUESTION, TG_ANALYSIS, TG_CONCLUSION, TG_DOCUMENT,
    TG_THOUGHT_DOCUMENT, TG_OBSERVATION_DOCUMENT,
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
    parent_uri: str,
    thought: str = "",
    action: str = "",
    arguments: Dict[str, Any] = None,
    observation: str = "",
    thought_document_id: Optional[str] = None,
    observation_document_id: Optional[str] = None,
) -> List[Triple]:
    """
    Build triples for one agent iteration (Analysis - think/act/observe cycle).

    Creates:
    - Entity declaration with tg:Analysis type
    - wasDerivedFrom link to parent (previous iteration or session)
    - Thought, action, arguments, and observation data
    - Document references for thought/observation when stored in librarian

    Args:
        iteration_uri: URI of this iteration (from agent_iteration_uri)
        parent_uri: URI of the parent (previous iteration or session)
        thought: The agent's reasoning/thought (used if thought_document_id not provided)
        action: The tool/action name
        arguments: Arguments passed to the tool (will be JSON-encoded)
        observation: The result/observation from the tool (used if observation_document_id not provided)
        thought_document_id: Optional document URI for thought in librarian (preferred)
        observation_document_id: Optional document URI for observation in librarian (preferred)

    Returns:
        List of Triple objects
    """
    if arguments is None:
        arguments = {}

    triples = [
        _triple(iteration_uri, RDF_TYPE, _iri(PROV_ENTITY)),
        _triple(iteration_uri, RDF_TYPE, _iri(TG_ANALYSIS)),
        _triple(iteration_uri, RDFS_LABEL, _literal(f"Analysis: {action}")),
        _triple(iteration_uri, PROV_WAS_DERIVED_FROM, _iri(parent_uri)),
        _triple(iteration_uri, TG_ACTION, _literal(action)),
        _triple(iteration_uri, TG_ARGUMENTS, _literal(json.dumps(arguments))),
    ]

    # Thought: use document reference or inline
    if thought_document_id:
        triples.append(_triple(iteration_uri, TG_THOUGHT_DOCUMENT, _iri(thought_document_id)))
    elif thought:
        triples.append(_triple(iteration_uri, TG_THOUGHT, _literal(thought)))

    # Observation: use document reference or inline
    if observation_document_id:
        triples.append(_triple(iteration_uri, TG_OBSERVATION_DOCUMENT, _iri(observation_document_id)))
    elif observation:
        triples.append(_triple(iteration_uri, TG_OBSERVATION, _literal(observation)))

    return triples


def agent_final_triples(
    final_uri: str,
    parent_uri: str,
    answer: str = "",
    document_id: Optional[str] = None,
) -> List[Triple]:
    """
    Build triples for an agent final answer (Conclusion).

    Creates:
    - Entity declaration with tg:Conclusion type
    - wasDerivedFrom link to parent (last iteration or session)
    - Either document reference (if document_id provided) or inline answer

    Args:
        final_uri: URI of the final answer (from agent_final_uri)
        parent_uri: URI of the parent (last iteration or session if no iterations)
        answer: The final answer text (used if document_id not provided)
        document_id: Optional document URI in librarian (preferred)

    Returns:
        List of Triple objects
    """
    triples = [
        _triple(final_uri, RDF_TYPE, _iri(PROV_ENTITY)),
        _triple(final_uri, RDF_TYPE, _iri(TG_CONCLUSION)),
        _triple(final_uri, RDFS_LABEL, _literal("Conclusion")),
        _triple(final_uri, PROV_WAS_DERIVED_FROM, _iri(parent_uri)),
    ]

    if document_id:
        # Store reference to document in librarian (as IRI)
        triples.append(_triple(final_uri, TG_DOCUMENT, _iri(document_id)))
    elif answer:
        # Fallback: store inline answer
        triples.append(_triple(final_uri, TG_ANSWER, _literal(answer)))

    return triples
