
import logging
import argparse
from prometheus_client import start_http_server

from . api import Api

default_api_gateway = "http://api-gateway:8088/"
default_port = 8888

def run():

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )

    parser = argparse.ArgumentParser(
        prog="workbench-ui",
        description=__doc__
    )
    
    parser.add_argument(
        '-g', '--gateway',
        default=default_api_gateway,
        help=f'API host (default: {default_api_gateway})',
    )

    parser.add_argument(
        '--port',
        type=int,
        default=default_port,
        help=f'Port number to listen on (default: {default_port})',
    )

    parser.add_argument(
        '--metrics',
        action=argparse.BooleanOptionalAction,
        default=True,
        help=f'Metrics enabled (default: true)',
    )

    parser.add_argument(
        '-P', '--metrics-port',
        type=int,
        default=8000,
        help=f'Prometheus metrics port (default: 8000)',
    )

    args = parser.parse_args()
    args = vars(args)

    if args["metrics"]:
        start_http_server(args["metrics_port"])

    logging.info("Starting...")

    a = Api(**args)
    a.run()

if __name__ == '__main__':
    run()

