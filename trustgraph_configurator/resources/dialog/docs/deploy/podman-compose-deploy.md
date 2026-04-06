When you download the deploy configuration, you will have a ZIP file containing all the configuration needed to launch TrustGraph in Podman Compose. Unzip the ZIP file:

```bash
unzip deploy.zip
```

Navigate to the `docker-compose` directory. From this directory, launch TrustGraph with:

```bash
podman compose -f docker-compose.yaml up -d
```

If you are on Linux, running SELinux, you may need to change permissions on files in the deploy bundle so that they are accessible from within containers. This affects the `grafana` and `prometheus` directories.

```bash
chcon -Rt svirt_sandbox_file_t grafana prometheus
chmod 755 prometheus/ grafana/ grafana/*/
chmod 644 prometheus/* grafana/*/*
```
