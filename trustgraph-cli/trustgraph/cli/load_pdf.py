"""
DEPRECATED: This tool is deprecated and will be removed in a future version.

Use tg-add-library-document to add a document to the library, followed by
tg-start-library-processing to initiate processing.

Example:
    # Add document to library
    tg-add-library-document --id my-doc --title "My PDF" document.pdf

    # Start processing
    tg-start-library-processing --document-id my-doc --collection default

The library-based workflow provides:
- Progress feedback for large file uploads
- Resumable uploads
- Better error handling
- Centralized document management
"""

import hashlib
import argparse
import os
import sys
import time
import uuid
import warnings

from trustgraph.api import Api
from trustgraph.knowledge import hash, to_uri
from trustgraph.knowledge import PREF_PUBEV, PREF_DOC, PREF_ORG
from trustgraph.knowledge import Organization, PublicationEvent
from trustgraph.knowledge import DigitalDocument

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_user = 'trustgraph'
default_collection = 'default'

class Loader:

    def __init__(
            self,
            url,
            flow_id,
            user,
            collection,
            metadata,
    ):

        self.api = Api(url).flow().id(flow_id)

        self.user = user
        self.collection = collection
        self.metadata = metadata

    def load(self, files):

        for file in files:
            self.load_file(file)

    def load_file(self, file):

        try:

            path = file
            data = open(path, "rb").read()

            # Create a SHA256 hash from the data
            id = hash(data)

            id = to_uri(PREF_DOC, id)

            self.metadata.id = id

            self.api.load_document(
                document=data, id=id, metadata=self.metadata, 
                user=self.user,
                collection=self.collection,
            )

            print(f"{file}: Loaded successfully.")

        except Exception as e:
            print(f"{file}: Failed: {str(e)}", flush=True)
            raise e

def main():

    # Print deprecation warning
    print("\n" + "=" * 70, file=sys.stderr)
    print("DEPRECATION WARNING: tg-load-pdf is deprecated.", file=sys.stderr)
    print("", file=sys.stderr)
    print("Please use the library-based workflow instead:", file=sys.stderr)
    print("  1. tg-add-library-document to add the document", file=sys.stderr)
    print("  2. tg-start-library-processing to start processing", file=sys.stderr)
    print("", file=sys.stderr)
    print("This provides progress feedback, resumable uploads, and", file=sys.stderr)
    print("better handling of large documents.", file=sys.stderr)
    print("=" * 70 + "\n", file=sys.stderr)

    parser = argparse.ArgumentParser(
        prog='tg-load-pdf',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-f', '--flow-id',
        default="default",
        help=f'Flow ID (default: default)'
    )

    parser.add_argument(
        '-U', '--user',
        default=default_user,
        help=f'User ID (default: {default_user})'
    )

    parser.add_argument(
        '-C', '--collection',
        default=default_collection,
        help=f'Collection ID (default: {default_collection})'
    )

    parser.add_argument(
        '--name', help=f'Document name'
    )

    parser.add_argument(
        '--description', help=f'Document description'
    )

    parser.add_argument(
        '--copyright-notice', help=f'Copyright notice'
    )

    parser.add_argument(
        '--copyright-holder', help=f'Copyright holder'
    )

    parser.add_argument(
        '--copyright-year', help=f'Copyright year'
    )

    parser.add_argument(
        '--license', help=f'Copyright license'
    )

    parser.add_argument(
        '--publication-organization', help=f'Publication organization'
    )

    parser.add_argument(
        '--publication-description', help=f'Publication description'
    )

    parser.add_argument(
        '--publication-date', help=f'Publication date'
    )

    parser.add_argument(
        '--document-url', help=f'Document URL'
    )

    parser.add_argument(
        '--keyword', nargs='+', help=f'Keyword'
    )

    parser.add_argument(
        '--identifier', '--id', help=f'Document ID'
    )

    parser.add_argument(
        'files', nargs='+',
        help=f'File to load'
    )

    args = parser.parse_args()

    try:

        document = DigitalDocument(
            id,
            name=args.name,
            description=args.description,
            copyright_notice=args.copyright_notice,
            copyright_holder=args.copyright_holder,
            copyright_year=args.copyright_year,
            license=args.license,
            url=args.document_url,
            keywords=args.keyword,
        )

        if args.publication_organization:
            org = Organization(
                id=to_uri(PREF_ORG, hash(args.publication_organization)),
                name=args.publication_organization,
            )
            document.publication = PublicationEvent(
                id = to_uri(PREF_PUBEV, str(uuid.uuid4())),
                organization=org,
                description=args.publication_description,
                start_date=args.publication_date,
                end_date=args.publication_date,
            )

        p = Loader(
            url=args.url,
            flow_id = args.flow_id,
            user=args.user,
            collection=args.collection,
            metadata=document,
        )

        p.load(args.files)

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()