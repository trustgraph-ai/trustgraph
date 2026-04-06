The API Gateway is a required component which supports the CLI and Workbench. The API Gateway must be configured with a secret key. However, that secret key can be empty if no authentication is required. The Workbench does not currently use keys for authentication. The below example shows how to set the API Gateway secret to be empty with no authentication.

```bash
kubectl -n {{namespace}} create secret \
    generic gateway-secret \
    --from-literal=gateway-secret=
```
