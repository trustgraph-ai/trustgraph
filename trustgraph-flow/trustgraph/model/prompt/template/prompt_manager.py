
import ibis
import json
from jsonschema import validate

from trustgraph.clients.llm_client import LlmClient

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

    def __init__(self, llm, config):
        self.llm = llm
        self.config = config
        self.terms = config.global_terms

        self.prompts = config.prompts

        try:
            self.system_template = ibis.Template(config.system_template)
        except:
            raise RuntimeError("Error in system template")

        self.templates = {}
        for k, v in self.prompts.items():
            try:
                self.templates[k] = ibis.Template(v.template)
            except:
                raise RuntimeError(f"Error in template: {k}")

            if v.terms is None:
                v.terms = {}

    def invoke(self, id, input):

        if id not in self.prompts:
            raise RuntimeError("ID invalid")

        terms = self.terms | self.prompts[id].terms | input

        resp_type = self.prompts[id].response_type

        prompt = {
            "system": self.system_template.render(terms),
            "prompt": self.templates[id].render(terms)
        }

        resp = self.llm.request(**prompt)

        if resp_type == "text":
            return resp

        if resp_type != "json":
            raise RuntimeError(f"Response type {resp_type} not known")

        try:
            obj = json.loads(resp)
        except:
            raise RuntimeError("JSON parse fail")

        print(resp)
        print(obj)
        if self.prompts[id].schema:
            try:
                print(self.prompts[id].schema)
                validate(instance=obj, schema=self.prompts[id].schema)
            except Exception as e:
                raise RuntimeError(f"Schema validation fail: {e}")

        return obj

