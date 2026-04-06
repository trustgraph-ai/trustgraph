The TGI service URL must be provided in a Kubernetes secret.

```bash
kubectl -n {{namespace}} \
    create secret generic tgi-credentials \
    --from-literal=tgi-url=http://tgi:8080/v1
```

Replace the URL with the URL of your TGI service.
