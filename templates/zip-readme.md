These are launch configurations for TrustGraph.  See https://trustgraph.ai for
the quickstart using docker compose.

Hint for Linux: There are files here which get mounted as volumes inside
Docker Compose containers.  This may trigger SELinux rules on your system, to
permit access insider the containers, use a command like this...

chcon -Rt svirt_sandbox_file_t grafana/ prometheus/

The file vertexai/private.json is a placeholder for real GCP credentials if
you are using the VertexAI LLM.  If you're using that in Docker Compose,
replace with your real credentials, and don't forget to permit access if you
are using Linux:

chcon -Rt svirt_sandbox_file_t vertexai/

