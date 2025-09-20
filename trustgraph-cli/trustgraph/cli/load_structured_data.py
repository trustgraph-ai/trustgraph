"""
Load structured data into TrustGraph using a descriptor configuration.

This utility can:
1. Analyze data samples to discover appropriate schemas
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
    discover_schema: bool = False,
    generate_descriptor: bool = False,
    parse_only: bool = False,
    load: bool = False,
    auto: bool = False,
    output_file: str = None,
    sample_size: int = 100,
    sample_chars: int = 500,
    schema_name: str = None,
    flow: str = 'default',
    user: str = 'trustgraph',
    collection: str = 'default',
    dry_run: bool = False,
    verbose: bool = False
):
    """
    Load structured data using a descriptor configuration.
    
    Args:
        api_url: TrustGraph API URL
        input_file: Path to input data file
        descriptor_file: Path to JSON descriptor configuration
        discover_schema: Analyze data and discover matching schemas
        generate_descriptor: Generate descriptor from data sample
        parse_only: Parse data but don't import to TrustGraph
        load: Load data to TrustGraph using existing descriptor
        auto: Run full automatic pipeline (discover schema + generate descriptor + import)
        output_file: Path to write output (descriptor/parsed data)
        sample_size: Number of records to sample for analysis
        sample_chars: Maximum characters to read for sampling
        schema_name: Target schema name for generation
        flow: TrustGraph flow name to use for prompts
        user: User name for metadata (default: trustgraph)
        collection: Collection name for metadata (default: default)
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
        
        # Step 1: Auto-discover schema (reuse discover_schema logic)
        discovered_schema = _auto_discover_schema(api_url, input_file, sample_chars, flow, logger)
        if not discovered_schema:
            logger.error("Failed to discover suitable schema automatically")
            print("❌ Could not automatically determine the best schema for your data.")
            print("💡 Try running with --discover-schema first to see available options.")
            return None
            
        logger.info(f"✅ Discovered schema: {discovered_schema}")
        print(f"🎯 Auto-selected schema: {discovered_schema}")
        
        # Step 2: Auto-generate descriptor
        logger.info("Step 2: Generating descriptor configuration...")
        auto_descriptor = _auto_generate_descriptor(api_url, input_file, discovered_schema, sample_chars, flow, logger)
        if not auto_descriptor:
            logger.error("Failed to generate descriptor automatically")
            print("❌ Could not automatically generate descriptor configuration.")
            return None
            
        logger.info("✅ Generated descriptor configuration")
        print("📝 Generated descriptor configuration")
        
        # Step 3: Parse and preview data using shared pipeline  
        logger.info("Step 3: Parsing and validating data...")
        
        # Create temporary descriptor file for validation
        import tempfile
        temp_descriptor = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(auto_descriptor, temp_descriptor, indent=2)
        temp_descriptor.close()
        
        try:
            # Use shared pipeline for preview (small sample)
            preview_objects, _ = _process_data_pipeline(input_file, temp_descriptor.name, user, collection, sample_size=5)
            
            # Show preview
            print("📊 Data Preview (first few records):")
            print("=" * 50)
            for i, obj in enumerate(preview_objects[:3], 1):
                values = obj.get('values', {})
                print(f"Record {i}: {values}")
            print("=" * 50)
            
            # Step 4: Import (unless dry_run)
            if dry_run:
                logger.info("✅ Dry run complete - data is ready for import")
                print("✅ Dry run successful! Data is ready for import.")
                print(f"💡 Run without --dry-run to import data to TrustGraph.")
                return None
            else:
                logger.info("Step 4: Importing data to TrustGraph...")
                print("🚀 Importing data to TrustGraph...")
                
                # Use shared pipeline for full processing (no sample limit)
                output_objects, descriptor = _process_data_pipeline(input_file, temp_descriptor.name, user, collection)
                
                # Get batch size from descriptor
                batch_size = descriptor.get('output', {}).get('options', {}).get('batch_size', 1000)
                
                # Send to TrustGraph using shared function
                imported_count = _send_to_trustgraph(output_objects, api_url, flow, batch_size)
                
                # Summary
                format_info = descriptor.get('format', {})
                format_type = format_info.get('type', 'csv').lower()
                schema_name = descriptor.get('output', {}).get('schema_name', 'default')
                
                print(f"\n🎉 Auto-Import Complete!")
                print(f"- Input format: {format_type}")
                print(f"- Target schema: {schema_name}")
                print(f"- Records imported: {imported_count}")
                print(f"- Flow used: {flow}")
                
                logger.info("Auto-import pipeline completed successfully")
                return imported_count
                
        except Exception as e:
            logger.error(f"Auto-import failed: {e}")
            print(f"❌ Auto-import failed: {e}")
            return None
            
        finally:
            # Clean up temp descriptor file
            try:
                import os
                os.unlink(temp_descriptor.name)
            except:
                pass
    
    elif discover_schema:
        logger.info(f"Analyzing {input_file} to discover schemas...")
        logger.info(f"Sample size: {sample_size} records")
        logger.info(f"Sample chars: {sample_chars} characters")
        
        # Use the helper function to discover schema (get raw response for display)
        response = _auto_discover_schema(api_url, input_file, sample_chars, flow, logger, return_raw_response=True)
        
        if response:
            # Debug: print response type and content 
            logger.debug(f"Response type: {type(response)}, content: {response}")
            if isinstance(response, list) and len(response) == 1:
                # Just print the schema name for clean output
                print(f"Best matching schema: {response[0]}")
            elif isinstance(response, list):
                # Multiple schemas - show the list
                print("Multiple schemas found:")
                for schema in response:
                    print(f"  - {schema}")
            else:
                # Show full response for debugging
                print("Schema Discovery Results:")
                print("=" * 50)
                print(response)
                print("=" * 50)
        else:
            print("Could not determine the best matching schema for your data.")
            print("Available schemas can be viewed using: tg-config-list schema")
        
    elif generate_descriptor:
        logger.info(f"Generating descriptor from {input_file}...")
        logger.info(f"Sample size: {sample_size} records")
        logger.info(f"Sample chars: {sample_chars} characters")
        
        # If no schema specified, discover it first
        if not schema_name:
            logger.info("No schema specified, auto-discovering...")
            schema_name = _auto_discover_schema(api_url, input_file, sample_chars, flow, logger)
            if not schema_name:
                print("Error: Could not determine schema automatically.")
                print("Please specify a schema using --schema-name or run --discover-schema first.")
                return
            logger.info(f"Auto-selected schema: {schema_name}")
        else:
            logger.info(f"Target schema: {schema_name}")
        
        # Generate descriptor using helper function
        descriptor = _auto_generate_descriptor(api_url, input_file, schema_name, sample_chars, flow, logger)
        
        if descriptor:
            # Output the generated descriptor
            if output_file:
                try:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(json.dumps(descriptor, indent=2))
                    print(f"Generated descriptor saved to: {output_file}")
                    logger.info(f"Descriptor saved to {output_file}")
                except Exception as e:
                    logger.error(f"Failed to save descriptor to {output_file}: {e}")
                    print(f"Error saving descriptor: {e}")
            else:
                print("Generated Descriptor:")
                print("=" * 50)
                print(json.dumps(descriptor, indent=2))
                print("=" * 50)
                print("Use this descriptor with --parse-only to validate or without modes to import.")
        else:
            print("Error: Failed to generate descriptor.")
            print("Check the logs for details or try --discover-schema to verify schema availability.")
            
    elif parse_only:
        if not descriptor_file:
            raise ValueError("--descriptor is required when using --parse-only")
        logger.info(f"Parsing {input_file} with descriptor {descriptor_file}...")
        
        # Use shared pipeline
        output_records, descriptor = _process_data_pipeline(input_file, descriptor_file, user, collection, sample_size)
        
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
        
        # Get summary info from descriptor
        format_info = descriptor.get('format', {})
        format_type = format_info.get('type', 'csv').lower()
        schema_name = descriptor.get('output', {}).get('schema_name', 'default')
        mappings = descriptor.get('mappings', [])
        
        print(f"\nParsing Summary:")
        print(f"- Input format: {format_type}")
        print(f"- Records processed: {len(output_records)}")
        print(f"- Target schema: {schema_name}")
        print(f"- Field mappings: {len(mappings)}")
        
    elif load:
        if not descriptor_file:
            raise ValueError("--descriptor is required when using --load")
        logger.info(f"Loading {input_file} to TrustGraph using descriptor {descriptor_file}...")
        
        # Use shared pipeline (no sample_size limit for full load)
        output_records, descriptor = _process_data_pipeline(input_file, descriptor_file, user, collection)
        
        # Get batch size from descriptor or use default
        batch_size = descriptor.get('output', {}).get('options', {}).get('batch_size', 1000)
        
        # Send to TrustGraph
        print(f"🚀 Importing {len(output_records)} records to TrustGraph...")
        imported_count = _send_to_trustgraph(output_records, api_url, flow, batch_size)
        
        # Get summary info from descriptor
        format_info = descriptor.get('format', {})
        format_type = format_info.get('type', 'csv').lower()
        schema_name = descriptor.get('output', {}).get('schema_name', 'default')
        
        print(f"\n🎉 Load Complete!")
        print(f"- Input format: {format_type}")
        print(f"- Target schema: {schema_name}")
        print(f"- Records imported: {imported_count}")
        print(f"- Flow used: {flow}")


