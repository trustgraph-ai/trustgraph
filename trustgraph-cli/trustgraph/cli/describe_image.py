"""
Invokes the image-to-text service to produce a text description of an
image file.  The image MIME type is guessed from the filename unless
specified.
"""

import argparse
import mimetypes
import os
from trustgraph.api import Api, TrustGraphException

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def query(url, flow_id, image, mime_type, prompt=None, system=None,
          token=None, workspace="default"):

    with open(image, "rb") as f:
        image_data = f.read()

    if mime_type is None:
        mime_type, _ = mimetypes.guess_type(image)
        if mime_type is None:
            raise RuntimeError(
                f"Can't guess MIME type of {image}, specify --mime-type"
            )

    api = Api(url=url, token=token, workspace=workspace)
    socket = api.socket()
    flow = socket.flow(flow_id)

    try:

        result = flow.image_to_text(
            image=image_data,
            mime_type=mime_type,
            prompt=prompt,
            system=system,
        )

        print(result.text)

    finally:
        socket.close()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-describe-image',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-t', '--token',
        default=default_token,
        help='Authentication token (default: $TRUSTGRAPH_TOKEN)',
    )

    parser.add_argument(
        '-w', '--workspace',
        default=default_workspace,
        help=f'Workspace (default: {default_workspace})',
    )

    parser.add_argument(
        '-f', '--flow-id',
        default="default",
        help=f'Flow ID (default: default)'
    )

    parser.add_argument(
        '-i', '--image',
        required=True,
        help='Image file to describe e.g. photo.jpg',
    )

    parser.add_argument(
        '--mime-type',
        help='Image MIME type (default: guessed from filename)',
    )

    parser.add_argument(
        '-p', '--prompt',
        help='Prompt to use e.g. What is shown in this image?',
    )

    parser.add_argument(
        '-s', '--system',
        help='System prompt to use',
    )

    args = parser.parse_args()

    try:

        query(
            url=args.url,
            flow_id=args.flow_id,
            image=args.image,
            mime_type=args.mime_type,
            prompt=args.prompt,
            system=args.system,
            token=args.token,
            workspace=args.workspace,
        )

    except TrustGraphException as e:

        print(f"Error: [{e.error_type}] {e.message}", flush=True)

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
