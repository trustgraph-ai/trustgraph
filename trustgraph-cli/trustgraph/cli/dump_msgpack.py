"""
This utility reads a knowledge core in msgpack format and outputs its
contents in JSON form to standard output.  This is useful only as a
diagnostic utility.
"""

import msgpack
import sys
import argparse
import json

def dump(input_file, action):

    with open(input_file, 'rb') as f:

        unpacker = msgpack.Unpacker(f, raw=False)

        for unpacked in unpacker:
            print(json.dumps(unpacked))

def summary(input_file, action):

    vector_dim = None

    triples = set()

    max_records = 1000000

    with open(input_file, 'rb') as f:

        unpacker = msgpack.Unpacker(f, raw=False)

        rec_count = 0

        for msg in unpacker:

            if msg[0] == "ge":
                vector_dim = len(msg[1]["v"][0])

            if msg[0] == "t":

                for elt in msg[1]["m"]["m"]:
                    triples.add((
                        elt["s"]["v"],
                        elt["p"]["v"],
                        elt["o"]["v"],
                    ))

            if rec_count > max_records: break
            rec_count += 1

    print("Vector dimension:", vector_dim)

    for t in triples:
        if t[1] == "http://www.w3.org/2000/01/rdf-schema#label":
            print("-", t[2])

def main():
    
    parser = argparse.ArgumentParser(
        prog='tg-dump-msgpack',
        description=__doc__,
    )

    parser.add_argument(
        '-i', '--input-file',
        required=True,
        help=f'Input file'
    )

    parser.add_argument(
        '-s', '--summary', action="store_const", const="summary",
        dest="action",
        help=f'Show a summary'
    )

    parser.add_argument(
        '-r', '--records', action="store_const", const="records",
        dest="action",
        help=f'Dump individual records'
    )

    args = parser.parse_args()

    if args.action == "summary":
        summary(**vars(args))
    else:
        dump(**vars(args))

if __name__ == "__main__":
    main()