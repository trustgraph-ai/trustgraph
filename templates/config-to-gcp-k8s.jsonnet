
local engine = import "k8s.jsonnet";
local decode = import "decode-config.jsonnet";
local components = import "components.jsonnet";

// Import config
local config = import "config.json";

// Produce patterns from config
local patterns = decode(config);

local ns = {
    apiVersion: "v1",
    kind: "Namespace",
    metadata: {
        name: "trustgraph",
    },
    "spec": {
    },
};

local sc = {
    apiVersion: "storage.k8s.io/v1",
    kind: "StorageClass",
    metadata: {
        name: "tg",
    },
    provisioner: "pd.csi.storage.gke.io",
    parameters: {
        type: "pd-balanced",
        "csi.storage.k8s.io/fstype": "ext4",
    },
    reclaimPolicy: "Delete",
    volumeBindingMode: "WaitForFirstConsumer",
};

//patterns["pulsar"].create(engine)

// Extract resources usnig the engine
local resources = std.flattenArrays([
    p.create(engine) for p in std.objectValues(patterns)
]);

local resourceList = {
    apiVersion: "v1",
    kind: "List",
    items: [ns, sc] + resources,
};


resourceList

