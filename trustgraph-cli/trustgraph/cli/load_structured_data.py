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
    auto: bool = False,
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
        auto: Run full automatic pipeline (suggest schema + generate descriptor + import)
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
    if auto:
        logger.info(f"🚀 Starting automatic pipeline for {input_file}...")
        logger.info("Step 1: Analyzing data to discover best matching schema...")
        
        # Step 1: Auto-discover schema (reuse suggest_schema logic)
        discovered_schema = _auto_discover_schema(api_url, input_file, sample_chars, logger)
        if not discovered_schema:
            logger.error("Failed to discover suitable schema automatically")
            print("❌ Could not automatically determine the best schema for your data.")
            print("💡 Try running with --suggest-schema first to see available options.")
            return None
            
        logger.info(f"✅ Discovered schema: {discovered_schema}")
        print(f"🎯 Auto-selected schema: {discovered_schema}")
        
        # Step 2: Auto-generate descriptor
        logger.info("Step 2: Generating descriptor configuration...")
        auto_descriptor = _auto_generate_descriptor(api_url, input_file, discovered_schema, sample_chars, logger)
        if not auto_descriptor:
            logger.error("Failed to generate descriptor automatically")
            print("❌ Could not automatically generate descriptor configuration.")
            return None
            
        logger.info("✅ Generated descriptor configuration")
        print("📝 Generated descriptor configuration")
        
        # Step 3: Parse and preview data
        logger.info("Step 3: Parsing and validating data...")
        preview_records = _auto_parse_preview(input_file, auto_descriptor, min(sample_size, 5), logger)
        if preview_records is None:
            logger.error("Failed to parse data with generated descriptor")
            print("❌ Could not parse data with generated descriptor.")
            return None
            
        # Show preview
        print("📊 Data Preview (first few records):")
        print("=" * 50)
        for i, record in enumerate(preview_records[:3], 1):
            print(f"Record {i}: {record}")
        print("=" * 50)
        
        # Step 4: Import (unless dry_run)
        if dry_run:
            logger.info("✅ Dry run complete - data is ready for import")
            print("✅ Dry run successful! Data is ready for import.")
            print(f"💡 Run without --dry-run to import {len(preview_records)} records to TrustGraph.")
            return None
        else:
            logger.info("Step 4: Importing data to TrustGraph...")
            print("🚀 Importing data to TrustGraph...")
            
            # Recursively call ourselves with the auto-generated descriptor
            # This reuses all the existing import logic
            import tempfile
            import os
            
            # Save auto-generated descriptor to temp file
            temp_descriptor = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
            json.dump(auto_descriptor, temp_descriptor, indent=2)
            temp_descriptor.close()
            
            try:
                # Call the full pipeline mode with our auto-generated descriptor
                result = load_structured_data(
                    api_url=api_url,
                    input_file=input_file,
                    descriptor_file=temp_descriptor.name,
                    flow=flow,
                    dry_run=False,  # We already handled dry_run above
                    verbose=verbose
                )
                
                print("✅ Auto-import completed successfully!")
                logger.info("Auto-import pipeline completed successfully")
                return result
                
            finally:
                # Clean up temp descriptor file
                try:
                    os.unlink(temp_descriptor.name)
                except:
                    pass
    
    elif suggest_schema:
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


# Helper functions for auto mode
def _auto_discover_schema(api_url, input_file, sample_chars, logger):
    """Auto-discover the best matching schema for the input data"""
    try:
        # Read sample data
        with open(input_file, 'r', encoding='utf-8') as f:
            sample_data = f.read(sample_chars)
        
        # Import API modules
        from trustgraph.api import Api
        api = Api(api_url)
        config_api = api.config()
        
        # Get available schemas
        schema_keys = config_api.list("schema")
        if not schema_keys:
            logger.error("No schemas available in TrustGraph configuration")
            return None
            
        # Get schema definitions
        schemas = {}
        for key in schema_keys:
            try:
                schema_def = config_api.get("schema", key)
                schemas[key] = schema_def
            except Exception as e:
                logger.warning(f"Could not load schema {key}: {e}")
                
        if not schemas:
            logger.error("No valid schemas could be loaded")
            return None
            
        # Use prompt service for schema selection
        flow_api = api.flow().id("default")
        prompt_client = flow_api.prompt()
        
        prompt = f"""Analyze this data sample and determine the best matching schema:

DATA SAMPLE:
{sample_data[:1000]}

AVAILABLE SCHEMAS:
{json.dumps(schemas, indent=2)}

Return ONLY the schema name (key) that best matches this data. Consider:
1. Field names and types in the data
2. Data structure and format
3. Domain and use case alignment

Schema name:"""

        response = prompt_client.schema_selection(
            schemas=schemas,
            sample=sample_data[:1000]
        )
        
        # Extract schema name from response
        if isinstance(response, dict) and 'schema' in response:
            return response['schema']
        elif isinstance(response, str):
            # Try to extract schema name from text response
            response_lower = response.lower().strip()
            for schema_key in schema_keys:
                if schema_key.lower() in response_lower:
                    return schema_key
                    
            # If no exact match, try first mentioned schema
            words = response.split()
            for word in words:
                clean_word = word.strip('.,!?":').lower()
                if clean_word in [s.lower() for s in schema_keys]:
                    matching_schema = next(s for s in schema_keys if s.lower() == clean_word)
                    return matching_schema
                    
        logger.warning(f"Could not parse schema selection from response: {response}")
        
        # Fallback: return first available schema
        logger.info(f"Using fallback: first available schema '{schema_keys[0]}'")
        return schema_keys[0]
        
    except Exception as e:
        logger.error(f"Schema discovery failed: {e}")
        return None


