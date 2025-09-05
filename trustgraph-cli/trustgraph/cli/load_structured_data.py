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
    flow: str = 'default',
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
        
        # Fetch available schemas from Config API
        try:
            from trustgraph.api import Api
            from trustgraph.api.types import ConfigKey
            
            api = Api(api_url)
            config_api = api.config()
            
            # Get list of available schema keys
            logger.info("Fetching available schemas from Config API...")
            schema_keys = config_api.list("schema")
            logger.info(f"Found {len(schema_keys)} schemas: {schema_keys}")
            
            if not schema_keys:
                logger.warning("No schemas found in configuration")
                print("No schemas available in TrustGraph configuration")
                return
            
            # Fetch each schema definition
            schemas = []
            config_keys = [ConfigKey(type="schema", key=key) for key in schema_keys]
            schema_values = config_api.get(config_keys)
            
            for value in schema_values:
                try:
                    # Schema values are JSON strings, parse them
                    schema_def = json.loads(value.value) if isinstance(value.value, str) else value.value
                    schemas.append(schema_def)
                    logger.debug(f"Loaded schema: {value.key}")
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse schema {value.key}: {e}")
                    continue
            
            logger.info(f"Successfully loaded {len(schemas)} schema definitions")
            
            # Use TrustGraph prompt service for schema suggestion
            flow_api = api.flow().id("default")
            
            # Call schema-selection prompt with actual schemas and data sample
            logger.info("Calling TrustGraph schema-selection prompt...")
            response = flow_api.prompt(
                id="schema-selection",
                variables={
                    "schemas": schemas,  # Array of actual schema definitions (note: plural 'schemas')
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
        
        # Fetch available schemas from Config API (same as suggest-schema mode)
        try:
            from trustgraph.api import Api
            from trustgraph.api.types import ConfigKey
            
            api = Api(api_url)
            config_api = api.config()
            
            # Get list of available schema keys
            logger.info("Fetching available schemas from Config API...")
            schema_keys = config_api.list("schema")
            logger.info(f"Found {len(schema_keys)} schemas: {schema_keys}")
            
            if not schema_keys:
                logger.warning("No schemas found in configuration")
                print("No schemas available in TrustGraph configuration")
                return
            
            # Fetch each schema definition
            schemas = []
            config_keys = [ConfigKey(type="schema", key=key) for key in schema_keys]
            schema_values = config_api.get(config_keys)
            
            for value in schema_values:
                try:
                    # Schema values are JSON strings, parse them
                    schema_def = json.loads(value.value) if isinstance(value.value, str) else value.value
                    schemas.append(schema_def)
                    logger.debug(f"Loaded schema: {value.key}")
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse schema {value.key}: {e}")
                    continue
            
            logger.info(f"Successfully loaded {len(schemas)} schema definitions")
            
            # Use TrustGraph prompt service for descriptor generation
            flow_api = api.flow().id("default")
            
            # Call diagnose-structured-data prompt with schemas and data sample
            logger.info("Calling TrustGraph diagnose-structured-data prompt...")
            response = flow_api.prompt(
                id="diagnose-structured-data",
                variables={
                    "schemas": schemas,  # Array of actual schema definitions
                    "sample": sample_data  # Note: using 'sample' instead of 'data'
                }
            )
            
            # Output the generated descriptor
            if output_file:
                try:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        if isinstance(response, str):
                            f.write(response)
                        else:
                            f.write(json.dumps(response, indent=2))
                    print(f"Generated descriptor saved to: {output_file}")
                    logger.info(f"Descriptor saved to {output_file}")
                except Exception as e:
                    logger.error(f"Failed to save descriptor to {output_file}: {e}")
                    print(f"Error saving descriptor: {e}")
            else:
                print("Generated Descriptor:")
                print("=" * 50)
                if isinstance(response, str):
                    print(response)
                else:
                    print(json.dumps(response, indent=2))
                
        except ImportError as e:
            logger.error(f"Failed to import TrustGraph API: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to call TrustGraph prompt service: {e}")
            raise
            
    elif parse_only:
        if not descriptor_file:
            raise ValueError("--descriptor is required when using --parse-only")
        logger.info(f"Parsing {input_file} with descriptor {descriptor_file}...")
        
        # Load descriptor configuration
        try:
            with open(descriptor_file, 'r', encoding='utf-8') as f:
                descriptor = json.load(f)
            logger.info(f"Loaded descriptor configuration from {descriptor_file}")
        except Exception as e:
            logger.error(f"Failed to load descriptor file: {e}")
            raise
            
        # Read input data based on format in descriptor
        try:
            format_info = descriptor.get('format', {})
            format_type = format_info.get('type', 'csv').lower()
            encoding = format_info.get('encoding', 'utf-8')
            
            logger.info(f"Input format: {format_type}, encoding: {encoding}")
            
            with open(input_file, 'r', encoding=encoding) as f:
                raw_data = f.read()
            
            logger.info(f"Read {len(raw_data)} characters from input file")
            
        except Exception as e:
            logger.error(f"Failed to read input file: {e}")
            raise
            
        # Parse data based on format type
        parsed_records = []
        
        if format_type == 'csv':
            import csv
            from io import StringIO
            
            options = format_info.get('options', {})
            delimiter = options.get('delimiter', ',')
            has_header = options.get('has_header', True) or options.get('header', True)
            
            logger.info(f"CSV options - delimiter: '{delimiter}', has_header: {has_header}")
            
            try:
                reader = csv.DictReader(StringIO(raw_data), delimiter=delimiter)
                if not has_header:
                    # If no header, create field names from first row or use generic names
                    first_row = next(reader)
                    fieldnames = [f"field_{i+1}" for i in range(len(first_row))]
                    reader = csv.DictReader(StringIO(raw_data), fieldnames=fieldnames, delimiter=delimiter)
                
                for row_num, row in enumerate(reader, start=1):
                    # Respect sample_size limit
                    if row_num > sample_size:
                        logger.info(f"Reached sample size limit of {sample_size} records")
                        break
                    parsed_records.append(row)
                    
            except Exception as e:
                logger.error(f"Failed to parse CSV data: {e}")
                raise
                
        elif format_type == 'json':
            try:
                data = json.loads(raw_data)
                if isinstance(data, list):
                    parsed_records = data[:sample_size]  # Respect sample_size
                elif isinstance(data, dict):
                    # Handle single object or extract array from root path
                    root_path = format_info.get('options', {}).get('root_path')
                    if root_path:
                        # Simple JSONPath-like extraction (basic implementation)
                        if root_path.startswith('$.'):
                            key = root_path[2:]
                            data = data.get(key, data)
                    
                    if isinstance(data, list):
                        parsed_records = data[:sample_size]
                    else:
                        parsed_records = [data]
                        
            except Exception as e:
                logger.error(f"Failed to parse JSON data: {e}")
                raise
                
        elif format_type == 'xml':
            import xml.etree.ElementTree as ET
            
            options = format_info.get('options', {})
            record_path = options.get('record_path', '//record')  # XPath to find record elements
            field_attribute = options.get('field_attribute')  # Attribute name for field names (e.g., "name")
            
            # Legacy support for old options format
            if 'root_element' in options or 'record_element' in options:
                root_element = options.get('root_element')
                record_element = options.get('record_element', 'record')
                if root_element:
                    record_path = f"//{root_element}/{record_element}"
                else:
                    record_path = f"//{record_element}"
                    
            logger.info(f"XML options - record_path: '{record_path}', field_attribute: '{field_attribute}'")
            
            try:
                root = ET.fromstring(raw_data)
                
                # Find record elements using XPath
                # ElementTree XPath support is limited, convert absolute paths to relative
                xpath_expr = record_path
                if xpath_expr.startswith('/ROOT/'):
                    # Remove /ROOT/ prefix since we're already at the root
                    xpath_expr = xpath_expr[6:]
                elif xpath_expr.startswith('/'):
                    # Convert absolute path to relative by removing leading /
                    xpath_expr = '.' + xpath_expr
                
                records = root.findall(xpath_expr)
                logger.info(f"Found {len(records)} records using XPath: {record_path} (converted to: {xpath_expr})")
                
                # Convert XML elements to dictionaries
                record_count = 0
                for element in records:
                    if record_count >= sample_size:
                        logger.info(f"Reached sample size limit of {sample_size} records")
                        break
                    
                    record = {}
                    
                    if field_attribute:
                        # Handle field elements with name attributes (UN data format)
                        # <field name="Country or Area">Albania</field>
                        for child in element:
                            if child.tag == 'field' and field_attribute in child.attrib:
                                field_name = child.attrib[field_attribute]
                                field_value = child.text.strip() if child.text else ""
                                record[field_name] = field_value
                    else:
                        # Handle standard XML structure
                        # Convert element attributes to fields
                        record.update(element.attrib)
                        
                        # Convert child elements to fields
                        for child in element:
                            if child.text:
                                record[child.tag] = child.text.strip()
                            else:
                                record[child.tag] = ""
                        
                        # If no children or attributes, use element text as single field
                        if not record and element.text:
                            record['value'] = element.text.strip()
                    
                    parsed_records.append(record)
                    record_count += 1
                    
            except ET.ParseError as e:
                logger.error(f"Failed to parse XML data: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to process XML data: {e}")
                raise
                
        else:
            raise ValueError(f"Unsupported format type: {format_type}")
            
        logger.info(f"Successfully parsed {len(parsed_records)} records")
        
        # Apply basic transformations and validation (simplified version)
        mappings = descriptor.get('mappings', [])
        processed_records = []
        
        for record_num, record in enumerate(parsed_records, start=1):
            processed_record = {}
            
            for mapping in mappings:
                source_field = mapping.get('source_field') or mapping.get('source')
                target_field = mapping.get('target_field') or mapping.get('target')
                
                if source_field in record:
                    value = record[source_field]
                    
                    # Apply basic transforms (simplified)
                    transforms = mapping.get('transforms', [])
                    for transform in transforms:
                        transform_type = transform.get('type')
                        
                        if transform_type == 'trim' and isinstance(value, str):
                            value = value.strip()
                        elif transform_type == 'upper' and isinstance(value, str):
                            value = value.upper()
                        elif transform_type == 'lower' and isinstance(value, str):
                            value = value.lower()
                        elif transform_type == 'title_case' and isinstance(value, str):
                            value = value.title()
                        elif transform_type == 'to_int':
                            try:
                                value = int(value) if value != '' else None
                            except (ValueError, TypeError):
                                logger.warning(f"Failed to convert '{value}' to int in record {record_num}")
                        elif transform_type == 'to_float':
                            try:
                                value = float(value) if value != '' else None
                            except (ValueError, TypeError):
                                logger.warning(f"Failed to convert '{value}' to float in record {record_num}")
                    
                    # Convert all values to strings as required by ExtractedObject schema
                    processed_record[target_field] = str(value) if value is not None else ""
                else:
                    logger.warning(f"Source field '{source_field}' not found in record {record_num}")
            
            processed_records.append(processed_record)
        
        # Format output for TrustGraph ExtractedObject structure
        output_records = []
        schema_name = descriptor.get('output', {}).get('schema_name', 'default')
        confidence = descriptor.get('output', {}).get('options', {}).get('confidence', 0.9)
        
        for record in processed_records:
            output_record = {
                "metadata": {
                    "id": f"parsed-{len(output_records)+1}",
                    "metadata": [],  # Empty metadata triples
                    "user": "trustgraph",
                    "collection": "default"
                },
                "schema_name": schema_name,
                "values": record,
                "confidence": confidence,
                "source_span": ""
            }
            output_records.append(output_record)
        
        # Output results
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(output_records, f, indent=2)
                print(f"Parsed data saved to: {output_file}")
                logger.info(f"Parsed {len(output_records)} records saved to {output_file}")
            except Exception as e:
                logger.error(f"Failed to save parsed data to {output_file}: {e}")
                print(f"Error saving parsed data: {e}")
        else:
            print("Parsed Data Preview:")
            print("=" * 50)
            # Show first few records for preview
            preview_count = min(3, len(output_records))
            for i in range(preview_count):
                print(f"Record {i+1}:")
                print(json.dumps(output_records[i], indent=2))
                print()
            
            if len(output_records) > preview_count:
                print(f"... and {len(output_records) - preview_count} more records")
                print(f"Total records processed: {len(output_records)}")
        
        print(f"\nParsing Summary:")
        print(f"- Input format: {format_type}")
        print(f"- Records processed: {len(output_records)}")
        print(f"- Target schema: {schema_name}")
        print(f"- Field mappings: {len(mappings)}")
            
    else:
        # Full pipeline: parse and import
        if not descriptor_file:
            # Auto-generate descriptor if not provided
            logger.info("No descriptor provided, auto-generating...")
            logger.info(f"Schema name: {schema_name}")
            
            # Read sample data for descriptor generation
            try:
                with open(input_file, 'r', encoding='utf-8') as f:
                    sample_data = f.read(sample_chars)
                    logger.info(f"Read {len(sample_data)} characters for descriptor generation")
            except Exception as e:
                logger.error(f"Failed to read input file for descriptor generation: {e}")
                raise
            
            # Generate descriptor using TrustGraph prompt service
            try:
                from trustgraph.api import Api
                from trustgraph.api.types import ConfigKey
                
                api = Api(api_url)
                config_api = api.config()
                
                # Get available schemas
                logger.info("Fetching available schemas for descriptor generation...")
                schema_keys = config_api.list("schema")
                logger.info(f"Found {len(schema_keys)} schemas: {schema_keys}")
                
                if not schema_keys:
                    logger.warning("No schemas found in configuration")
                    print("No schemas available in TrustGraph configuration")
                    return
                
                # Fetch each schema definition
                schemas = []
                config_keys = [ConfigKey(type="schema", key=key) for key in schema_keys]
                schema_values = config_api.get(config_keys)
                
                for value in schema_values:
                    try:
                        schema_def = json.loads(value.value) if isinstance(value.value, str) else value.value
                        schemas.append(schema_def)
                        logger.debug(f"Loaded schema: {value.key}")
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse schema {value.key}: {e}")
                        continue
                
                logger.info(f"Successfully loaded {len(schemas)} schema definitions")
                
                # Generate descriptor using diagnose-structured-data prompt
                flow_api = api.flow().id(flow)
                
                logger.info("Calling TrustGraph diagnose-structured-data prompt for descriptor generation...")
                response = flow_api.prompt(
                    id="diagnose-structured-data",
                    variables={
                        "schemas": schemas,
                        "sample": sample_data
                    }
                )
                
                # Parse the generated descriptor
                if isinstance(response, str):
                    try:
                        descriptor = json.loads(response)
                    except json.JSONDecodeError:
                        logger.error("Generated descriptor is not valid JSON")
                        raise ValueError("Failed to generate valid descriptor")
                else:
                    descriptor = response
                
                # Override schema_name if provided
                if schema_name:
                    descriptor.setdefault('output', {})['schema_name'] = schema_name
                
                logger.info("Successfully generated descriptor from data sample")
                
            except ImportError as e:
                logger.error(f"Failed to import TrustGraph API: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to generate descriptor: {e}")
                raise
        else:
            # Load existing descriptor
            try:
                with open(descriptor_file, 'r', encoding='utf-8') as f:
                    descriptor = json.load(f)
                logger.info(f"Loaded descriptor configuration from {descriptor_file}")
            except Exception as e:
                logger.error(f"Failed to load descriptor file: {e}")
                raise
        
        logger.info(f"Processing {input_file} for import...")
        
        # Parse data using the same logic as parse-only mode, but with full dataset
        try:
            format_info = descriptor.get('format', {})
            format_type = format_info.get('type', 'csv').lower()
            encoding = format_info.get('encoding', 'utf-8')
            
            logger.info(f"Input format: {format_type}, encoding: {encoding}")
            
            with open(input_file, 'r', encoding=encoding) as f:
                raw_data = f.read()
            
            logger.info(f"Read {len(raw_data)} characters from input file")
            
        except Exception as e:
            logger.error(f"Failed to read input file: {e}")
            raise
        
        # Parse data (reuse parse-only logic but process all records)
        parsed_records = []
        batch_size = descriptor.get('output', {}).get('options', {}).get('batch_size', 1000)
        
        if format_type == 'csv':
            import csv
            from io import StringIO
            
            options = format_info.get('options', {})
            delimiter = options.get('delimiter', ',')
            has_header = options.get('has_header', True) or options.get('header', True)
            
            logger.info(f"CSV options - delimiter: '{delimiter}', has_header: {has_header}")
            
            try:
                reader = csv.DictReader(StringIO(raw_data), delimiter=delimiter)
                if not has_header:
                    first_row = next(reader)
                    fieldnames = [f"field_{i+1}" for i in range(len(first_row))]
                    reader = csv.DictReader(StringIO(raw_data), fieldnames=fieldnames, delimiter=delimiter)
                
                record_count = 0
                for row in reader:
                    parsed_records.append(row)
                    record_count += 1
                    
                    # Process in batches to avoid memory issues
                    if record_count % batch_size == 0:
                        logger.info(f"Parsed {record_count} records...")
                        
            except Exception as e:
                logger.error(f"Failed to parse CSV data: {e}")
                raise
                
        elif format_type == 'json':
            try:
                data = json.loads(raw_data)
                if isinstance(data, list):
                    parsed_records = data
                elif isinstance(data, dict):
                    root_path = format_info.get('options', {}).get('root_path')
                    if root_path:
                        if root_path.startswith('$.'):
                            key = root_path[2:]
                            data = data.get(key, data)
                    
                    if isinstance(data, list):
                        parsed_records = data
                    else:
                        parsed_records = [data]
                        
            except Exception as e:
                logger.error(f"Failed to parse JSON data: {e}")
                raise
                
        elif format_type == 'xml':
            import xml.etree.ElementTree as ET
            
            options = format_info.get('options', {})
            record_path = options.get('record_path', '//record')
            field_attribute = options.get('field_attribute')
            
            # Legacy support for old options format
            if 'root_element' in options or 'record_element' in options:
                root_element = options.get('root_element')
                record_element = options.get('record_element', 'record')
                if root_element:
                    record_path = f"//{root_element}/{record_element}"
                else:
                    record_path = f"//{record_element}"
                    
            logger.info(f"XML options - record_path: '{record_path}', field_attribute: '{field_attribute}'")
            
            try:
                root = ET.fromstring(raw_data)
                
                # Find record elements using XPath
                xpath_expr = record_path
                if xpath_expr.startswith('/ROOT/'):
                    xpath_expr = xpath_expr[6:]
                elif xpath_expr.startswith('/'):
                    xpath_expr = '.' + xpath_expr
                
                records = root.findall(xpath_expr)
                logger.info(f"Found {len(records)} records using XPath: {record_path} (converted to: {xpath_expr})")
                
                # Convert XML elements to dictionaries
                for element in records:
                    record = {}
                    
                    if field_attribute:
                        # Handle field elements with name attributes (UN data format)
                        for child in element:
                            if child.tag == 'field' and field_attribute in child.attrib:
                                field_name = child.attrib[field_attribute]
                                field_value = child.text.strip() if child.text else ""
                                record[field_name] = field_value
                    else:
                        # Handle standard XML structure
                        record.update(element.attrib)
                        
                        for child in element:
                            if child.text:
                                record[child.tag] = child.text.strip()
                            else:
                                record[child.tag] = ""
                        
                        if not record and element.text:
                            record['value'] = element.text.strip()
                    
                    parsed_records.append(record)
                    
            except ET.ParseError as e:
                logger.error(f"Failed to parse XML data: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to process XML data: {e}")
                raise
                
        else:
            raise ValueError(f"Unsupported format type: {format_type}")
            
        logger.info(f"Successfully parsed {len(parsed_records)} records")
        
        # Apply transformations and create TrustGraph objects
        mappings = descriptor.get('mappings', [])
        processed_records = []
        schema_name = descriptor.get('output', {}).get('schema_name', 'default')
        confidence = descriptor.get('output', {}).get('options', {}).get('confidence', 0.9)
        
        logger.info(f"Applying {len(mappings)} field mappings...")
        
        for record_num, record in enumerate(parsed_records, start=1):
            processed_record = {}
            
            for mapping in mappings:
                source_field = mapping.get('source_field') or mapping.get('source')
                target_field = mapping.get('target_field') or mapping.get('target')
                
                if source_field in record:
                    value = record[source_field]
                    
                    # Apply transforms
                    transforms = mapping.get('transforms', [])
                    for transform in transforms:
                        transform_type = transform.get('type')
                        
                        if transform_type == 'trim' and isinstance(value, str):
                            value = value.strip()
                        elif transform_type == 'upper' and isinstance(value, str):
                            value = value.upper()
                        elif transform_type == 'lower' and isinstance(value, str):
                            value = value.lower()
                        elif transform_type == 'title_case' and isinstance(value, str):
                            value = value.title()
                        elif transform_type == 'to_int':
                            try:
                                value = int(value) if value != '' else None
                            except (ValueError, TypeError):
                                logger.warning(f"Failed to convert '{value}' to int in record {record_num}")
                        elif transform_type == 'to_float':
                            try:
                                value = float(value) if value != '' else None
                            except (ValueError, TypeError):
                                logger.warning(f"Failed to convert '{value}' to float in record {record_num}")
                    
                    # Convert all values to strings as required by ExtractedObject schema
                    processed_record[target_field] = str(value) if value is not None else ""
                else:
                    logger.warning(f"Source field '{source_field}' not found in record {record_num}")
            
            # Create TrustGraph ExtractedObject
            output_record = {
                "metadata": {
                    "id": f"import-{record_num}",
                    "metadata": [],
                    "user": "trustgraph",
                    "collection": "default"
                },
                "schema_name": schema_name,
                "values": processed_record,
                "confidence": confidence,
                "source_span": ""
            }
            processed_records.append(output_record)
        
        logger.info(f"Processed {len(processed_records)} records with transformations")
        
        if dry_run:
            print(f"Dry run mode - would import {len(processed_records)} records to TrustGraph")
            print(f"Target schema: {schema_name}")
            print(f"Sample record:")
            if processed_records:
                # Show what the batched format will look like
                sample_batch = processed_records[:min(3, len(processed_records))]
                batch_values = [record["values"] for record in sample_batch]
                first_record = processed_records[0]
                batched_sample = {
                    "metadata": first_record["metadata"],
                    "schema_name": first_record["schema_name"],
                    "values": batch_values,
                    "confidence": first_record["confidence"],
                    "source_span": first_record["source_span"]
                }
                print(json.dumps(batched_sample, indent=2))
            return
        
        # Import to TrustGraph using objects import endpoint via WebSocket
        logger.info(f"Importing {len(processed_records)} records to TrustGraph...")
        
        try:
            import asyncio
            from websockets.asyncio.client import connect
            
            # Construct objects import URL similar to load_knowledge pattern
            if not api_url.endswith("/"):
                api_url += "/"
            
            # Convert HTTP URL to WebSocket URL if needed
            ws_url = api_url.replace("http://", "ws://").replace("https://", "wss://")
            objects_url = ws_url + f"api/v1/flow/{flow}/import/objects"
            
            logger.info(f"Connecting to objects import endpoint: {objects_url}")
            
            async def import_objects():
                async with connect(objects_url) as ws:
                    imported_count = 0
                    
                    # Process records in batches
                    for i in range(0, len(processed_records), batch_size):
                        batch_records = processed_records[i:i + batch_size]
                        
                        # Extract values from each record in the batch
                        batch_values = [record["values"] for record in batch_records]
                        
                        # Create batched ExtractedObject message using first record as template
                        first_record = batch_records[0]
                        batched_record = {
                            "metadata": first_record["metadata"],
                            "schema_name": first_record["schema_name"],
                            "values": batch_values,  # Array of value dictionaries
                            "confidence": first_record["confidence"],
                            "source_span": first_record["source_span"]
                        }
                        
                        # Send batched ExtractedObject
                        await ws.send(json.dumps(batched_record))
                        imported_count += len(batch_records)
                        
                        if imported_count % 100 == 0:
                            logger.info(f"Imported {imported_count}/{len(processed_records)} records...")
                    
                    logger.info(f"Successfully imported {imported_count} records to TrustGraph")
                    return imported_count
            
            # Run the async import
            imported_count = asyncio.run(import_objects())
            print(f"Import completed: {imported_count} records imported to schema '{schema_name}'")
            
        except ImportError as e:
            logger.error(f"Failed to import required modules: {e}")
            print(f"Error: Required modules not available - {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to import data to TrustGraph: {e}")
            print(f"Import failed: {e}")
            raise


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
  %(prog)s --input products.xml --suggest-schema --sample-chars 1000
  
  # Step 2: Generate descriptor configuration from data sample
  %(prog)s --input customers.csv --generate-descriptor --schema-name customer --output descriptor.json
  %(prog)s --input products.xml --generate-descriptor --schema-name product --output xml_descriptor.json
  
  # Generate descriptor with custom sampling (more data for better analysis)
  %(prog)s --input large_dataset.csv --generate-descriptor --schema-name product --sample-chars 100000 --sample-size 500
  
  # Step 3: Parse data and review output without importing (supports CSV, JSON, XML)
  %(prog)s --input customers.csv --descriptor descriptor.json --parse-only --output parsed.json
  %(prog)s --input products.xml --descriptor xml_descriptor.json --parse-only
  
  # Step 4: Import data to TrustGraph using descriptor
  %(prog)s --input customers.csv --descriptor descriptor.json
  %(prog)s --input products.xml --descriptor xml_descriptor.json
  
  # All-in-one: Auto-generate descriptor and import (for simple cases)
  %(prog)s --input customers.csv --schema-name customer
  
  # Dry run to validate without importing
  %(prog)s --input customers.csv --descriptor descriptor.json --dry-run

Use Cases:
  --suggest-schema     : Diagnose which TrustGraph schemas might match your data
                        (uses --sample-chars to limit data sent for analysis)
  --generate-descriptor: Create/review the structured data language configuration  
                        (uses --sample-chars to limit data sent for analysis)
  --parse-only        : Validate that parsed data looks correct before import
                        (uses --sample-size to limit records processed, ignores --sample-chars)
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
        '-f', '--flow',
        default='default',
        help='TrustGraph flow name to use for import (default: default)'
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
        help='Number of records to process (parse-only mode) or sample for analysis (default: 100)'
    )
    
    parser.add_argument(
        '--sample-chars',
        type=int,
        default=500,
        help='Maximum characters to read for sampling (suggest-schema/generate-descriptor modes only, default: 500)'
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
    
    # Warn about irrelevant parameters
    if args.parse_only and args.sample_chars != 500:  # 500 is the default
        print("Warning: --sample-chars is ignored in --parse-only mode (entire file is processed)", file=sys.stderr)
    
    if (args.suggest_schema or args.generate_descriptor) and args.sample_size != 100:  # 100 is default
        print("Warning: --sample-size is ignored in analysis modes, use --sample-chars instead", file=sys.stderr)
    
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
            flow=args.flow,
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