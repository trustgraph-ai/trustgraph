
"""
Keyword index over chunk text, backed by SQLite FTS5.  Consumes Chunk
messages off the ingestion stream and answers BM25 keyword queries; both
sides live in one service because the index is a single local file.  One
FTS5 table per (workspace, collection) keeps BM25 corpus statistics and
collection deletion scoped correctly.
"""

import asyncio
import logging
import re
import sqlite3
from pathlib import Path

from .... base import KeywordIndexService, CollectionConfigHandler
from .... schema import ChunkMatch

# Module logger
logger = logging.getLogger(__name__)

default_ident = "kw-index"
default_index_path = "/data/kw-index.db"

# FTS5 table names embed workspace/collection; quoting handles the rest, but
# strip anything outside the character set other stores allow in names so a
# hostile name can't smuggle quote characters.
_NAME_SAFE = re.compile(r"[^A-Za-z0-9_-]")

def _table(workspace, collection):
    ws = _NAME_SAFE.sub("_", workspace)
    coll = _NAME_SAFE.sub("_", collection)
    return f"kw_{ws}_{coll}"

def to_match_query(text):
    """User text -> FTS5 MATCH expression.

    Raw text is not valid FTS5 syntax ("7.3.2" is a syntax error, the "-" in
    "AURA-7" is column-filter syntax), so each whitespace token is quoted as
    a phrase and the phrases are OR-ed: BM25 scores accumulate over matching
    terms, and a quoted phrase of sub-tokens ("7.3.2" -> [7 3 2]) still
    matches the exact dotted term without also matching "7.3.1".
    """
    tokens = [t for t in text.split() if t.strip('"')]
    if not tokens:
        return None
    return " OR ".join('"' + t.replace('"', '""') + '"' for t in tokens)

class Processor(CollectionConfigHandler, KeywordIndexService):

    def __init__(self, **params):

        index_path = params.get("index_path", default_index_path)

        super(Processor, self).__init__(
            **params | {
                "index_path": index_path,
            }
        )

        Path(index_path).parent.mkdir(parents=True, exist_ok=True)

        # Writes are serialized on one connection by the lock; reads get
        # their own connection so a query never queues behind the chunk
        # ingestion backlog. WAL lets the reader proceed while a write
        # commits, and NORMAL sync is safe with WAL (an index is
        # re-derivable from the chunk store anyway). All sqlite work runs
        # in a thread so the event loop is never blocked.
        self.db = sqlite3.connect(index_path, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.read_db = sqlite3.connect(index_path, check_same_thread=False)
        self._lock = asyncio.Lock()

        # Register for config push notifications
        self.register_config_handler(self.on_collection_config, types=["collection"])

        logger.info(f"Keyword index at {index_path}")

    def _index(self, table, chunk_id, body):
        self.db.execute(
            f'CREATE VIRTUAL TABLE IF NOT EXISTS "{table}" '
            f'USING fts5(chunk_id UNINDEXED, body)'
        )
        # Re-ingesting a chunk replaces its previous row rather than
        # accumulating duplicates.
        self.db.execute(
            f'DELETE FROM "{table}" WHERE chunk_id = ?', (chunk_id,)
        )
        self.db.execute(
            f'INSERT INTO "{table}" (chunk_id, body) VALUES (?, ?)',
            (chunk_id, body),
        )
        self.db.commit()

    def _query(self, table, match, limit):
        try:
            rows = self.read_db.execute(
                f'SELECT chunk_id, bm25("{table}") FROM "{table}" '
                f'WHERE "{table}" MATCH ? ORDER BY bm25("{table}") LIMIT ?',
                (match, limit),
            ).fetchall()
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                # Nothing indexed for this collection yet
                return []
            raise
        # bm25() is lower-is-better (negative); negate so ChunkMatch.score
        # is higher-is-better like the vector path.
        return [ChunkMatch(chunk_id=r[0], score=-r[1]) for r in rows]

    async def index_chunk(self, workspace, message):

        if not self.collection_exists(workspace, message.metadata.collection):
            logger.warning(
                f"Collection {message.metadata.collection} for workspace {workspace} "
                f"does not exist in config (likely deleted while data was in-flight). "
                f"Dropping message."
            )
            return

        chunk_id = message.document_id
        if not chunk_id:
            return

        body = message.chunk.decode("utf-8", errors="replace")
        if not body.strip():
            return

        table = _table(workspace, message.metadata.collection)

        async with self._lock:
            await asyncio.to_thread(self._index, table, chunk_id, body)

    async def query_keyword_index(self, workspace, request):

        match = to_match_query(request.query)
        if match is None:
            return []

        limit = request.limit if request.limit > 0 else 20
        table = _table(workspace, request.collection)

        # No lock: reads run on their own connection and WAL keeps them
        # consistent alongside the writer.
        return await asyncio.to_thread(self._query, table, match, limit)

    async def create_collection(self, workspace: str, collection: str, metadata: dict):
        """FTS5 tables are created lazily on first indexed chunk."""
        logger.info(
            f"Collection create request for {workspace}/{collection} - "
            f"table created lazily on first write"
        )

    async def delete_collection(self, workspace: str, collection: str):
        """Drop the FTS5 table for this collection via config push."""
        table = _table(workspace, collection)

        def drop():
            self.db.execute(f'DROP TABLE IF EXISTS "{table}"')
            self.db.commit()

        async with self._lock:
            await asyncio.to_thread(drop)
        logger.info(f"Deleted keyword index table: {table}")

    @staticmethod
    def add_args(parser):

        KeywordIndexService.add_args(parser)

        parser.add_argument(
            '--index-path',
            default=default_index_path,
            help=f'SQLite FTS5 index file (default: {default_index_path})'
        )

def run():

    Processor.launch(default_ident, __doc__)
