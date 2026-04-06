
import json
import logging
import argparse
import sys

from . import Generator, Packager

def run():

    parser = argparse.ArgumentParser(
        prog="tg-build-deployment",
        description=__doc__
    )

    parser.add_argument(
        '-v', '--version',
        help=f'Version'
    )

    parser.add_argument(
        '-i', '--input',
        default="config.json",
        help=f'Input configuration name (default: config.json)'
    )

    parser.add_argument(
        '-o', '--output',
        default="deploy.zip",
        help=f'Output file name (default: deploy.zip)'
    )

    parser.add_argument(
        '-t', '--template',
        help=f'Template to use'
    )

    parser.add_argument(
        '-p', '--platform',
        default="docker-compose",
        help=f'Platform (default: docker-compose)'
    )

    parser.add_argument(
        '--latest',
        action='store_true',
        help="Latest version",
    )

    parser.add_argument(
        '--latest-stable',
        action='store_true',
        help="Latest stable version",
    )

    parser.add_argument(
        '-O', '--output-tg-config',
        action='store_true',
        help="Output only TrustGraph configuration to stdout",
    )

    parser.add_argument(
        '-R', '--output-resources',
        action='store_true',
        help="Output only resources (docker-compose.yaml or resources.yaml) to stdout",
    )

    try:

        args = parser.parse_args()
        args = vars(args)

        input = args["input"]

        with open(input) as f:
            config = f.read()

        output = args["output"]
        output_tg_config = args.get("output_tg_config", False)
        output_resources = args.get("output_resources", False)

        # Configure logging only if not outputting to stdout
        if not output_tg_config and not output_resources:
            logging.basicConfig(level=logging.INFO, format='%(message)s')
        else:
            # Suppress all logging when outputting to stdout
            logging.basicConfig(level=logging.CRITICAL)

        del args["input"]
        del args["output"]
        del args["output_tg_config"]
        del args["output_resources"]

        a = Packager(**args)
        
        if output_tg_config:
            a.write_tg_config(config)
        elif output_resources:
            a.write_resources(config)
        else:
            a.write(config, output)

    except Exception as e:

        print(f"Exception: {e}", file=sys.stderr)
        sys.exit(1)

