local images = import "values/images.jsonnet";

{

    garage +: {

        // Garage S3 credentials - these are the actual access key ID and secret key
        // Access Key ID must be in format: GK + 24 hex characters (12 bytes)
        // Secret Key must be 64 hex characters (32 bytes)
        // For production, generate secure random values and override these defaults
        "access-key":: "GK000000000000000000000001",
        "secret-key":: "b171f00be9be4c32c734f4c05fe64c527a8ab5eb823b376cfa8c2531f70fc427",
        "rpc-secret":: "bbba746a9e289bad64a9e7a36a4299dac8d6e0b8cc2a6c2937fe756df4492008",
        // For a production system, override this value
        "admin-token":: "batts-rockhearted-unpartially",
        region:: "garage",
        "replication-factor":: "1",  // Set to 1 for single-node, 3 for production

        // Storage volume sizes
        "meta-size":: "2G",    // Metadata volume size
        "data-size":: "5G",    // Data volume size (also used for cluster layout capacity)

        create:: function(engine)

            local accessKey = self["access-key"];
            local secretKey = self["secret-key"];
            local rpcSecret = self["rpc-secret"];
            local adminToken = self["admin-token"];
            local region = self.region;
            local replicationFactor = self["replication-factor"];
            local metaSize = self["meta-size"];
            local dataSize = self["data-size"];

            // Garage daemon configuration file - TOML format
            local garage_conf = |||
                metadata_dir = "/var/lib/garage/meta"
                data_dir = "/var/lib/garage/data"

                db_engine = "lmdb"

                replication_factor = %s

                compression_level = 1

                rpc_bind_addr = "[::]:3901"
                rpc_public_addr = "[::]:3901"
                rpc_secret = "%s"

                [s3_api]
                s3_region = "%s"
                api_bind_addr = "[::]:3900"
                root_domain = ".s3.garage.local"

                [s3_web]
                bind_addr = "[::]:3902"
                root_domain = ".web.garage.local"
                index = "index.html"

                [k2v_api]
                api_bind_addr = "[::]:3904"

                [admin]
                api_bind_addr = "[::]:3903"
                admin_token = "%s"
            ||| % [replicationFactor, rpcSecret, region, adminToken];

            // Config volume - contains the rendered garage.toml
            local cfgVol = engine.configVolume(
                "garage-cfg", "garage",
                {
                    "garage.toml": garage_conf,
                }
            );

            // Volumes - Garage stores metadata and data separately
            local vol_meta = engine.volume("garage-meta").with_size(metaSize);
            local vol_data = engine.volume("garage-data").with_size(dataSize);

            // Main Garage daemon container
            local garage_container =
                engine.container("garage")
                    .with_image(images.garage)
                    .with_command([
                        "/garage", "-c", "/etc/garage/garage.toml", "server"
                    ])
                    .with_environment({
                        RUST_LOG: "garage=info",
                    })
                    .with_limits("1.0", "512M")
                    .with_reservations("0.5", "512M")
                    .with_port(3900, 3900, "s3-api")
                    .with_port(3901, 3901, "rpc")
                    .with_port(3902, 3902, "web")
                    .with_port(3903, 3903, "admin")
                    .with_port(3904, 3904, "k2v")
                    .with_volume_mount(cfgVol, "/etc/garage/")
                    .with_volume_mount(vol_meta, "/var/lib/garage/meta")
                    .with_volume_mount(vol_data, "/var/lib/garage/data");

            // Init container - configures cluster layout and creates S3 credentials
            // IMPORTANT: This container exits with code 0 after completion
            // Orchestrator must NOT restart it (use K8s Job or Compose restart: "no")
            // Uses Alpine base image since garage container has no shell
            local init_container =
                engine.container("garage-init")
                    .with_image("docker.io/alpine:3.23.2")
                    .with_environment({
                        GARAGE_ACCESS_KEY: accessKey,
                        GARAGE_SECRET_KEY: secretKey,
                        GARAGE_REGION: region,
                        GARAGE_ADMIN_TOKEN: adminToken,
                        GARAGE_RPC_SECRET: rpcSecret,
                        GARAGE_DATA_SIZE: dataSize,
                    })
                    .with_limits("0.5", "256M")
                    .with_reservations("0.25", "128M")
                    .with_volume_mount(cfgVol, "/etc/garage/")
                    .with_command([
                        "sh", "-c", |||
                            set -e

                            # Install required tools
                            echo "Installing curl, jq and downloading garage CLI..."
                            apk add --no-cache curl jq

                            # Download garage binary (v2.1.0) for remote management
                            curl -fsSL "https://garagehq.deuxfleurs.fr/_releases/v2.1.0/x86_64-unknown-linux-musl/garage" \
                                -o /usr/local/bin/garage
                            chmod +x /usr/local/bin/garage

                            echo "Waiting for Garage daemon to be ready..."
                            MAX_ATTEMPTS=60
                            ATTEMPT=0
                            # Wait for /health to respond (even 503 is fine - means daemon is up)
                            until curl -s http://garage:3903/health >/dev/null 2>&1; do
                                ATTEMPT=$((ATTEMPT+1))
                                if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
                                    echo "ERROR: Garage failed to become ready after ${MAX_ATTEMPTS} attempts"
                                    exit 1
                                fi
                                echo "Attempt ${ATTEMPT}/${MAX_ATTEMPTS}: Garage not ready, retrying in 2s..."
                                sleep 2
                            done
                            echo "Garage daemon is ready."

                            # Get the node ID via v2 Admin API
                            echo "Getting Garage node ID via Admin API..."
                            curl -s -H "Authorization: Bearer ${GARAGE_ADMIN_TOKEN}" \
                                "http://garage:3903/v2/GetNodeInfo?node=self" > /tmp/garage-node-info.json

                            # Extract node ID from response (the key in success map is the node ID)
                            NODE_ID=$(jq -r '.success | to_entries[0].value.nodeId' /tmp/garage-node-info.json)
                            echo "Node ID: ${NODE_ID}"

                            if [ -z "$NODE_ID" ] || [ "$NODE_ID" = "null" ]; then
                                echo "ERROR: Failed to retrieve node ID"
                                exit 1
                            fi

                            # ===== LAYOUT MANAGEMENT VIA REMOTE RPC =====
                            # Use garage CLI with -h and -s flags to connect remotely
                            # -h requires format: <node-id>@<host>:<port>
                            # -s provides the RPC secret

                            # Construct full RPC identifier
                            RPC_HOST="${NODE_ID}@garage:3901"
                            echo "RPC Host: ${RPC_HOST}"

                            # Check current layout to see if node is already assigned (idempotent)
                            echo "Checking current cluster layout..."
                            LAYOUT_OUTPUT=$(garage -h "${RPC_HOST}" -s "${GARAGE_RPC_SECRET}" layout show 2>&1)

                            # Check if node already has a role assigned
                            # Layout output shows abbreviated node ID (first 16 chars)
                            NODE_ID_SHORT="${NODE_ID:0:16}"
                            if echo "$LAYOUT_OUTPUT" | grep -q "$NODE_ID_SHORT"; then
                                echo "Node ${NODE_ID_SHORT}... already assigned in layout, skipping."
                            else
                                echo "Assigning node to cluster layout..."
                                # Assign node to zone dc1 with configured capacity
                                garage -h "${RPC_HOST}" -s "${GARAGE_RPC_SECRET}" \
                                    layout assign ${NODE_ID} -z dc1 -c ${GARAGE_DATA_SIZE}

                                echo "Applying layout configuration..."
                                # Get current staged version and apply
                                garage -h "${RPC_HOST}" -s "${GARAGE_RPC_SECRET}" \
                                    layout apply --version 1

                                echo "Layout configured successfully."
                                # Wait for layout to stabilize
                                sleep 5
                            fi

                            # ===== KEY MANAGEMENT VIA REMOTE RPC =====

                            # Check if key already exists (idempotent)
                            # GARAGE_ACCESS_KEY is already a valid Garage Key ID (GK + 24 hex chars)
                            if garage -h "${RPC_HOST}" -s "${GARAGE_RPC_SECRET}" key info "${GARAGE_ACCESS_KEY}" >/dev/null 2>&1; then
                                echo "Access key ${GARAGE_ACCESS_KEY} already exists, skipping creation."
                            else
                                echo "Importing S3 access key: ${GARAGE_ACCESS_KEY}"

                                # Import key with the provided credentials (both already in valid Garage format)
                                # GARAGE_ACCESS_KEY = Key ID (GK + 24 hex chars)
                                # GARAGE_SECRET_KEY = Secret (64 hex chars)
                                garage -h "${RPC_HOST}" -s "${GARAGE_RPC_SECRET}" \
                                    key import "${GARAGE_ACCESS_KEY}" "${GARAGE_SECRET_KEY}" --yes

                                echo "Access key imported successfully."
                            fi

                            # Grant permissions to the key
                            echo "Granting create-bucket permission to key..."
                            garage -h "${RPC_HOST}" -s "${GARAGE_RPC_SECRET}" \
                                key allow --create-bucket "${GARAGE_ACCESS_KEY}"

                            echo ""
                            echo "Garage initialization complete!"
                            echo "S3 Endpoint: http://garage:3900"
                            echo "Region: ${GARAGE_REGION}"
                            exit 0
                        |||,
                    ]);

            // Container sets
            local garage_containerSet = engine.containers("garage", [garage_container]);
            local init_containerSet = engine.containers("garage-init", [init_container]);

            // Service - expose Garage ports
            local garage_service =
                engine.service(garage_containerSet)
                    .with_port(3900, 3900, "s3-api")
                    .with_port(3901, 3901, "rpc")
                    .with_port(3902, 3902, "web")
                    .with_port(3903, 3903, "admin")
                    .with_port(3904, 3904, "k2v");

            engine.resources([
                cfgVol,
                vol_meta,
                vol_data,
                garage_containerSet,
                init_containerSet,
                garage_service,
            ])

    },

}