# Shared core functions
def _load_descriptor(descriptor_file):
    """Load and validate descriptor configuration"""
    try:
        with open(descriptor_file, 'r', encoding='utf-8') as f:
            descriptor = json.load(f)
        logger.info(f"Loaded descriptor configuration from {descriptor_file}")
        return descriptor
    except Exception as e:
        logger.error(f"Failed to load descriptor file: {e}")
        raise


def _read_input_data(input_file, format_info):
    """Read raw data based on format type"""
    try:
        encoding = format_info.get('encoding', 'utf-8')
        
        with open(input_file, 'r', encoding=encoding) as f:
            raw_data = f.read()
        
        logger.info(f"Read {len(raw_data)} characters from input file")
        return raw_data
        
    except Exception as e:
        logger.error(f"Failed to read input file: {e}")
        raise


def _parse_data_by_format(raw_data, format_info, sample_size=None):
    """Parse raw data into records based on format (CSV/JSON/XML)"""
    format_type = format_info.get('type', 'csv').lower()
    parsed_records = []
    
    logger.info(f"Input format: {format_type}")
    
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
                # Respect sample_size limit if provided
                if sample_size and row_num > sample_size:
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
                parsed_records = data[:sample_size] if sample_size else data
            elif isinstance(data, dict):
                # Handle single object or extract array from root path
                root_path = format_info.get('options', {}).get('root_path')
                if root_path:
                    # Simple JSONPath-like extraction (basic implementation)
                    if root_path.startswith('$.'):
                        key = root_path[2:]
                        data = data.get(key, data)
                
                if isinstance(data, list):
                    parsed_records = data[:sample_size] if sample_size else data
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
                if sample_size and record_count >= sample_size:
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
    return parsed_records


