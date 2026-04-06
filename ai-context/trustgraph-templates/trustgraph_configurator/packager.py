
import pathlib
import yaml
import json
import logging
import importlib.resources
from io import BytesIO
import zipfile
import os

from . import Generator
from . index import Index

logger = logging.getLogger("packager")
logger.setLevel(logging.INFO)

class Packager:

    def __init__(
            self, version, template, platform,
            latest, latest_stable,
    ):

        if latest:
            version = Index.get_latest().version
            template = Index.get_latest().name

        if latest_stable:
            version = Index.get_latest_stable().version
            template = Index.get_latest_stable().name

        if template is None:
            raise RuntimeError(
                "You must latest, latest-stable or select a template."
            )

        if version is None:
            versions = [
                v
                for v in Index.get_templates()
                if v.name == template
            ]
            if len(versions) < 1:
                raise RuntimeError(f"Template {template} not known")
            version = versions[-1].version

        files = importlib.resources.files()

        self.template = template
        self.version = version
        self.templates = files.joinpath("templates").joinpath(template)
        self.resources = files.joinpath("resources").joinpath(template)
        self.platform = platform

    def fetch(self, dir, filename):

        if filename == "trustgraph/config.json":
            config = self.generate_trustgraph_config(self.config)
            config = json.dumps(config)
            path = self.templates.joinpath(dir, filename)
            return str(path), config.encode("utf-8")
        
        if filename == "config.json":
            path = self.templates.joinpath(dir, filename)
            return str(path), self.config.encode("utf-8")
        
        if filename == "version.jsonnet":
            path = self.templates.joinpath(dir, filename)
            return str(path), f"\"{self.version}\"".encode("utf-8")

        if dir:
            candidates = [
                self.templates.joinpath(dir, filename),
                self.templates.joinpath(filename),
                self.resources.joinpath(dir, filename),
                self.resources.joinpath(filename),
            ]
        else:
            candidates = [
                self.templates.joinpath(filename)
            ]

        try:

            if filename == "vertexai/private.json":
                private_json = "Put your GCP private.json here"
                return str(candidates[0]), (private_json.encode("utf-8"))

            for c in candidates:
                logger.debug("Try: %s", c)

                if os.path.isfile(c):
                    with open(c, "rb") as f:
                        logger.debug("Loading: %s", c)
                        return str(c), f.read()

            raise RuntimeError(
                f"Could not load file={filename} dir={dir}"
            )
                
        except:

            path = os.path.join(self.templates, filename)
            logger.debug("Try: %s", path)
            with open(path, "rb") as f:
                logger.debug("Loaded: %s", path)
                return str(path), f.read()

    def process_renderer(self, renderer_name):
        gen = Generator(fetch=self.fetch)
        renderers_dir = self.templates.joinpath("renderers")
        if renderers_dir.exists():
            path = self.templates.joinpath(f"renderers/{renderer_name}")
            return gen.process_file(path)
        else:
            path = self.templates.joinpath(renderer_name)
            return gen.process(path.read_text())

    def generate_trustgraph_config(self, config):
        config = config.encode("utf-8")
        return self.process_renderer("config-to-tg-configuration.jsonnet")

    def generate_additionals(self, config):
        config = config.encode("utf-8")
        return self.process_renderer("config-to-additionals.jsonnet")

    def generate_resources(self, config):
        config = config.encode("utf-8")
        return self.process_renderer(f"config-to-{self.platform}.jsonnet")
    
    def write(self, config, output):

        try:

            data = self.generate(config)

            print("Writing output file...")

            with open(output, "wb") as f:
                f.write(data)

            print(f"Wrote {output}.")

        except Exception as e:
            logging.error(f"Exception: {e}")
            raise e
   
    def generate(self, config):

        self.config = config

        logger.info(f"Generating for platform={self.platform} "
                    f"template={self.template} "
                    f"version={self.version}")

        try:

            if self.platform in set(["docker-compose", "podman-compose"]):
                data = self.generate_docker_compose(
                    "docker-compose", self.version, config
                )
            elif self.platform in set([
                    "minikube-k8s", "gcp-k8s", "aks-k8s", "eks-k8s",
                    "scw-k8s", "ovh-k8s"
            ]):
                data = self.generate_k8s(
                    self.platform, self.version, config
                )
            else:
                raise RuntimeError("Bad platform")

            return data

        except Exception as e:
            logging.error(f"Exception: {e}")
            raise e
    
    def write_tg_config(self, config):
        """Output only the TrustGraph configuration to stdout"""
        try:
            self.config = config
            tg_config_json = self.generate_trustgraph_config(config)
            tg_config_file = json.dumps(tg_config_json, indent=4)
            print(tg_config_file)
        except Exception as e:
            logging.error(f"Exception: {e}")
            raise e
    
    def write_resources(self, config):
        """Output only the platform resources to stdout"""
        try:
            self.config = config
            
            if self.platform in set(["docker-compose", "podman-compose"]):
                compose_json = self.generate_resources(config)
                compose_file = yaml.dump(compose_json)
                print(compose_file)
            elif self.platform in set([
                    "minikube-k8s", "gcp-k8s", "aks-k8s", "eks-k8s",
                    "scw-k8s", "ovh-k8s"
            ]):
                processed = self.generate_resources(config)
                y = yaml.dump(processed)
                print(y)
            else:
                raise RuntimeError("Bad platform")
                
        except Exception as e:
            logging.error(f"Exception: {e}")
            raise e

    def generate_docker_compose(self, platform, version, config):

        compose_json = self.generate_resources(config)
        compose_file = yaml.dump(compose_json)

        # Generate TG config for versions after 1.1...
        if version[:2] != "0." and version[:3] != "1.0":
            tg_config_json = self.generate_trustgraph_config(config)
            tg_config_file = json.dumps(tg_config_json, indent=4)

        # Check if config-to-additionals.jsonnet exists for this version
        renderers_dir = self.templates.joinpath("renderers")
        if renderers_dir.exists():
            additionals_path = self.templates.joinpath("renderers/config-to-additionals.jsonnet")
        else:
            additionals_path = self.templates.joinpath("config-to-additionals.jsonnet")
        has_additionals = os.path.isfile(additionals_path)

        # Generate additional config files from configVolume parts (if supported)
        additionals = self.generate_additionals(config) if has_additionals else []

        mem = BytesIO()

        with zipfile.ZipFile(mem, mode='w') as out:

            def output(name, content):
                logger.info(f"Adding {name}...")
                out.writestr(name, content)

            output("docker-compose.yaml", compose_file)

            # Add seperate TG config for versions after 1.1...
            if version[:2] != "0." and version[:3] != "1.0":
                output("trustgraph/config.json", tg_config_file)

            # Add generated config files from additionals (if available)
            # Skip trustgraph/config.json since it's handled above
            for item in additionals:
                if item['path'] != 'trustgraph/config.json':
                    output(item['path'], item['content'])

            # Fallback: Walk resources directory if additionals not available
            # This maintains backward compatibility with older versions
            if not has_additionals and os.path.isdir(self.resources):
                for root, dirs, files in os.walk(self.resources):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, self.resources)
                        with open(file_path, 'r') as f:
                            content = f.read()
                        output(rel_path, content)

        logger.info("Generation complete.")

        return mem.getvalue()

    def generate_k8s(self, platform, version, config):

        processed = self.generate_resources(config)

        y = yaml.dump(processed)

        mem = BytesIO()

        with zipfile.ZipFile(mem, mode='w') as out:

            def output(name, content):
                logger.info(f"Adding {name}...")
                out.writestr(name, content)

            fname = "resources.yaml"

            output(fname, y)

        logger.info("Generation complete.")

        return mem.getvalue()

