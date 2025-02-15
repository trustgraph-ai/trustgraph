
import argparse
import time
import os
from yaml import load, Loader
import json
import multiprocessing
from multiprocessing.connection import wait

import importlib

from .. log_level import LogLevel

def fn(module_name, class_name, params, w):

    print(f"Starting {module_name}...")

    if "log_level" in params:
        params["log_level"] = LogLevel(params["log_level"])

    while True:

        try:

            print(f"Starting {class_name} using {module_name}...")

            module = importlib.import_module(module_name)
            class_object = getattr(module, class_name)

            processor = class_object(**params)

            processor.run()
            print(f"{module_name} stopped.")

        except Exception as e:
            print("Exception:", e)

        print("Restarting in 10...")

        time.sleep(10)

    print("Closing")
    w.close()

class Processing:

    def __init__(
            self,
            pulsar_host,
            log_level,
            file,
            pulsar_api_key=None,
    ):
        self.pulsar_host = pulsar_host
        self.log_level = log_level
        self.file = file
        self.pulsar_api_key = pulsar_api_key
        self.defs = load(open(file, "r"), Loader=Loader)

    def run(self):

        procs = []
        readers = []
        services = []

        for service in self.defs["services"]:

            sdef = self.defs["services"][service]

            params = {
                "pulsar_host": self.pulsar_host,
                "pulsar_api_key": self.pulsar_api_key,
                "log_level": str(self.log_level),
            }

            if "parameters" in sdef:
                for par in sdef["parameters"]:
                    params[par] = sdef["parameters"][par]

            module_name = sdef["module"]
            class_name = sdef.get("class", "Processor")

            r, w = multiprocessing.Pipe(duplex=False)

            process = multiprocessing.Process(
                target=fn,
                args=(module_name, class_name, params, w)
            )
            process.start()

            w.close()

            procs.append(process)
            services.append(service)
            readers.append(r)
            
        wait_for = len(readers)

        while wait_for > 0:

            ret = wait(readers)

            for r in ret:

                try:
                    msg = r.recv()
                except EOFError:
                    readers.remove(r)
                    wait_for -= 1

        print("All processes exited")

        for p in procs:
            p.join()

    def __del__(self):
        pass

def run():

    # Seems not to work.
#     multiprocessing.set_start_method('spawn')

    parser = argparse.ArgumentParser(
        prog='run-processing',
        description=__doc__,
    )

    default_pulsar_host = os.getenv("PULSAR_HOST", 'pulsar://pulsar:6650')
    default_pulsar_api_key = os.getenv("PULSAR_API_KEY", None)

    parser.add_argument(
        '-p', '--pulsar-host',
        default=default_pulsar_host,
        help=f'Pulsar host (default: {default_pulsar_host})',
    )
    
    parser.add_argument(
        '--pulsar-api-key',
        default=default_pulsar_api_key,
        help=f'Pulsar API key',
    )

    parser.add_argument(
        '-l', '--log-level',
        type=LogLevel,
        default=LogLevel.INFO,
        choices=list(LogLevel),
        help=f'Output queue (default: info)'
    )

    parser.add_argument(
        '-f', '--file',
        default="processing.yaml",
        help=f'Processing definition file (default: processing.yaml)'
    )

    args = parser.parse_args()

    while True:

        try:
            p = Processing(
                pulsar_host=args.pulsar_host,
                pulsar_api_key=args.pulsar_api_key,
                file=args.file,
                log_level=args.log_level,
            )

            p.run()

            print("Finished.")
            break

        except Exception as e:

            print("Exception:", e, flush=True)
            print("Will retry...", flush=True)

        time.sleep(10)

