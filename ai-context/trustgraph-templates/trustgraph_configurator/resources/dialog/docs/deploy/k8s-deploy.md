To deploy to Kubernetes, you likely need to have Kubernetes credentials set up to connect to the Kubernetes management service. The mechanism to do this varies with the different kinds of Kubernetes services in use, check with your cloud provider documentation.

When you download the deploy configuration, you will have a ZIP file containing all the configuration needed to launch TrustGraph on Kubernetes. Unzip the ZIP file:

```bash
unzip deploy.zip
```

and launch:

```bash
kubectl apply -f resources.yaml
```
