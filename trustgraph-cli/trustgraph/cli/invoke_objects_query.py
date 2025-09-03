"""
Uses the ObjectsQuery service to execute GraphQL queries against structured data
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
default_user = 'trustgraph'
default_collection = 'default'

def format_output(data, output_format):
    """Format GraphQL response data in the specified format"""
    if not data:
        return "No data returned"
    
    # Handle case where data contains multiple query results
    if len(data) == 1:
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

def objects_query(
        url, flow_id, query, user, collection, variables, operation_name, output_format='table'
):

    api = Api(url).flow().id(flow_id)

    # Parse variables if provided as JSON string
    parsed_variables = {}
    if variables:
        try:
            parsed_variables = json.loads(variables)
        except json.JSONDecodeError as e:
            print(f"Error parsing variables JSON: {e}", file=sys.stderr)
            sys.exit(1)

    resp = api.objects_query(
        query=query,
        user=user,
        collection=collection,
        variables=parsed_variables if parsed_variables else None,
        operation_name=operation_name
    )

    # Check for GraphQL errors
    if "errors" in resp and resp["errors"]:
        print("GraphQL Errors:", file=sys.stderr)
        for error in resp["errors"]:
            print(f"  - {error.get('message', 'Unknown error')}", file=sys.stderr)
            if "path" in error and error["path"]:
                print(f"    Path: {error['path']}", file=sys.stderr)
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
        prog='tg-invoke-objects-query',
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
        '-q', '--query',
        required=True,
        help='GraphQL query to execute',
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
        '-v', '--variables',
        help='GraphQL variables as JSON string (e.g., \'{"limit": 5}\')'
    )

    parser.add_argument(
        '-o', '--operation-name',
        help='Operation name for multi-operation GraphQL documents'
    )

    parser.add_argument(
        '--format', 
        choices=['table', 'json', 'csv'],
        default='table',
        help='Output format (default: table)'
    )

    args = parser.parse_args()

    try:

        objects_query(
            url=args.url,
            flow_id=args.flow_id,
            query=args.query,
            user=args.user,
            collection=args.collection,
            variables=args.variables,
            operation_name=args.operation_name,
            output_format=args.format,
        )

    except Exception as e:

        print("Exception:", e, flush=True, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
