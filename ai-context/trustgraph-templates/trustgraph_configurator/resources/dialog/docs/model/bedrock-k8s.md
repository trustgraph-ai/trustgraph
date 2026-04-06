To use AWS Bedrock, you must have enabled models in the AWS Bedrock console. You must also provide an AWS access key ID and secret key as a Kubernetes secret before deploying the application.

```bash
kubectl -n {{namespace}} create secret \
    generic bedrock-credentials \
    --from-literal=aws-id-key=AWS-ID-KEY \
    --from-literal=aws-secret=AWS-SECRET-KEY \
    --from-literal=aws-region=AWS-REGION-HERE
```
