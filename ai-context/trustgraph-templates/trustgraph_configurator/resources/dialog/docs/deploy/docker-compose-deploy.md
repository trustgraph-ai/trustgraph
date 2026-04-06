When you download the deploy configuration, you will have a ZIP file containing all the configuration needed to launch TrustGraph in Docker Compose. Unzip the ZIP file:

```bash
unzip deploy.zip
```

On MacOS, it may be necessary to specify a destination directory for the TrustGraph package:

```bash
unzip deploy.zip -d deploy
```

Navigate to the `docker-compose` directory. From this directory, launch TrustGraph with:

```bash
docker compose -f docker-compose.yaml up -d
```

If you are on Linux, running SELinux, you may need to change permissions on files in the deploy bundle so that they are accessible from within containers. This affects the `grafana` and `prometheus` directories.

```bash
chcon -Rt svirt_sandbox_file_t grafana prometheus
chmod 755 prometheus/ grafana/ grafana/*/
chmod 644 prometheus/* grafana/*/*
```