def _auto_generate_descriptor(api_url, input_file, schema_name, sample_chars, logger):
    """Auto-generate descriptor configuration for the discovered schema"""
    try:
        # Read sample data
        with open(input_file, 'r', encoding='utf-8') as f:
            sample_data = f.read(sample_chars)
        
        # Import API modules
        from trustgraph.api import Api
        api = Api(api_url)
        config_api = api.config()
        
        # Get schema definition
        schema_def = config_api.get("schema", schema_name)
        
        # Use prompt service for descriptor generation
        flow_api = api.flow().id("default") 
        prompt_client = flow_api.prompt()
        
        response = prompt_client.diagnose_structured_data(
            sample=sample_data,
            schema_name=schema_name,
            schema=schema_def
        )
        
        if isinstance(response, str):
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                logger.error("Generated descriptor is not valid JSON")
                return None
        else:
            return response
            
    except Exception as e:
        logger.error(f"Descriptor generation failed: {e}")
        return None


def _auto_parse_preview(input_file, descriptor, max_records, logger):
    """Parse and preview data using the auto-generated descriptor"""
    try:
        # Simplified parsing logic for preview (reuse existing logic)
        format_info = descriptor.get('format', {})
        format_type = format_info.get('type', 'csv').lower()
        encoding = format_info.get('encoding', 'utf-8')
        
        with open(input_file, 'r', encoding=encoding) as f:
            raw_data = f.read()
        
        parsed_records = []
        
        if format_type == 'csv':
            import csv
            from io import StringIO
            
            options = format_info.get('options', {})
            delimiter = options.get('delimiter', ',')
            has_header = options.get('has_header', True) or options.get('header', True)
            
            reader = csv.DictReader(StringIO(raw_data), delimiter=delimiter)
            if not has_header:
                first_row = next(reader)
                fieldnames = [f"field_{i+1}" for i in range(len(first_row))]
                reader = csv.DictReader(StringIO(raw_data), fieldnames=fieldnames, delimiter=delimiter)
            
            count = 0
            for row in reader:
                if count >= max_records:
                    break
                parsed_records.append(dict(row))
                count += 1
                
        elif format_type == 'json':
            import json
            data = json.loads(raw_data)
            
            if isinstance(data, list):
                parsed_records = data[:max_records] 
            else:
                parsed_records = [data]
                
        # Apply basic field mappings for preview
        mappings = descriptor.get('mappings', [])
        preview_records = []
        
        for record in parsed_records:
            processed_record = {}
            for mapping in mappings:
                source_field = mapping.get('source_field')
                target_field = mapping.get('target_field', source_field)
                
                if source_field in record:
                    value = record[source_field]
                    processed_record[target_field] = str(value) if value is not None else ""
                    
            if processed_record:  # Only add if we got some data
                preview_records.append(processed_record)
        
        return preview_records if preview_records else parsed_records
        
    except Exception as e:
        logger.error(f"Preview parsing failed: {e}")
        return None


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
  
  # FULLY AUTOMATIC: Discover schema + generate descriptor + import (zero manual steps!)
  %(prog)s --input customers.csv --auto
  %(prog)s --input products.xml --auto --dry-run  # Preview before importing
  
  # Dry run to validate without importing
  %(prog)s --input customers.csv --descriptor descriptor.json --dry-run

Use Cases:
  --auto              : 🚀 FULLY AUTOMATIC: Discover schema + generate descriptor + import data
                        (zero manual configuration required!)
  --suggest-schema     : Diagnose which TrustGraph schemas might match your data
                        (uses --sample-chars to limit data sent for analysis)
  --generate-descriptor: Create/review the structured data language configuration  
                        (uses --sample-chars to limit data sent for analysis)
  --parse-only        : Validate that parsed data looks correct before import
                        (uses --sample-size to limit records processed, ignores --sample-chars)

For more information on the descriptor format, see:
  docs/tech-specs/structured-data-descriptor.md
""",
    )
    
    # Required arguments
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
    mode_group.add_argument(
        '--auto',
        action='store_true',
        help='Run full automatic pipeline: discover schema + generate descriptor + import data'
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
    
    # Input validation
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    # Mode-specific validation
    if args.parse_only and not args.descriptor:
        print("Error: --descriptor is required when using --parse-only", file=sys.stderr)
        sys.exit(1)
    
    # Warn about irrelevant parameters
    if args.parse_only and args.sample_chars != 500:  # 500 is the default
        print("Warning: --sample-chars is ignored in --parse-only mode (entire file is processed)", file=sys.stderr)
    
    if (args.suggest_schema or args.generate_descriptor) and args.sample_size != 100:  # 100 is default
        print("Warning: --sample-size is ignored in analysis modes, use --sample-chars instead", file=sys.stderr)
    
    # Require explicit mode selection - no implicit behavior
    if not any([args.suggest_schema, args.generate_descriptor, args.parse_only, args.auto]):
        print("Error: Must specify an operation mode", file=sys.stderr)
        print("Available modes:", file=sys.stderr)
        print("  --auto                 : Discover schema + generate descriptor + import", file=sys.stderr)
        print("  --suggest-schema       : Analyze data and suggest schemas", file=sys.stderr)
        print("  --generate-descriptor  : Generate descriptor from data", file=sys.stderr)
        print("  --parse-only          : Parse data without importing", file=sys.stderr)
        sys.exit(1)
    
    try:
        load_structured_data(
            api_url=args.api_url,
            input_file=args.input,
            descriptor_file=args.descriptor,
            suggest_schema=args.suggest_schema,
            generate_descriptor=args.generate_descriptor,
            parse_only=args.parse_only,
            auto=args.auto,
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