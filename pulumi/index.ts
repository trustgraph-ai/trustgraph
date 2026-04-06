
import * as pulumi from "@pulumi/pulumi";
import * as gcp from "@pulumi/gcp";
import { local } from "@pulumi/command";
import * as fs from 'fs';

const cfg = new pulumi.Config();

function get(tag : string) {

    let val = cfg.get(tag);

    if (!val) {
        console.log("ERROR: The '" + tag + "' config is mandatory");
        throw "The '" + tag + "' config is mandatory";
    }

    return val;

}

const imageVersion = process.env.IMAGE_VERSION;
if (!imageVersion)
    throw Error("IMAGE_VERSION not defined");

const repo = get("artifact-repo");
const artifactRepoRegion = get("artifact-repo-region");
const artifactName = get("artifact-name");
const hostname = get("hostname");
const managedZone = get("managed-zone");
const project = get("gcp-project");
const region = get("gcp-region");
const cloudRunRegion = get("cloud-run-region");
const environment = get("environment");
const domain = get("domain");
const minScale = get("min-scale");
const maxScale = get("max-scale");

const provider = new gcp.Provider(
    "gcp",
    {
	project: project,
	region: region,
    }
);

const artifactRepo = new gcp.artifactregistry.Repository(
    "artifact-repo",
    {
	description: "repository for " + environment,
	format: "DOCKER",
	location: artifactRepoRegion,
	repositoryId: artifactName,
	cleanupPolicies: [
	    {
		id: "keep-minimum-versions",
		action: "KEEP",
		mostRecentVersions: {
		    keepCount: 5,
		},
	    }
	],
    },
    {
	provider: provider,
    }
);

const localImageName = "localhost/config-svc:" + imageVersion;

const imageName = repo + "/config-svc:" + imageVersion;

const taggedImage = new local.Command(
    "podman-tag-command",
    {
	create: "podman tag " + localImageName + " " + imageName,
    }
);

const image = new local.Command(
    "podman-push-command",
    {
	create: "podman push " + imageName,
    },
    {
	dependsOn: [taggedImage, artifactRepo],
    }
);

const svcAccount = new gcp.serviceaccount.Account(
    "service-account",
    {
	accountId: "config-svc-" + environment,
	displayName: "Config service",
	description: "Config service",
    },
    {
	provider: provider,
    }
);

const service = new gcp.cloudrun.Service(
    "service",
    {
	name: "config-svc-" + environment,
	location: cloudRunRegion,
	template: {
	    metadata: {
		labels: {
		    version: "v" + imageVersion.replace(/\./g, "-"),
		},		
		annotations: {

		    // Scale attributes
                    "autoscaling.knative.dev/minScale": minScale,
                    "autoscaling.knative.dev/maxScale": maxScale,

		    // 2nd generation.  Need to specify at least 512MB RAM.
                    // Going back to gen1 because faster cold starts
		    "run.googleapis.com/execution-environment": "gen1",

		}
	    },
            spec: {
		containerConcurrency: 100,
		timeoutSeconds: 300,
		serviceAccountName: svcAccount.email,
		containers: [
		    {
			image: imageName,
			ports: [
                            {
				"name": "http1", // Must be http1 or h2c.
				"containerPort": 8080,
                            }
			],
			resources: {
                            limits: {
				cpu: "1000m",
				memory: "512Mi",
                            }
			},
		    }
		],
            },
	},
    },
    {
	provider: provider,
	dependsOn: [image],
    }
);

const allUsersPolicy = gcp.organizations.getIAMPolicy(
    {
	bindings: [{
            role: "roles/run.invoker",
            members: ["allUsers"],
	}],
    },
    {
	provider: provider,
    }
);

const noAuthPolicy = new gcp.cloudrun.IamPolicy(
    "no-auth-policy",
    {
	location: service.location,
	project: service.project,
	service: service.name,
	policyData: allUsersPolicy.then(pol => pol.policyData),
    },
    {
	provider: provider,
    }
);

////////////////////////////////////////////////////////////////////////////

const domainMapping = new gcp.cloudrun.DomainMapping(
    "domain-mapping",
    {
	name: hostname,
	location: cloudRunRegion,
	metadata: {
	    namespace: project,
	},
	spec: {
	    routeName: service.name,
	}
    },
    {
	provider: provider
    }
);

const zone = gcp.dns.getManagedZoneOutput(
    {
	name: managedZone,
    },
    {
	provider: provider,
    }
);

////////////////////////////////////////////////////////////////////////////

domainMapping.statuses.apply(
    ss => ss[0].resourceRecords
).apply(
    rrs => {
	if (rrs) {

	    let mapping : { [k : string] : string[] } = {};
	    
	    for(var i = 0; i < rrs.length; i++) {
		if (rrs[i].rrdata) {

		    const rr = rrs[i].rrdata;
		    const tp = rrs[i].type;

		    if (!rr || !tp) continue;

		    if (mapping[tp])
			mapping[tp].push(rr);
		    else
			mapping[tp] = [rr];

		}
	    }

	    for (let tp in mapping) {

		const recordSet = new gcp.dns.RecordSet(
		    "resource-record-" + tp,
		    {
			name: hostname + ".",
			managedZone: zone.name,
			type: tp,
			ttl: 300,
			rrdatas: mapping[tp],
		    },
		    {
			provider: provider,
		    }
		);

	    }

	}

    }
);

////////////////////////////////////////////////////////////////////////////

const serviceMon = new gcp.monitoring.GenericService(
    "service-monitoring",
    {
	basicService: {
            serviceLabels: {
		service_name: service.name,
		location: cloudRunRegion,
            },
            serviceType: "CLOUD_RUN",
	},
	displayName: "Config service (" + environment + ")",
	serviceId: "config-service-" + environment + "-mon",
	userLabels: {
	    "service": service.name,
	    "application": "config-svc",
	    "environment": environment,
	},
    },
    {
	provider: provider,
    }
);

const latencySlo = new gcp.monitoring.Slo(
    "latency-slo",
    {
	service: serviceMon.serviceId,
	sloId: "config-service-" + environment + "-latency-slo",
	displayName: "Config service latency (" + environment + ")",
	goal: 0.95,
	rollingPeriodDays: 5,
	basicSli: {
	    latency: {
		threshold: "2s"
	    }
	},
    },
    {
	provider: provider,
    }
);

const availabilitySlo = new gcp.monitoring.Slo(
    "availability-slo",
    {
	service: serviceMon.serviceId,
	sloId: "config-service-" + environment + "-availability-slo",
	displayName: "Config service availability (" + environment + ")",
	goal: 0.95,
	rollingPeriodDays: 5,
	windowsBasedSli: {
	    windowPeriod: "3600s",
	    goodTotalRatioThreshold: {
		basicSliPerformance: {
		    availability: {
		    }
		},
		threshold: 0.9,
	    }
	}
    },
    {
	provider: provider,
    }
);

