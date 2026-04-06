
//
// This majorly does not work
//

// This configuration fails primarily because it tries to treat Ceph
// like a stateless web app. You are currently pointing mon host to a
// generic service name (ceph-mon), but you aren't telling the Monitor
// process to assume that service identity.

// To make this work with the "Service Name" approach across any
// engine, you need to fix the binding logic and the messenger protocol.

// 1. The ceph.conf Fix

// Need to enable Messenger v2 (modern) and tell the cluster to use
// the service names for its initial quorum.

//Change this section:
// Ini, TOML

// [global]
// fsid = %s
// mon initial members = mon0
// mon host = ceph-mon:6789
// ...

// To this:
// Ini, TOML

// [global]
// fsid = %s
// # Use the actual service names as members
// mon initial members = ceph-mon
// # Explicitly use the Service name (VIP)
// mon host = ceph-mon
// # Force modern protocol
// ms_bind_msgr2 = true
// ms_bind_msgr1 = true

// 2. The MON Environment & Command Fix

// This is the most critical part. Your current config sets MON_IP:
// "0.0.0.0". This causes the MON to bind to the Pod IP, which breaks
// when the Pod restarts. You must force it to bind to the Service IP.

// Update mon_env:
// Code snippet

// local mon_env = cluster_env + {
//     CEPH_DAEMON: "MON",
//     MON_NAME: "mon0",
//     # Remove MON_IP: "0.0.0.0"
//     # Add these:
//     MON_ADDR: "ceph-mon", // This says to resolve the service name
// };

// Update mon_container command: You are currently wiping the MON data
// on every start (rm -rf /var/lib/ceph/mon/*). Stop doing that. If you
// wipe the data, you lose the cluster state and the OSDs will refuse to
// talk to the "new" MON.

// Code snippet

// .with_command([
//     "bash", "-c",
//     # 1. Resolve the Service IP at runtime
//     "export MON_IP=$(getent hosts ceph-mon | awk '{ print $1 }'); " +
//     inject_mon_config + 
//     # 2. Start the daemon telling it its PUBLIC address is the Service VIP
//     "exec /opt/ceph-container/bin/entrypoint.sh"
// ])

// 3. Why your current config "Majorly does not work"

// The "Wipe" Logic: By running rm -rf /var/lib/ceph/mon/* in the
// MON container, you are creating a "New Cluster" every time the
// container starts. Since the OSDs store the fsid and cluster
// secrets, they will reject the "new" MON.

// DNS Race Condition: Your OSD/MGR/RGW containers wait for
// ceph-mon DNS, which is good. However, if ceph-mon resolves to a
// Round Robin IP (multiple pods) rather than a stable ClusterIP, the
// connection will be flaky.

// Messenger Protocol: Without ms_bind_msgr2, Ceph defaults to the
// old v1 protocol which is much more sensitive to NAT/Container IP
// mismatches.

// SUMMARY

// Component: ceph.conf
// Change: Add ms_bind_msgr2 = true
// Why: Supports modern container networking better.

// Component: MON Start
// Change: Remove rm -rf
// Why: Ceph MONs must keep their database to maintain the cluster.

// Component: MON Address
// Change: Use getent hosts ceph-mon
// Why: Forces the MON to advertise the Service VIP instead of its own Pod IP.

// Component: MON Keyring
// Change: Ensure /etc/ceph/ceph.mon.keyring exists
// Why: MONs need their specific key to start.

local images = import "values/images.jsonnet";