def _apply_transformations(records, mappings):
    """Apply descriptor mappings and transformations"""
    processed_records = []
    
    for record_num, record in enumerate(records, start=1):
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
    
    return processed_records


def _format_extracted_objects(processed_records, descriptor, user, collection):
    """Convert to TrustGraph ExtractedObject format"""
    output_records = []
    schema_name = descriptor.get('output', {}).get('schema_name', 'default')
    confidence = descriptor.get('output', {}).get('options', {}).get('confidence', 0.9)
    
    for record in processed_records:
        output_record = {
            "metadata": {
                "id": f"parsed-{len(output_records)+1}",
                "metadata": [],  # Empty metadata triples
                "user": user,
                "collection": collection
            },
            "schema_name": schema_name,
            "values": record,
            "confidence": confidence,
            "source_span": ""
        }
        output_records.append(output_record)
    
    return output_records


def _process_data_pipeline(input_file, descriptor_file, user, collection, sample_size=None):
    """Shared pipeline: load descriptor → read → parse → transform → format"""
    # Load descriptor configuration
    descriptor = _load_descriptor(descriptor_file)
    
    # Read input data based on format in descriptor
    format_info = descriptor.get('format', {})
    raw_data = _read_input_data(input_file, format_info)
    
    # Parse data based on format type
    parsed_records = _parse_data_by_format(raw_data, format_info, sample_size)
    
    # Apply transformations and validation
    mappings = descriptor.get('mappings', [])
    processed_records = _apply_transformations(parsed_records, mappings)
    
    # Format output for TrustGraph ExtractedObject structure
    output_records = _format_extracted_objects(processed_records, descriptor, user, collection)
    
    return output_records, descriptor


