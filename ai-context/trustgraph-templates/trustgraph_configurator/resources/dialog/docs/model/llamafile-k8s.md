To use Llamafile, you must have a Llamafile service running on an accessible host. The Llamafile host must be provided in a Kubernetes secret.

```bash
kubectl -n {{namespace}} create secret \
    generic llamafile-credentials \
    --from-literal=llamafile-url=http://llamafile:1234/
```
