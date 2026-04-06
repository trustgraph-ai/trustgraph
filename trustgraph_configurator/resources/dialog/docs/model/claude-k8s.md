To use Anthropic Claude, you need a Claude API key which must be provided in a Kubernetes secret.

```bash
kubectl -n {{namespace}} create secret \
    generic claude-credentials \
    --from-literal=claude-key=CLAUDE-KEY-HERE
```
