"""
Sets a prompt template.
"""

import argparse
import os
from trustgraph.api import Api, ConfigKey, ConfigValue
import json
import tabulate
import textwrap

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')

def set_system(url, system):

    api = Api(url).config()

    api.put([
        ConfigValue(type="prompt", key="system", value=json.dumps(system))
    ])

    print("System prompt set.")

def set_prompt(url, id, prompt, response, schema):

    api = Api(url).config()

    values = api.get([
        ConfigKey(type="prompt", key="template-index")
    ])

    ix = json.loads(values[0].value)

    object = {
        "id": id,
        "prompt": prompt,
    }

    if response:
        object["response-type"] = response
    else:
        object["response-type"] = "text"

    if schema:
        object["schema"] = schema

    if id not in ix:
        ix.append(id)

    values = api.put([
        ConfigValue(
            type="prompt", key="template-index", value=json.dumps(ix)
        ),
        ConfigValue(
            type="prompt", key=f"template.{id}", value=json.dumps(object)
        )
    ])

    print("Prompt set.")

def main():

    parser = argparse.ArgumentParser(
        prog='tg-set-prompt',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '--id',
        help=f'Prompt ID',
    )

    parser.add_argument(
        '--response',
        help=f'Response form, should be one of: text json',
    )

    parser.add_argument(
        '--schema',
        help=f'JSON schema, for JSON response form',
    )

    parser.add_argument(
        '--prompt',
        help=f'Prompt template',
    )

    parser.add_argument(
        '--system',
        help=f'System prompt',
    )

    args = parser.parse_args()

    try:

        if args.system:
            if args.id or args.prompt or args.schema or args.response:
                raise RuntimeError("Can't use --system with other args")
                
            set_system(
                url=args.api_url, system=args.system
            )

        else:

            if args.id is None:
                raise RuntimeError("Must specify --id for prompt")

            if args.prompt is None:
                raise RuntimeError("Must specify --prompt for prompt")

            if args.response:
                if args.response not in ["text", "json"]:
                    raise RuntimeError("Response must be one of: text json")
                    
            if args.schema:
                try:
                    schobj = json.loads(args.schema)
                except:
                    raise RuntimeError("JSON schema must be valid JSON")
            else:
                schobj = None

            set_prompt(
                url=args.api_url, id=args.id, prompt=args.prompt,
                response=args.response, schema=schobj
            )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()