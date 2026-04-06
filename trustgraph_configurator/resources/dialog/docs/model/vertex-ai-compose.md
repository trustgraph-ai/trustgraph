To use VertexAI, you need to have a Google Cloud credential file provisioned for a service account which has access to the VertexAI services. This means signing up to GCP and using an existing, or launching a new GCP project. The GCP credential will be a JSON file which should be stored in `vertexai/private.json`.

The credential file is mounted as a volume in Docker Compose, which can cause issues with SELinux if you are running on Linux. Make sure that Docker has access to volume files if this affects you.

```bash
chcon -Rt svirt_sandbox_file_t vertexai/
```
