
import json
import logging
import argparse
import tabulate

from . import Index

from . import Generator, Packager

def list():

    parser = argparse.ArgumentParser(
        prog="tg-show-config-params",
        description=__doc__
    )

    args = parser.parse_args()
    args = vars(args)

    platforms = [
        (v.name, v.description)
        for v in Index.get_platforms()
    ]

    templates = [
        (v.name, v.description, v.status, v.version)
        for v in Index.get_templates()
    ]

    print()
    print("Platforms:")
    print(tabulate.tabulate(
        platforms,
        tablefmt="pretty",
        headers=["name", "description", "status", "version"],
        maxcolwidths=[None, 40],
        stralign="left"
    ))

    print()
    print("Templates:")
    print(tabulate.tabulate(
        templates, tablefmt="pretty",
        headers=["tpl", "description", "status", "version"],
        maxcolwidths=[None, 60],
        stralign="left"
    ))

    print()

    latest = Index.get_latest()
    if latest:
        print("Latest version:", latest.version)

    stable = Index.get_latest_stable()
    if stable:
        print("Latest stable:", stable.version)

    print()

