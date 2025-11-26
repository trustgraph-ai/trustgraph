"""
Multi-queue Pulsar message dumper for debugging TrustGraph message flows.

This utility monitors multiple Pulsar queues simultaneously and logs all messages
to a file with timestamps and pretty-printed formatting. Useful for debugging
message flows, diagnosing stuck services, and understanding system behavior.
"""

import pulsar
import sys
import json
from datetime import datetime
import argparse

def format_message(queue_name, msg):
    """Format a message with timestamp and queue name."""
    timestamp = datetime.now().isoformat()

    # Try to parse as JSON and pretty-print
    try:
        value = msg.value()

        # If it's bytes, decode it
        if isinstance(value, bytes):
            value = value.decode('utf-8')

        # If it's a string, try to parse as JSON
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                body = json.dumps(parsed, indent=2)
            except (json.JSONDecodeError, TypeError):
                body = value
        else:
            # Try to convert to dict for pretty printing
            try:
                # Pulsar schema objects have __dict__ or similar
                if hasattr(value, '__dict__'):
                    parsed = {k: v for k, v in value.__dict__.items()
                             if not k.startswith('_')}
                else:
                    parsed = str(value)
                body = json.dumps(parsed, indent=2, default=str)
            except (TypeError, AttributeError):
                body = str(value)

    except Exception as e:
        body = f"<Error formatting message: {e}>\n{msg.value()}"

    # Format the output
    header = f"\n{'='*80}\n[{timestamp}] Queue: {queue_name}\n{'='*80}\n"
    return header + body + "\n"

def main():
    parser = argparse.ArgumentParser(
        prog='tg-dump-queues',
        description='Monitor and dump messages from multiple Pulsar queues',
        epilog="""
Examples:
  # Monitor agent and prompt queues
  tg-dump-queues non-persistent://tg/request/agent:default \\
                 non-persistent://tg/request/prompt:default

  # Monitor with custom output file
  tg-dump-queues non-persistent://tg/request/agent:default \\
                 --output debug.log

  # Append to existing log file
  tg-dump-queues non-persistent://tg/request/agent:default \\
                 --output queue.log --append

Common queue patterns:
  - Agent requests:   non-persistent://tg/request/agent:default
  - Agent responses:  non-persistent://tg/response/agent:default
  - Prompt requests:  non-persistent://tg/request/prompt:default
  - Prompt responses: non-persistent://tg/response/prompt:default
  - LLM requests:     non-persistent://tg/request/text-completion:default
  - LLM responses:    non-persistent://tg/response/text-completion:default
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'queues',
        nargs='+',
        help='Pulsar queue names to monitor'
    )

    parser.add_argument(
        '--output', '-o',
        default='queue.log',
        help='Output file (default: queue.log)'
    )

    parser.add_argument(
        '--append', '-a',
        action='store_true',
        help='Append to output file instead of overwriting'
    )

    parser.add_argument(
        '--pulsar-host',
        default='pulsar://localhost:6650',
        help='Pulsar host URL (default: pulsar://localhost:6650)'
    )

    parser.add_argument(
        '--listener-name',
        default='localhost',
        help='Pulsar listener name (default: localhost)'
    )

    parser.add_argument(
        '--subscriber',
        default='debug',
        help='Subscriber name for queue subscription (default: debug)'
    )

    args = parser.parse_args()

    # Filter out any accidentally included flags
    queues = [q for q in args.queues if not q.startswith('--')]

    if not queues:
        parser.error("No queues specified")

    print(f"TrustGraph Queue Dumper")
    print(f"Monitoring {len(queues)} queue(s):")
    for q in queues:
        print(f"  - {q}")
    print(f"Output file: {args.output}")
    print(f"Mode: {'append' if args.append else 'overwrite'}")
    print(f"Press Ctrl+C to stop\n")

    # Connect to Pulsar
    try:
        client = pulsar.Client(args.pulsar_host, listener_name=args.listener_name)
    except Exception as e:
        print(f"Error connecting to Pulsar at {args.pulsar_host}: {e}", file=sys.stderr)
        sys.exit(1)

    # Subscribe to all queues
    consumers = []
    for queue in queues:
        try:
            consumer = client.subscribe(
                queue,
                args.subscriber,
                consumer_type=pulsar.ConsumerType.Shared
            )
            consumers.append((queue, consumer))
            print(f"✓ Subscribed to: {queue}")
        except Exception as e:
            print(f"✗ Error subscribing to {queue}: {e}", file=sys.stderr)

    if not consumers:
        print("\nNo consumers created. Exiting.", file=sys.stderr)
        client.close()
        sys.exit(1)

    print(f"\nListening for messages...\n")

    # Open output file (overwrite by default, append if --append specified)
    mode = 'a' if args.append else 'w'
    try:
        with open(args.output, mode) as f:
            f.write(f"\n{'#'*80}\n")
            f.write(f"# Session started: {datetime.now().isoformat()}\n")
            f.write(f"# Monitoring queues: {', '.join(queues)}\n")
            f.write(f"{'#'*80}\n")
            f.flush()

            try:
                # Process messages from all consumers
                while True:
                    for queue_name, consumer in consumers:
                        try:
                            # Non-blocking receive with timeout
                            msg = consumer.receive(timeout_millis=100)
                            consumer.acknowledge(msg)

                            # Format and write
                            output = format_message(queue_name, msg)
                            f.write(output)
                            f.flush()

                            # Also print to console (truncated)
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] {queue_name}: Message received")

                        except Exception as e:
                            # Timeout is normal, just continue silently
                            if "TimeOut" not in str(e) and "Timeout" not in str(e):
                                error_msg = f"Error receiving from {queue_name}: {e}\n"
                                f.write(error_msg)
                                f.flush()
                                print(error_msg, file=sys.stderr)

            except KeyboardInterrupt:
                print("\n\nStopping...")
                f.write(f"\n{'#'*80}\n")
                f.write(f"# Session ended: {datetime.now().isoformat()}\n")
                f.write(f"{'#'*80}\n")

    except IOError as e:
        print(f"Error writing to {args.output}: {e}", file=sys.stderr)
        sys.exit(1)

    # Cleanup
    for _, consumer in consumers:
        consumer.close()
    client.close()

    print(f"\nMessages logged to: {args.output}")

if __name__ == '__main__':
    main()
