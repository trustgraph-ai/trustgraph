
import logging

from . api import Api

def run_service():

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(message)s"
    )

    logging.info("Starting...")

    a = Api(port=8080)

    a.run()