{
    with:: function(key, value)
        self + {
            ["ceph-" + key]:: value,
        },

    // Ceph credentials and cluster settings
    "ceph-access-key":: "object-user",
    "ceph-secret-key":: "object-password",
    "ceph-cluster-id":: "ceph",
    "ceph-fsid":: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",

    // Pool redundancy settings
    // size: 2 = two replicas for fault tolerance
    // min_size: 1 = allow degraded I/O if one OSD is down (prevents cluster freeze)
    "ceph-pool-size":: "2",
    "ceph-pool-min-size":: "1",

    ceph +: {
        create:: function(engine)
            // Pre-Shared Cryptographic Material - Config-as-Code Approach
            // These keys are generated once and distributed to all daemons
            // This ensures cryptographic consistency across the shared-nothing architecture
            local admin_key = "AQBpxSBlAAAAABAAU99V6D8vS7Uu9y1S8W0iBg==";
            local mon_key = "AQBpxSBlAAAAABAAn7pL/pG9oT+X6vO7V1S6bg==";

            // Ceph configuration file - rendered from Jsonnet variables
            local ceph_conf = |||
                [global]
                fsid = %s
                mon initial members = mon0
                mon host = ceph-mon:6789
                public network = 0.0.0.0/0
                cluster network = 0.0.0.0/0
                osd pool default size = %s
                osd pool default min size = %s
                osd crush chooseleaf type = 0
                auth cluster required = cephx
                auth service required = cephx
                auth client required = cephx
            ||| % [$["ceph-fsid"], $["ceph-pool-size"], $["ceph-pool-min-size"]];

            // Admin keyring - distributed to all daemons
            local admin_keyring = |||
                [client.admin]
                    key = %s
                    caps mds = "allow *"
                    caps mgr = "allow *"
                    caps mon = "allow *"
                    caps osd = "allow *"
            ||| % [admin_key];

            // Monitor keyring - used by MON for cluster operations
            local mon_keyring = |||
                [mon.]
                    key = %s
                    caps mon = "allow *"
            ||| % [mon_key];

            // Config injection command - writes files before entrypoint
            local inject_config = "printf '%s' > /etc/ceph/ceph.conf; printf '%s' > /etc/ceph/ceph.client.admin.keyring; " % [ceph_conf, admin_keyring];
            local inject_mon_config = inject_config + ("printf '%s' > /etc/ceph/ceph.mon.keyring; " % [mon_keyring]);

            // Data volumes - sized appropriately for production workloads
            local vol_mon = engine.volume("ceph-mon").with_size("20G");
            local vol_mgr = engine.volume("ceph-mgr").with_size("20G");
            local vol_osd = engine.volume("ceph-osd").with_size("100G");
            local vol_rgw = engine.volume("ceph-rgw").with_size("20G");

            // Isolated config volumes per daemon (ReadWriteOnce compatible)
            // Each daemon gets its own non-shared config volume to support
            // multi-node scheduling in K8s and other orchestrators
            local vol_mon_config = engine.volume("ceph-mon-config").with_size("500M");
            local vol_mgr_config = engine.volume("ceph-mgr-config").with_size("500M");
            local vol_osd_config = engine.volume("ceph-osd-config").with_size("500M");
            local vol_rgw_config = engine.volume("ceph-rgw-config").with_size("500M");
            local vol_init_config = engine.volume("ceph-init-config").with_size("500M");

            // Simplified cluster environment - Config-as-Code model
            // No fetch logic needed - config is injected before entrypoint runs
            local cluster_env = {
                CLUSTER: $["ceph-cluster-id"],
                FSID: $["ceph-fsid"],
                KV_TYPE: "none",  // No external coordination
            };

            // MON-specific environment
            // Config-as-Code: MON uses injected config files, not fetch logic
            //
            // CRITICAL: MON_DATA_AVAIL="0" forces fresh cluster bootstrap
            // The ceph/daemon entrypoint script (variables_stack.sh) uses this as a gate:
            // - MON_DATA_AVAIL="0" -> run mkfs, create new cluster with our FSID
            // - MON_DATA_AVAIL="1" -> attempt to join existing cluster (infinite probe loop)
            //
            // Network configuration for monmap generation
            local mon_env = cluster_env + {
                CEPH_DAEMON: "MON",
                MON_NAME: "mon0",
                MON_PORT: "6789",
                MON_DATA_AVAIL: "0",
                MON_IP: "0.0.0.0",
                NETWORK_AUTO_DETECT: "4",
                CEPH_PUBLIC_NETWORK: "0.0.0.0/0",
            };

            // Simplified daemon environments - Config-as-Code model
            // All daemons receive config via injection, not fetch from MON
            // This eliminates "static mode" errors and networking complexity

            // MGR-specific environment
            local mgr_env = cluster_env + {
                CEPH_DAEMON: "MGR",
                MGR_NAME: "mgr0",
            };

            // OSD-specific environment
            local osd_env = cluster_env + {
                CEPH_DAEMON: "OSD",
                OSD_TYPE: "directory",
            };

            // RGW-specific environment
            local rgw_env = cluster_env + {
                CEPH_DAEMON: "RGW",
                RGW_NAME: "rgw0",
                RGW_FRONTEND_PORT: "7480",
            };

            // MON (Monitor) container - cluster state and quorum
            // Config-as-Code: Injects pre-shared keys before entrypoint
            // CRITICAL: Wipes /var/lib/ceph/mon/* on every start to force fresh bootstrap
            // This ensures MON always uses our FSID and doesn't inherit stale cluster state
            local mon_container =
                engine.container("ceph-mon")
                    .with_image(images.ceph)
                    .with_environment(mon_env)
                    .with_command([
                        "bash", "-c",
                        "rm -rf /var/lib/ceph/mon/*; " +
                        inject_mon_config +
                        "exec /opt/ceph-container/bin/entrypoint.sh"
                    ])
                    .with_limits("1.0", "1536M")
                    .with_reservations("0.5", "1024M")
                    .with_port(6789, 6789, "mon")
                    .with_port(3300, 3300, "mon-msgr2")
                    .with_volume_mount(vol_mon, "/var/lib/ceph/mon")
                    .with_volume_mount(vol_mon_config, "/etc/ceph");

            // MGR (Manager) container - cluster management and dashboard
            // Config-as-Code: Uses injected config files with pre-shared keys
            // DNS wait ensures MON is available before MGR connects
            local mgr_container =
                engine.container("ceph-mgr")
                    .with_image(images.ceph)
                    .with_environment(mgr_env)
                    .with_command([
                        "bash", "-c",
                        "until getent hosts ceph-mon; do echo 'Waiting for MON DNS...'; sleep 2; done; " +
                        inject_config +
                        "exec /opt/ceph-container/bin/entrypoint.sh"
                    ])
                    .with_limits("1.0", "1536M")
                    .with_reservations("0.5", "1024M")
                    .with_port(7000, 7000, "mgr")
                    .with_port(8443, 8443, "dashboard")
                    .with_port(9283, 9283, "prometheus")
                    .with_volume_mount(vol_mgr, "/var/lib/ceph/mgr")
                    .with_volume_mount(vol_mgr_config, "/etc/ceph");

            // OSD (Object Storage Daemon) - actual data storage
            // Config-as-Code: Uses injected config files with pre-shared keys
            // Increased resources to prevent OOM during recovery operations
            // DNS wait ensures MON is available before OSD connects
            local osd_container =
                engine.container("ceph-osd")
                    .with_image(images.ceph)
                    .with_environment(osd_env)
                    .with_command([
                        "bash", "-c",
                        "until getent hosts ceph-mon; do echo 'Waiting for MON DNS...'; sleep 2; done; " +
                        inject_config +
                        "exec /opt/ceph-container/bin/entrypoint.sh"
                    ])
                    .with_limits("2.0", "4096M")
                    .with_reservations("1.0", "2048M")
                    .with_port(6800, 6800, "osd")
                    .with_volume_mount(vol_osd, "/var/lib/ceph/osd")
                    .with_volume_mount(vol_osd_config, "/etc/ceph");

            // RGW (RADOS Gateway) - S3 API endpoint
            // Config-as-Code: Uses injected config files with pre-shared keys
            // DNS wait ensures MON is available before RGW connects
            local rgw_container =
                engine.container("ceph-rgw")
                    .with_image(images.ceph)
                    .with_environment(rgw_env)
                    .with_command([
                        "bash", "-c",
                        "until getent hosts ceph-mon; do echo 'Waiting for MON DNS...'; sleep 2; done; " +
                        inject_config +
                        "exec /opt/ceph-container/bin/entrypoint.sh"
                    ])
                    .with_limits("1.0", "1536M")
                    .with_reservations("0.5", "1024M")
                    .with_port(7480, 7480, "s3")
                    .with_volume_mount(vol_rgw, "/var/lib/ceph/radosgw")
                    .with_volume_mount(vol_rgw_config, "/etc/ceph");

            // Init container - one-time S3 user provisioning
            // IMPORTANT: This container exits with code 0 after completion
            // Orchestrator must NOT restart it (use K8s Job or Compose restart: "no")
            // Config-as-Code: Uses injected config to run radosgw-admin commands
            local init_container =
                engine.container("ceph-init")
                    .with_image(images.ceph)
                    .with_environment({
                        CLUSTER: $["ceph-cluster-id"],
                        FSID: $["ceph-fsid"],
                        KV_TYPE: "none",
                        RGW_ACCESS_KEY: $["ceph-access-key"],
                        RGW_SECRET_KEY: $["ceph-secret-key"],
                    })
                    .with_limits("0.5", "512M")
                    .with_reservations("0.25", "256M")
                    .with_volume_mount(vol_init_config, "/etc/ceph")
                    .with_command([
                        "bash", "-c",
                        inject_config + |||
                            set -e

                            # Wait for cluster health
                            echo "Waiting for Ceph cluster to be healthy..."
                            MAX_ATTEMPTS=60
                            ATTEMPT=0
                            until ceph --cluster ${CLUSTER} health 2>/dev/null | grep -q "HEALTH_OK\|HEALTH_WARN"; do
                                ATTEMPT=$((ATTEMPT+1))
                                if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
                                    echo "ERROR: Cluster failed to become healthy after ${MAX_ATTEMPTS} attempts"
                                    exit 1
                                fi
                                echo "Attempt ${ATTEMPT}/${MAX_ATTEMPTS}: Cluster not ready, retrying in 5s..."
                                sleep 5
                            done
                            echo "Cluster is healthy."

                            # Wait for RGW availability
                            echo "Waiting for RGW to be ready..."
                            ATTEMPT=0
                            until curl -sf http://ceph-rgw:7480 >/dev/null 2>&1; do
                                ATTEMPT=$((ATTEMPT+1))
                                if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
                                    echo "ERROR: RGW failed to become ready after ${MAX_ATTEMPTS} attempts"
                                    exit 1
                                fi
                                echo "Attempt ${ATTEMPT}/${MAX_ATTEMPTS}: RGW not ready, retrying in 5s..."
                                sleep 5
                            done
                            echo "RGW is ready."

                            # Idempotent S3 user creation
                            echo "Provisioning S3 user: ${RGW_ACCESS_KEY}"
                            if radosgw-admin --cluster ${CLUSTER} user info --uid="${RGW_ACCESS_KEY}" >/dev/null 2>&1; then
                                echo "User ${RGW_ACCESS_KEY} already exists, skipping creation."
                            else
                                echo "Creating new S3 user: ${RGW_ACCESS_KEY}"
                                radosgw-admin --cluster ${CLUSTER} user create \
                                    --uid="${RGW_ACCESS_KEY}" \
                                    --display-name="Object Storage User" \
                                    --access-key="${RGW_ACCESS_KEY}" \
                                    --secret-key="${RGW_SECRET_KEY}"
                                echo "S3 user created successfully."
                            fi

                            echo "Initialization complete. Exiting."
                            exit 0
                        |||,
                    ]);

            // Container sets - each daemon gets its own for K8s node distribution
            local mon_containerSet = engine.containers("ceph-mon", [mon_container]);
            local mgr_containerSet = engine.containers("ceph-mgr", [mgr_container]);
            local osd_containerSet = engine.containers("ceph-osd", [osd_container]);
            local rgw_containerSet = engine.containers("ceph-rgw", [rgw_container]);
            local init_containerSet = engine.containers("ceph-init", [init_container]);

            // Services - expose daemon ports for inter-daemon communication
            local mon_service =
                engine.service(mon_containerSet)
                    .with_port(6789, 6789, "mon")
                    .with_port(3300, 3300, "mon-msgr2");

            local mgr_service =
                engine.service(mgr_containerSet)
                    .with_port(7000, 7000, "mgr")
                    .with_port(8443, 8443, "dashboard")
                    .with_port(9283, 9283, "prometheus");

            local osd_service =
                engine.service(osd_containerSet)
                    .with_port(6800, 6800, "osd");

            local rgw_service =
                engine.service(rgw_containerSet)
                    .with_port(7480, 7480, "s3");

            engine.resources([

                // Data volumes
                vol_mon,
                vol_mgr,
                vol_osd,
                vol_rgw,

                // Config volumes (isolated, no sharing)
                vol_mon_config,
                vol_mgr_config,
                vol_osd_config,
                vol_rgw_config,
                vol_init_config,

                // Container sets
                mon_containerSet,
                mgr_containerSet,
                osd_containerSet,
                rgw_containerSet,
                init_containerSet,

                // Services
                mon_service,
                mgr_service,
                osd_service,
                rgw_service,

            ])
    },
}