def _send_to_trustgraph(objects, api_url, flow, batch_size=1000):
    """Send ExtractedObject records to TrustGraph using WebSocket"""
    import json
    import asyncio
    from websockets.asyncio.client import connect
    
    try:
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
                
                for record in objects:
                    try:
                        # Send individual ExtractedObject records
                        await ws.send(json.dumps(record))
                        imported_count += 1
                        
                        if imported_count % 100 == 0:
                            logger.info(f"Imported {imported_count}/{len(objects)} records...")
                            print(f"✅ Imported {imported_count}/{len(objects)} records...")
                            
                    except Exception as e:
                        logger.error(f"Failed to send record {imported_count + 1}: {e}")
                        print(f"❌ Failed to send record {imported_count + 1}: {e}")
                
                logger.info(f"Successfully imported {imported_count} records to TrustGraph")
                return imported_count
        
        # Run the async import
        imported_count = asyncio.run(import_objects())
        
        # Summary
        total_records = len(objects)
        failed_count = total_records - imported_count
        
        print(f"\n📊 Import Summary:")
        print(f"- Total records: {total_records}")
        print(f"- Successfully imported: {imported_count}")
        print(f"- Failed: {failed_count}")
        
        if failed_count > 0:
            print(f"⚠️  {failed_count} records failed to import. Check logs for details.")
        else:
            print("✅ All records imported successfully!")
            
        return imported_count
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        print(f"Error: Required modules not available - {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to import data to TrustGraph: {e}")
        print(f"Import failed: {e}")
        raise


# Helper functions for auto mode
def _auto_discover_schema(api_url, input_file, sample_chars, flow, logger, return_raw_response=False):
    """Auto-discover the best matching schema for the input data
    
    Args:
        api_url: TrustGraph API URL
        input_file: Path to input data file
        sample_chars: Number of characters to sample from file
        flow: TrustGraph flow name to use for prompts
        logger: Logger instance
        return_raw_response: If True, return raw prompt response; if False, parse to extract schema name
        
    Returns:
        Schema name (str) if return_raw_response=False, or full response if True
    """
    try:
        # Read sample data
        with open(input_file, 'r', encoding='utf-8') as f:
            sample_data = f.read(sample_chars)
            logger.info(f"Read {len(sample_data)} characters for analysis")
        
        # Import API modules
        from trustgraph.api import Api
        from trustgraph.api.types import ConfigKey
        api = Api(api_url)
        config_api = api.config()
        
        # Get available schemas
        logger.info("Fetching available schemas from Config API...")
        schema_keys = config_api.list("schema")
        logger.info(f"Found {len(schema_keys)} schemas: {schema_keys}")
        
        if not schema_keys:
            logger.error("No schemas available in TrustGraph configuration")
            return None
            
        # Get schema definitions
        schemas = {}
        for key in schema_keys:
            try:
                config_key = ConfigKey(type="schema", key=key)
                schema_values = config_api.get([config_key])
                if schema_values:
                    schema_def = json.loads(schema_values[0].value) if isinstance(schema_values[0].value, str) else schema_values[0].value
                    schemas[key] = schema_def
                    logger.debug(f"Loaded schema: {key}")
            except Exception as e:
                logger.warning(f"Could not load schema {key}: {e}")
                
        if not schemas:
            logger.error("No valid schemas could be loaded")
            return None
            
        logger.info(f"Successfully loaded {len(schemas)} schema definitions")
            
        # Use prompt service for schema selection
        flow_api = api.flow().id(flow)
        
        # Call schema-selection prompt with actual schemas and data sample
        logger.info("Calling TrustGraph schema-selection prompt...")
        response = flow_api.prompt(
            id="schema-selection",
            variables={
                "schemas": list(schemas.values()),  # Array of actual schema definitions
                "question": sample_data  # Truncate sample data
            }
        )
        
        # Return raw response if requested (for discover_schema mode)
        if return_raw_response:
            return response
        
        # Extract schema name from response
        if isinstance(response, dict) and 'schema' in response:
            return response['schema']
        elif isinstance(response, list) and len(response) > 0:
            # If response is a list, use the first element
            logger.info(f"Extracted schema '{response[0]}' from list response")
            return response[0]
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


