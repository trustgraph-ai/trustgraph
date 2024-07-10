
# For AMD...
# pip3 install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/rocm6.1/

----------------------------------------------------------------------------

docker network create trustgraph --driver bridge

docker volume create cassandra
docker volume create pulsar-conf
docker volume create pulsar-data
docker volume create etcd
docker volume create minio-data
docker volume create milvus

----------------------------------------------------------------------------

Cassandra:
docker run -i -t \
    --name cassandra \
    --network trustgraph \
    -p 9042:9042 \
    -v cassandra:/var/lib/cassandra \
    docker.io/cassandra:4.1.5

----------------------------------------------------------------------------

Pulsar:

docker run -it \
    --name pulsar \
    --network trustgraph \
    -p 6650:6650 \
    -p 8080:8080 \
    -v pulsar-conf:/pulsar/conf \
    -v pulsar-data:/pulsar/data \
    docker.io/apachepulsar/pulsar:3.3.0 \
        bin/pulsar standalone

----------------------------------------------------------------------------

Milvus:

docker run -i -t \
    --name etcd \
    --network trustgraph \
    -p 2379:2379 \
    -e ETCD_AUTO_COMPACTION_MODE=revision \
    -e ETCD_AUTO_COMPACTION_RETENTION=1000 \
    -e ETCD_QUOTA_BACKEND_BYTES=4294967296 \
    -e ETCD_SNAPSHOT_COUNT=50000 \
    -v etcd:/etcd \
    quay.io/coreos/etcd:v3.5.5 \
        etcd -advertise-client-urls=http://127.0.0.1:2379 \
        -listen-client-urls http://0.0.0.0:2379 --data-dir /etcd

docker run -i -t \
    --name minio \
    --network trustgraph \
    -p 9000:9000 -p 9001:9001 \
    -e MINIO_ACCESS_KEY=minioadmin \
    -e MINIO_SECRET_KEY=minioadmin \
    -v minio-data:/minio_data \
    docker.io/minio/minio:RELEASE.2024-07-04T14-25-45Z \
        minio server /minio_data --console-address :9001

docker run -i -t \
    --name milvus \
    --network trustgraph \
    -p 19530:19530 -p 9091:9091 \
    -e ETCD_ENDPOINTS=etcd:2379 \
    -e MINIO_ADDRESS=minio:9000 \
    -v milvus:/var/lib/milvus \
    docker.io/milvusdb/milvus:v2.4.5 \
        milvus run standalone

----------------------------------------------------------------------------

. env/bin/activate

scripts/pdf-decoder -p pulsar://localhost:6650/
scripts/chunker -p pulsar://localhost:6650/
scripts/vectorize-minilm -p pulsar://localhost:6650/
scripts/kg-extract-definitions -p pulsar://localhost:6650/
scripts/kg-extract-relationships -p pulsar://localhost:6650/
scripts/vector-write-milvus -p pulsar://localhost:6650/
scripts/graph-write-cassandra -p pulsar://localhost:6650/
scripts/llm-ollama-text  -p pulsar://localhost:6650/ -r http://monster:11434/

----------------------------------------------------------------------------

The pub/sub infra means individual processors can be switched out for other
processors which do the same thing e.g.

- graph-write writes to Cassandra but could be switched out for something else
  which uses a different store
- vector-store writes to Milvus but could be switched out for something which
  writes to a different store
- llm-ollama invokes Ollama, could be switched out for a different LLM with a
  different API

The vectorizer is a bit hard to switch out ATM, different embedding algorithms
have different vector dimensions, but can probably make that work.

kg-extractor turns chunks into edges, so maybe that could be switched out for
different algorithms & different schemas. Potentially a good place for 'value
add' processing to be added.

It would also be possible to have more than one processor running where
kg-extractor sits to have different kinds of semantic extraction: other
proceessors could take as input the output of vectorizer, and drop edges and
edge associations into graph-write and vector-store

Actually, as it stands, kg-extractor does 2 different kinds of processing
itself:

- Creates edges for relationships, and
- Creates edges for definitions

Each of those uses its own LLM invocation and mashes the output into RDF. It
would be useful to split kg-extractor into 2 pieces to demonstrate this bit of
the architecture.

----------------------------------------------------------------------------

- pdf-extractor turns a PDF doc into plain text.  For each PDF page, a
  separate blob of text is emitted currently.
- chunker applies chunking to turn 1 PDF page into several chunks
- vectorizer invokes a sentence embedding model to create vectors.  Doesn't
  store anything.  Output of vectorizer is chunk plus embedding.
- kg-extract turns chunks into edges using LLM prompting. There are 2 outputs:
  - RDF triples
  - An association between the vector embedding and RDF entities. For every
    triple, there's an association between the S, P and O entiites and the
    embedding.
- graph-write loads the triples into a store
- vector-store store the association between the vector and the RDF URI in a
  vector store

----------------------------------------------------------------------------

The demo query algorithm is...

- Take the question, extract embeddings using a sentence model
- Use the vector store to lookup RDF URIs
- Use the RDF URIs to find relevant RDF triples in Cassandra
- Also use Cassandra to turn RDF URIs into plain-text labels if they are known
- Construct the prompt, turn RDF triples into a knowledge graph format (used
  Cypher, seems to work but not sure that's the best choice)
- LLM prompt and show the answer

