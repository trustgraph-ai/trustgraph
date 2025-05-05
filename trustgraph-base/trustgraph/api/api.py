
import requests
import json
import base64
import time

from . library import Library
from . flow import Flow
from . config import Config
from . exceptions import *
from . types import *

def check_error(response):

    if "error" in response:

        try:
            msg = response["error"]["message"]
            tp = response["error"]["type"]
        except:
            raise ApplicationException(response["error"])

        raise ApplicationException(f"{tp}: {msg}")

class Api:

    def __init__(self, url="http://localhost:8088/"):

        self.url = url

        if not url.endswith("/"):
            self.url += "/"

        self.url += "api/v1/"

    def flow(self):
        return Flow(api=self)

    def config(self):
        return Config(api=self)

    def request(self, path, request):

        url = f"{self.url}{path}"

#        print("uri:", url)
#        print(json.dumps(request, indent=4))

        # Invoke the API, input is passed as JSON
        resp = requests.post(url, json=request)

        # Should be a 200 status code
        if resp.status_code != 200:
            raise ProtocolException(f"Status code {resp.status_code}")

#        print(resp.text)

        try:
            # Parse the response as JSON
            object = resp.json()
        except:
            raise ProtocolException(f"Expected JSON response")

        check_error(object)

        return object

    def library(self):
        return Library(self)