def _auto_generate_descriptor(api_url, input_file, schema_name, sample_chars, flow, logger):
    """Auto-generate descriptor configuration for the discovered schema"""
    try:
        # Read sample data
        with open(input_file, 'r', encoding='utf-8') as f:
            sample_data = f.read(sample_chars)
        
        # Import API modules
        from trustgraph.api import Api
        from trustgraph.api.types import ConfigKey
        api = Api(api_url)
        config_api = api.config()
        
        # Get schema definition
        config_key = ConfigKey(type="schema", key=schema_name)
        schema_values = config_api.get([config_key])
        if not schema_values:
            logger.error(f"Schema '{schema_name}' not found")
            return None
        schema_def = json.loads(schema_values[0].value) if isinstance(schema_values[0].value, str) else schema_values[0].value
        
        # Use prompt service for descriptor generation
        flow_api = api.flow().id(flow)
        
        # Call diagnose-structured-data prompt with schema and data sample
        response = flow_api.prompt(
            id="diagnose-structured-data",
            variables={
                "schemas": [schema_def],  # Array with single schema definition
                "sample": sample_data  # Data sample for analysis
            }
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
  # Step 1: Analyze data and discover matching schemas
  %(prog)s --input customers.csv --discover-schema
  %(prog)s --input products.xml --discover-schema --sample-chars 1000
  
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
  --discover-schema     : Diagnose which TrustGraph schemas might match your data
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
        help='TrustGraph flow name to use for prompts and import (default: default)'
    )
    
    parser.add_argument(
        '--user',
        default='trustgraph',
        help='User name for metadata (default: trustgraph)'
    )
    
    parser.add_argument(
        '--collection',
        default='default',
        help='Collection name for metadata (default: default)'
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
        '--discover-schema',
        action='store_true',
        help='Analyze data sample and discover matching TrustGraph schemas'
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
        '--load',
        action='store_true',
        help='Load data to TrustGraph using existing descriptor'
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
        help='Maximum characters to read for sampling (discover-schema/generate-descriptor modes only, default: 500)'
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
        
    if args.load and not args.descriptor:
        print("Error: --descriptor is required when using --load", file=sys.stderr)
        sys.exit(1)
    
    # Warn about irrelevant parameters
    if args.parse_only and args.sample_chars != 500:  # 500 is the default
        print("Warning: --sample-chars is ignored in --parse-only mode (entire file is processed)", file=sys.stderr)
    
    if (args.discover_schema or args.generate_descriptor) and args.sample_size != 100:  # 100 is default
        print("Warning: --sample-size is ignored in analysis modes, use --sample-chars instead", file=sys.stderr)
    
    # Require explicit mode selection - no implicit behavior
    if not any([args.discover_schema, args.generate_descriptor, args.parse_only, args.load, args.auto]):
        print("Error: Must specify an operation mode", file=sys.stderr)
        print("Available modes:", file=sys.stderr)
        print("  --auto                 : Discover schema + generate descriptor + import", file=sys.stderr)
        print("  --discover-schema       : Analyze data and discover schemas", file=sys.stderr)
        print("  --generate-descriptor  : Generate descriptor from data", file=sys.stderr)
        print("  --parse-only          : Parse data without importing", file=sys.stderr)
        print("  --load                : Import data using existing descriptor", file=sys.stderr)
        sys.exit(1)
    
    try:
        load_structured_data(
            api_url=args.api_url,
            input_file=args.input,
            descriptor_file=args.descriptor,
            discover_schema=args.discover_schema,
            generate_descriptor=args.generate_descriptor,
            parse_only=args.parse_only,
            load=args.load,
            auto=args.auto,
            output_file=args.output,
            sample_size=args.sample_size,
            sample_chars=args.sample_chars,
            schema_name=args.schema_name,
            flow=args.flow,
            user=args.user,
            collection=args.collection,
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
