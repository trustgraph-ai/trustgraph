
import ibis
import json
from jsonschema import validate
import re
import logging

# Module logger
logger = logging.getLogger(__name__)

class PromptConfiguration:
    def __init__(self, system_template, global_terms={}, prompts={}):
        self.system_template = system_template
        self.global_terms = global_terms
        self.prompts = prompts

class Prompt:
    def __init__(self, template, response_type = "text", terms=None, schema=None):
        self.template = template
        self.response_type = response_type
        self.terms = terms
        self.schema = schema

class PromptManager:

    def __init__(self):

        self.load_config({})

    def load_config(self, config):

        try:
            system = json.loads(config["system"])
        except:
            system = "Be helpful."

        try:
            ix = json.loads(config["template-index"])
        except:
            ix = []

        prompts = {}

        for k in ix:

            pc = config[f"template.{k}"]
            data = json.loads(pc)

            prompt = data.get("prompt")
            rtype = data.get("response-type", "text")
            schema = data.get("schema", None)

            prompts[k] = Prompt(
                template = prompt,
                response_type = rtype,
                schema = schema,
                terms = {}
            )

        self.config = PromptConfiguration(
            system,
            {},
            prompts
        )

        self.terms = self.config.global_terms
        self.prompts = self.config.prompts

        try:
            self.system_template = ibis.Template(self.config.system_template)
        except:
            raise RuntimeError("Error in system template")

        self.templates = {}
        for k, v in self.prompts.items():
            try:
                self.templates[k] = ibis.Template(v.template)
            except Exception as e:
                raise RuntimeError(f"Error in template: {k}: {e}")

            if v.terms is None:
                v.terms = {}

    def parse_json(self, text):
        json_match = re.search(r'```(?:json)?(.*?)```', text, re.DOTALL)
    
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            # If no delimiters, assume the entire output is JSON
            json_str = text.strip()

        return json.loads(json_str)

    def render(self, id, input):

        if id not in self.prompts:
            raise RuntimeError("ID invalid")

        terms = self.terms | self.prompts[id].terms | input

        resp_type = self.prompts[id].response_type

        return self.templates[id].render(terms)

    async def invoke(self, id, input, llm):

        logger.debug("Invoking prompt template...")

        terms = self.terms | self.prompts[id].terms | input

        resp_type = self.prompts[id].response_type

        prompt = {
            "system": self.system_template.render(terms),
            "prompt": self.render(id, input)
        }

        resp = await llm(**prompt)

        if resp_type == "text":
            return resp

        if resp_type != "json":
            raise RuntimeError(f"Response type {resp_type} not known")

        try:
            obj = self.parse_json(resp)
        except:
            logger.error(f"JSON parse failed: {resp}")
            raise RuntimeError("JSON parse fail")

        if self.prompts[id].schema:
            try:
                validate(instance=obj, schema=self.prompts[id].schema)
                logger.debug("Schema validation successful")
            except Exception as e:
                raise RuntimeError(f"Schema validation fail: {e}")

        return obj

