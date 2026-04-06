LMStudio service URL must be provided in a Kubernetes secret.

```bash
kubectl -n {{namespace}} \
    create secret generic lmstudio-credentials \
    --from-literal=lmstudio-url=http://lmstudio:11434/
```

Replace the URL with the URL of your LMStudio service.
