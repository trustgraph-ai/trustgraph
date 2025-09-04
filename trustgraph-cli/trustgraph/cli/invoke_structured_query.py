"""
Uses the Structured Query service to execute natural language questions against structured data
"""

import argparse
import os
import json
import sys
import csv
import io
from trustgraph.api import Api
from tabulate import tabulate

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')

def format_output(data, output_format):
    """Format structured query response data in the specified format"""
    if not data:
        return "No data returned"
    
    # Handle case where data contains multiple query results
    if isinstance(data, dict) and len(data) == 1:
        # Single query result - extract the list
        query_name, result_list = next(iter(data.items()))
        if isinstance(result_list, list):
            return format_table_data(result_list, query_name, output_format)
    
    # Multiple queries or non-list data - use JSON format
    if output_format == 'json':
        return json.dumps(data, indent=2)
    else:
        return json.dumps(data, indent=2)  # Fallback to JSON

def format_table_data(rows, table_name, output_format):
    """Format a list of rows in the specified format"""
    if not rows:
        return f"No {table_name} found"
    
    if output_format == 'json':
        return json.dumps({table_name: rows}, indent=2)
    
    elif output_format == 'csv':
        # Get field names in order from first row, then add any missing ones
        fieldnames = list(rows[0].keys()) if rows else []
        # Add any additional fields from other rows that might be missing
        all_fields = set(fieldnames)
        for row in rows:
            for field in row.keys():
                if field not in all_fields:
                    fieldnames.append(field)
                    all_fields.add(field)
        
        # Create CSV string
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue().rstrip()
    
    elif output_format == 'table':
        # Get field names in order from first row, then add any missing ones
        fieldnames = list(rows[0].keys()) if rows else []
        # Add any additional fields from other rows that might be missing
        all_fields = set(fieldnames)
        for row in rows:
            for field in row.keys():
                if field not in all_fields:
                    fieldnames.append(field)
                    all_fields.add(field)
        
        # Create table data
        table_data = []
        for row in rows:
            table_row = [row.get(field, '') for field in fieldnames]
            table_data.append(table_row)
        
        return tabulate(table_data, headers=fieldnames, tablefmt='pretty')
    
    else:
        return json.dumps({table_name: rows}, indent=2)

def structured_query(url, flow_id, question, output_format='table'):

    api = Api(url).flow().id(flow_id)

    resp = api.structured_query(question=question)

    # Check for errors
    if "error" in resp and resp["error"]:
        print("Error:", resp["error"].get("message", "Unknown error"), file=sys.stderr)
        sys.exit(1)

    # Check for query errors
    if "errors" in resp and resp["errors"]:
        print("Query Errors:", file=sys.stderr)
        for error in resp["errors"]:
            print(f"  - {error}", file=sys.stderr)
        # Still print data if available
        if "data" in resp and resp["data"]:
            print(format_output(resp["data"], output_format))
        sys.exit(1)

    # Print the data
    if "data" in resp:
        print(format_output(resp["data"], output_format))
    else:
        print("No data returned", file=sys.stderr)
        sys.exit(1)

def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-structured-query',
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
        '-q', '--question',
        required=True,
        help='Natural language question to execute',
    )

    parser.add_argument(
        '--format', 
        choices=['table', 'json', 'csv'],
        default='table',
        help='Output format (default: table)'
    )

    args = parser.parse_args()

    try:

        structured_query(
            url=args.url,
            flow_id=args.flow_id,
            question=args.question,
            output_format=args.format,
        )

    except Exception as e:

        print("Exception:", e, flush=True, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()