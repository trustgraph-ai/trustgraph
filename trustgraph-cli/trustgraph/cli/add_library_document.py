"""
Loads a document into the library
"""

import hashlib
import argparse
import os
import time
import uuid

from trustgraph.api import Api
from trustgraph.knowledge import hash, to_uri
from trustgraph.knowledge import PREF_PUBEV, PREF_DOC, PREF_ORG
from trustgraph.knowledge import Organization, PublicationEvent
from trustgraph.knowledge import DigitalDocument

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_user = 'trustgraph'

class Loader:

    def __init__(
            self, id, url, user, metadata, title, comments, kind, tags
    ):

        self.api = Api(url).library()

        self.user = user
        self.metadata = metadata
        self.title = title
        self.comments = comments
        self.kind = kind
        self.identifier = id

        if tags:
            self.tags = tags.split(",")
        else:
            self.tags = []

    def load(self, files):

        for file in files:
            self.load_file(file)

    def load_file(self, file):

        try:

            path = file
            data = open(path, "rb").read()

            # Create a SHA256 hash from the data
            if self.identifier:
                id = self.identifier
            else:
                id = hash(data)
                id = to_uri(PREF_DOC, id)
                

            self.metadata.id = id

            self.api.add_document(
                document=data, id=id, metadata=self.metadata, 
                user=self.user, kind=self.kind, title=self.title,
                comments=self.comments, tags=self.tags
            )

            print(f"{file}: Loaded successfully.")

        except Exception as e:
            print(f"{file}: Failed: {str(e)}", flush=True)
            raise e

def main():

    parser = argparse.ArgumentParser(
        prog='tg-add-library-document',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-U', '--user',
        default=default_user,
        help=f'User ID (default: {default_user})'
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
        '-k', '--kind',
        required=True,
        help=f'Document MIME type'
    )

    parser.add_argument(
        '--tags',
        help=f'Tags, command separated'
    )

    parser.add_argument(
        'files', nargs='+',
        help=f'File to load'
    )

    args = parser.parse_args()

    try:

        document = DigitalDocument(
            args.identifier,
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
            id=args.identifier,
            url=args.url,
            user=args.user,
            metadata=document,
            title=args.name,
            comments=args.description,
            kind=args.kind,
            tags=args.tags,
        )

        p.load(args.files)

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()