"""
Sets a model's token costs.
"""

import argparse
import os
from trustgraph.api import Api, ConfigKey, ConfigValue
import json
import tabulate
import textwrap

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)

def set_costs(api_url, model, input_costs, output_costs, token=None):

    api = Api(api_url, token=token).config()

    api.put([
        ConfigValue(
            type="token-costs", key=model,
            value=json.dumps({
                "input_price": input_costs / 1000000,
                "output_price": output_costs / 1000000,
            })
        ),
    ])

def set_prompt(url, id, prompt, response, schema):

    api = Api(url)

    values = api.config_get([
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

    values = api.config_put([
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
        prog='tg-set-token-costs',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '--model',
        required=True,
        help=f'Model ID',
    )

    parser.add_argument(
        '-i', '--input-costs',
        required=True,
        type=float,
        help=f'Input costs in $ per 1M tokens',
    )

    parser.add_argument(
        '-o', '--output-costs',
        required=True,
        type=float,
        help=f'Input costs in $ per 1M tokens',
    )

    parser.add_argument(
        '-t', '--token',
        default=default_token,
        help='Authentication token (default: $TRUSTGRAPH_TOKEN)',
    )

    args = parser.parse_args()

    try:

        set_costs(**vars(args))

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()