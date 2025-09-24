"""
Confidence Agent Entry Point

Main entry point for running the confidence-based agent as a standalone service.
"""

import sys
import asyncio
import logging
import argparse
from typing import Dict, Any

from .service import Processor


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="TrustGraph Confidence-Based Agent Service"
    )
    
    # Service configuration
    parser.add_argument(
        "--id", 
        type=str, 
        default="confidence-agent",
        help="Service identifier"
    )
    
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=15,
        help="Maximum number of agent iterations"
    )
    
    # Confidence thresholds
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.75,
        help="Default confidence threshold (0.0-1.0)"
    )
    
    parser.add_argument(
        "--graph-query-threshold",
        type=float, 
        default=0.8,
        help="Confidence threshold for GraphQuery operations"
    )
    
    parser.add_argument(
        "--text-completion-threshold",
        type=float,
        default=0.7, 
        help="Confidence threshold for TextCompletion operations"
    )
    
    parser.add_argument(
        "--mcp-tool-threshold",
        type=float,
        default=0.6,
        help="Confidence threshold for McpTool operations"
    )
    
    # Retry configuration
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum number of retries for low confidence steps"
    )
    
    parser.add_argument(
        "--retry-backoff-factor",
        type=float,
        default=2.0,
        help="Backoff factor for retry delays"
    )
    
    # Step execution
    parser.add_argument(
        "--step-timeout-ms",
        type=int,
        default=30000,
        help="Default timeout for step execution (milliseconds)"
    )
    
    parser.add_argument(
        "--parallel-execution",
        action="store_true",
        help="Enable parallel execution of independent steps"
    )
    
    # User interaction
    parser.add_argument(
        "--override-enabled",
        action="store_true",
        default=True,
        help="Enable user override for low confidence results"
    )
    
    # Logging
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    
    parser.add_argument(
        "--audit-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO", 
        help="Audit logging level"
    )
    
    # Pulsar configuration (standard TrustGraph parameters)
    parser.add_argument(
        "--pulsar-endpoint",
        type=str,
        default="pulsar://localhost:6650",
        help="Pulsar broker endpoint"
    )
    
    return parser.parse_args()


def setup_logging(log_level: str, audit_level: str):
    """Setup logging configuration."""
    
    # Configure main logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure audit logging with separate level
    audit_logger = logging.getLogger("confidence_agent_audit")
    audit_logger.setLevel(getattr(logging, audit_level.upper()))
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: main={log_level}, audit={audit_level}")


async def main():
    """Main entry point."""
    args = parse_args()
    
    # Setup logging
    setup_logging(args.log_level, args.audit_level)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting TrustGraph Confidence-Based Agent Service")
    
    # Build service parameters
    params = {
        "id": args.id,
        "max_iterations": args.max_iterations,
        "confidence_threshold": args.confidence_threshold,
        "graph_query_threshold": args.graph_query_threshold,
        "text_completion_threshold": args.text_completion_threshold,
        "mcp_tool_threshold": args.mcp_tool_threshold,
        "max_retries": args.max_retries,
        "retry_backoff_factor": args.retry_backoff_factor,
        "step_timeout_ms": args.step_timeout_ms,
        "parallel_execution": args.parallel_execution,
        "override_enabled": args.override_enabled,
        "pulsar_endpoint": args.pulsar_endpoint,
    }
    
    # Log configuration
    logger.info("Service configuration:")
    for key, value in params.items():
        logger.info(f"  {key}: {value}")
    
    try:
        # Create and run the service
        processor = Processor(**params)
        
        logger.info("Confidence agent service initialized successfully")
        
        # Run the service (this will block)
        await processor.run()
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Service failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Confidence agent service stopped")


def cli_main():
    """Entry point for command line execution."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli_main()