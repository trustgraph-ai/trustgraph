local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";

{

    volumes +: {
	etcd: {},
	"minio-data": {},
	milvus: {},
    },

    services +: {

	etcd: base + {
	    image: images.etcd,
	    command: [
		"etcd",
		"-advertise-client-urls=http://127.0.0.1:2379",
		"-listen-client-urls",
		"http://0.0.0.0:2379",
		"--data-dir",
		"/etcd",
	    ],
	    environment: {
		ETCD_AUTO_COMPACTION_MODE: "revision",
		ETCD_AUTO_COMPACTION_RETENTION: "1000",
		ETCD_QUOTA_BACKEND_BYTES: "4294967296",
		ETCD_SNAPSHOT_COUNT: "50000"
	    },
	    ports: [
                {
                    src: 2379,
                    dest: 2379,
                    name: "api",
                }
	    ],
	    volumes: [
		"etcd:/etcd"
	    ],
            deploy: {
		resources: {
		    limits: {
			cpus: '1.0',
			memory: '128M'
		    },
		    reservations: {
			cpus: '0.25',
			memory: '128M'
		    }
		},
	    },
        },

	minio: base + {
	    image: images.minio,
	    command: [
		"minio",
		"server",
		"/minio_data",
		"--console-address",
		":9001",
	    ],
	    environment: {
		MINIO_ROOT_USER: "minioadmin",
		MINIO_ROOT_PASSWORD: "minioadmin",
	    },
	    ports: [
                {
                    src: 9001,
                    dest: 9001,
                    name: "api",
                }
	    ],
	    volumes: [
		"minio-data:/minio_data",
	    ],	
            deploy: {
		resources: {
		    limits: {
			cpus: '0.5',
			memory: '128M'
		    },
		    reservations: {
			cpus: '0.25',
			memory: '128M'
		    }
		}
            },
	},

	milvus: base + {
	    image: images.milvus,
	    command: [
		"milvus", "run", "standalone"
	    ],
	    environment: {
		ETCD_ENDPOINTS: "etcd:2379",
		MINIO_ADDRESS: "minio:9000",
	    },
	    ports: [
                {
                    src: 9091,
                    dest: 9091,
                    name: "api",
                },
                {
                    src: 19530,
                    dest: 19530,
                    name: "api2",
                }
	    ],
	    volumes: [
		"milvus:/var/lib/milvus"
	    ],
            deploy: {
		resources: {
		    limits: {
			cpus: '1.0',
			memory: '256M'
		    },
		    reservations: {
			cpus: '0.5',
			memory: '256M'
		    }
		}
            },
	},

    },

}
