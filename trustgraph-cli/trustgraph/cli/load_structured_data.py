"""
Load structured data into TrustGraph using a descriptor configuration.

This utility can:
1. Analyze data samples to suggest appropriate schemas
2. Generate descriptor configurations from data samples
3. Parse and transform data using descriptor configurations
4. Import processed data into TrustGraph

The tool supports running all steps automatically or individual steps for
validation and debugging. The descriptor language allows for complex 
transformations, validations, and mappings without requiring custom code.
"""

import argparse
import os
import sys
import json
import logging

# Module logger
logger = logging.getLogger(__name__)

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')


def load_structured_data(
    api_url: str,
    input_file: str,
    descriptor_file: str = None,
    suggest_schema: bool = False,
    generate_descriptor: bool = False,
    parse_only: bool = False,
    output_file: str = None,
    sample_size: int = 100,
    sample_chars: int = 500,
    schema_name: str = None,
    dry_run: bool = False,
    verbose: bool = False
):
    """
    Load structured data using a descriptor configuration.
    
    Args:
        api_url: TrustGraph API URL
        input_file: Path to input data file
        descriptor_file: Path to JSON descriptor configuration
        suggest_schema: Analyze data and suggest matching schemas
        generate_descriptor: Generate descriptor from data sample
        parse_only: Parse data but don't import to TrustGraph
        output_file: Path to write output (descriptor/parsed data)
        sample_size: Number of records to sample for analysis
        sample_chars: Maximum characters to read for sampling
        schema_name: Target schema name for generation
        dry_run: If True, validate but don't import data
        verbose: Enable verbose logging
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    # Determine operation mode
    if suggest_schema:
        logger.info(f"Analyzing {input_file} to suggest schemas...")
        logger.info(f"Sample size: {sample_size} records")
        logger.info(f"Sample chars: {sample_chars} characters")
        
        # Read sample data from input file
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                # Read up to sample_chars characters
                sample_data = f.read(sample_chars)
                if len(sample_data) < sample_chars:
                    logger.info(f"Read entire file ({len(sample_data)} characters)")
                else:
                    logger.info(f"Read sample ({sample_chars} characters)")
        except Exception as e:
            logger.error(f"Failed to read input file: {e}")
            raise
        
        # Use TrustGraph prompt service for schema suggestion
        try:
            from trustgraph.api import Api
            
            api = Api(api_url)
            flow_api = api.flow().id("default")
            
            # Call schema-selection prompt with placeholder schema and data sample
            logger.info("Calling TrustGraph schema-selection prompt...")
            response = flow_api.prompt(
                id="schema-selection",
                variables={
                    "schema": "**PLACEHOLDER**",
                    "data": sample_data
                }
            )
            
            print("Schema Suggestion Results:")
            print("=" * 50)
            print(response)
            
        except ImportError as e:
            logger.error(f"Failed to import TrustGraph API: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to call TrustGraph prompt service: {e}")
            raise
        
    elif generate_descriptor:
        logger.info(f"Generating descriptor from {input_file}...")
        logger.info(f"Sample size: {sample_size} records")
        logger.info(f"Sample chars: {sample_chars} characters")
        if schema_name:
            logger.info(f"Target schema: {schema_name}")
        # TODO: Implement descriptor generation
        print(f"Would generate descriptor from {input_file}")
        print(f"Using sample of {sample_size} records, max {sample_chars} characters")
        if output_file:
            print(f"Would save descriptor to {output_file}")
            
    elif parse_only:
        if not descriptor_file:
            raise ValueError("--descriptor is required when using --parse-only")
        logger.info(f"Parsing {input_file} with descriptor {descriptor_file}...")
        # TODO: Implement parsing
        print(f"Would parse {input_file} using {descriptor_file}")
        if output_file:
            print(f"Would save parsed data to {output_file}")
            
    else:
        # Full pipeline: parse and import
        if not descriptor_file:
            # Auto-generate descriptor if not provided
            logger.info("No descriptor provided, auto-generating...")
            # TODO: Generate descriptor
            print(f"Would auto-generate descriptor from {input_file}")
        
        logger.info(f"Processing {input_file} for import...")
        # TODO: Implement full pipeline
        print(f"Would process and import data from {input_file}")
        if dry_run:
            print("Dry run mode - no data will be imported")


def main():
    """Main entry point for the CLI."""
    
    parser = argparse.ArgumentParser(
        prog='tg-load-structured-data',
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Step 1: Analyze data and suggest matching schemas
  %(prog)s --input customers.csv --suggest-schema
  
  # Step 2: Generate descriptor configuration from data sample
  %(prog)s --input customers.csv --generate-descriptor --schema-name customer --output descriptor.json
  
  # Generate descriptor with custom sampling (more data for better analysis)
  %(prog)s --input large_dataset.csv --generate-descriptor --schema-name product --sample-chars 100000 --sample-size 500
  
  # Step 3: Parse data and review output without importing
  %(prog)s --input customers.csv --descriptor descriptor.json --parse-only --output parsed.json
  
  # Step 4: Import data to TrustGraph using descriptor
  %(prog)s --input customers.csv --descriptor descriptor.json
  
  # All-in-one: Auto-generate descriptor and import (for simple cases)
  %(prog)s --input customers.csv --schema-name customer
  
  # Dry run to validate without importing
  %(prog)s --input customers.csv --descriptor descriptor.json --dry-run

Use Cases:
  --suggest-schema     : Diagnose which TrustGraph schemas might match your data
  --generate-descriptor: Create/review the structured data language configuration
  --parse-only        : Validate that parsed data looks correct before import
  (no mode flags)     : Full pipeline - parse and import to TrustGraph

For more information on the descriptor format, see:
  docs/tech-specs/structured-data-descriptor.md
        """.strip()
    )
    
    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'TrustGraph API URL (default: {default_url})'
    )
    
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Path to input data file to process'
    )
    
    parser.add_argument(
        '-d', '--descriptor',
        help='Path to JSON descriptor configuration file (required for full import and parse-only)'
    )
    
    # Operation modes (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--suggest-schema',
        action='store_true',
        help='Analyze data sample and suggest matching TrustGraph schemas'
    )
    mode_group.add_argument(
        '--generate-descriptor',
        action='store_true', 
        help='Generate descriptor configuration from data sample'
    )
    mode_group.add_argument(
        '--parse-only',
        action='store_true',
        help='Parse data using descriptor but don\'t import to TrustGraph'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output file path (for generated descriptors or parsed data)'
    )
    
    parser.add_argument(
        '--sample-size',
        type=int,
        default=100,
        help='Number of records to sample for analysis/generation (default: 100)'
    )
    
    parser.add_argument(
        '--sample-chars',
        type=int,
        default=500,
        help='Maximum characters to read from data file for sampling (default: 500)'
    )
    
    parser.add_argument(
        '--schema-name',
        help='Target schema name for descriptor generation'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate configuration and data without importing (full pipeline only)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output for debugging'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Number of records to process in each batch (default: 1000)'
    )
    
    parser.add_argument(
        '--max-errors',
        type=int,
        default=100,
        help='Maximum number of errors before stopping (default: 100)'
    )
    
    parser.add_argument(
        '--error-file',
        help='Path to write error records (optional)'
    )
    
    args = parser.parse_args()
    
    # Validate argument combinations
    if args.parse_only and not args.descriptor:
        print("Error: --descriptor is required when using --parse-only", file=sys.stderr)
        sys.exit(1)
    
    if not any([args.suggest_schema, args.generate_descriptor, args.parse_only]) and not args.descriptor:
        # Full pipeline mode without descriptor - schema_name should be provided
        if not args.schema_name:
            print("Error: --descriptor or --schema-name is required for full import", file=sys.stderr)
            sys.exit(1)
    
    try:
        load_structured_data(
            api_url=args.api_url,
            input_file=args.input,
            descriptor_file=args.descriptor,
            suggest_schema=args.suggest_schema,
            generate_descriptor=args.generate_descriptor,
            parse_only=args.parse_only,
            output_file=args.output,
            sample_size=args.sample_size,
            sample_chars=args.sample_chars,
            schema_name=args.schema_name,
            dry_run=args.dry_run,
            verbose=args.verbose
        )
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in descriptor - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()