To use VertexAI, you need to have a Google Cloud credential file provisioned for a service account which has access to the VertexAI services. This means signing up to GCP and using an existing, or launching a new GCP project. The GCP credential will be a JSON file which would arrive in a file called `private.json`.

The private.json file should be loaded into Kubernetes as a secret.

```bash
kubectl -n {{namespace}} create secret \
    generic vertexai-creds --from-file=private.json=private.json
```

> **Warning:** Google Cloud private.json files are secrets which potentially provide access to all of your Google Cloud resources. Take great care to ensure that the permissions of the account are minimal, ideally scoped to just AI services.
