
local k8s = import "k8s.jsonnet";

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
    provisioner: "disk.csi.azure.com",
    parameters: {
        // Standard disks (spinning magnetic), Locally Redundant Storage
        // Cheapest, basically
        skuName: "Standard_LRS",
    },
    reclaimPolicy: "Delete",
    volumeBindingMode: "WaitForFirstConsumer",
};

k8s + {

    // Extract resources usnig the engine
    package:: function(patterns)
        local resources = [sc, ns] + std.flattenArrays([
            p.create(self) for p in std.objectValues(patterns)
        ]);
        local resourceList = {
            apiVersion: "v1",
            kind: "List",
            items: [ns, sc] + resources,
        };
        resourceList

}

