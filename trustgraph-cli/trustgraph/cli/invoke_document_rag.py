"""
Uses the DocumentRAG service to answer a question
"""

import argparse
import os
import sys
from trustgraph.api import (
    Api,
    ExplainabilityClient,
    RAGChunk,
    ProvenanceEvent,
    Question,
    Grounding,
    Exploration,
    Synthesis,
)

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_user = 'trustgraph'
default_collection = 'default'
default_doc_limit = 10


def question_explainable(
    url, flow_id, question_text, user, collection, doc_limit, token=None, debug=False
):
    """Execute document RAG with explainability - shows provenance events inline."""
    api = Api(url=url, token=token)
    socket = api.socket()
    flow = socket.flow(flow_id)
    explain_client = ExplainabilityClient(flow, retry_delay=0.2, max_retries=10)

    try:
        # Stream DocumentRAG with explainability - process events as they arrive
        for item in flow.document_rag_explain(
            query=question_text,
            user=user,
            collection=collection,
            doc_limit=doc_limit,
        ):
            if isinstance(item, RAGChunk):
                # Print response content
                print(item.content, end="", flush=True)

            elif isinstance(item, ProvenanceEvent):
                # Process provenance event immediately
                prov_id = item.explain_id
                explain_graph = item.explain_graph or "urn:graph:retrieval"

                entity = explain_client.fetch_entity(
                    prov_id,
                    graph=explain_graph,
                    user=user,
                    collection=collection
                )

                if entity is None:
                    if debug:
                        print(f"\n  [warning] Could not fetch entity: {prov_id}", file=sys.stderr)
                    continue

                # Display based on entity type
                if isinstance(entity, Question):
                    print(f"\n  [question] {prov_id}", file=sys.stderr)
                    if entity.query:
                        print(f"    Query: {entity.query}", file=sys.stderr)
                    if entity.timestamp:
                        print(f"    Time: {entity.timestamp}", file=sys.stderr)

                elif isinstance(entity, Grounding):
                    print(f"\n  [grounding] {prov_id}", file=sys.stderr)
                    if entity.concepts:
                        for concept in entity.concepts:
                            print(f"    Concept: {concept}", file=sys.stderr)

                elif isinstance(entity, Exploration):
                    print(f"\n  [exploration] {prov_id}", file=sys.stderr)
                    if entity.chunk_count:
                        print(f"    Chunks retrieved: {entity.chunk_count}", file=sys.stderr)

                elif isinstance(entity, Synthesis):
                    print(f"\n  [synthesis] {prov_id}", file=sys.stderr)
                    if entity.document:
                        print(f"    Document: {entity.document}", file=sys.stderr)

                else:
                    if debug:
                        print(f"\n  [unknown] {prov_id} (type: {entity.entity_type})", file=sys.stderr)

        print()  # Final newline

    finally:
        socket.close()


def question(
    url, flow_id, question_text, user, collection, doc_limit,
    streaming=True, token=None, explainable=False, debug=False
):
    # Explainable mode uses the API to capture and process provenance events
    if explainable:
        question_explainable(
            url=url,
            flow_id=flow_id,
            question_text=question_text,
            user=user,
            collection=collection,
            doc_limit=doc_limit,
            token=token,
            debug=debug
        )
        return

    # Create API client
    api = Api(url=url, token=token)

    if streaming:
        # Use socket client for streaming
        socket = api.socket()
        flow = socket.flow(flow_id)

        try:
            response = flow.document_rag(
                query=question_text,
                user=user,
                collection=collection,
                doc_limit=doc_limit,
                streaming=True
            )

            # Stream output
            for chunk in response:
                print(chunk, end="", flush=True)
            print()  # Final newline

        finally:
            socket.close()
    else:
        # Use REST API for non-streaming
        flow = api.flow().id(flow_id)
        resp = flow.document_rag(
            query=question_text,
            user=user,
            collection=collection,
            doc_limit=doc_limit,
        )
        print(resp)


def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-document-rag',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-t', '--token',
        default=default_token,
        help='Authentication token (default: $TRUSTGRAPH_TOKEN)',
    )

    parser.add_argument(
        '-f', '--flow-id',
        default="default",
        help=f'Flow ID (default: default)'
    )

    parser.add_argument(
        '-q', '--question',
        required=True,
        help=f'Question to answer',
    )

    parser.add_argument(
        '-U', '--user',
        default=default_user,
        help=f'User ID (default: {default_user})'
    )

    parser.add_argument(
        '-C', '--collection',
        default=default_collection,
        help=f'Collection ID (default: {default_collection})'
    )

    parser.add_argument(
        '-d', '--doc-limit',
        type=int,
        default=default_doc_limit,
        help=f'Document limit (default: {default_doc_limit})'
    )

    parser.add_argument(
        '--no-streaming',
        action='store_true',
        help='Disable streaming (use non-streaming mode)'
    )

    parser.add_argument(
        '-x', '--explainable',
        action='store_true',
        help='Show provenance events: Question, Exploration, Synthesis (implies streaming)'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Show debug output for troubleshooting'
    )

    args = parser.parse_args()

    try:

        question(
            url=args.url,
            flow_id=args.flow_id,
            question_text=args.question,
            user=args.user,
            collection=args.collection,
            doc_limit=args.doc_limit,
            streaming=not args.no_streaming,
            token=args.token,
            explainable=args.explainable,
            debug=args.debug,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
