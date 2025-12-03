"""
Multi-queue Pulsar message dumper for debugging TrustGraph message flows.

This utility monitors multiple Pulsar queues simultaneously and logs all messages
to a file with timestamps and pretty-printed formatting. Useful for debugging
message flows, diagnosing stuck services, and understanding system behavior.

Uses TrustGraph's Subscriber abstraction for future-proof pub/sub compatibility.
"""

import pulsar
from pulsar.schema import BytesSchema
import sys
import json
import asyncio
from datetime import datetime
import argparse

from trustgraph.base.subscriber import Subscriber

def format_message(queue_name, msg):
    """Format a message with timestamp and queue name."""
    timestamp = datetime.now().isoformat()

    # Try to parse as JSON and pretty-print
    try:
        # Handle both Message objects and raw bytes
        if hasattr(msg, 'value'):
            # Message object with .value() method
            value = msg.value()
        else:
            # Raw bytes from schema-less subscription
            value = msg

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
        body = f"<Error formatting message: {e}>\n{str(msg)}"

    # Format the output
    header = f"\n{'='*80}\n[{timestamp}] Queue: {queue_name}\n{'='*80}\n"
    return header + body + "\n"


async def monitor_queue(subscriber, queue_name, central_queue, monitor_id, shutdown_event):
    """
    Monitor a single queue via Subscriber and forward messages to central queue.

    Args:
        subscriber: Subscriber instance for this queue
        queue_name: Name of the queue (for logging)
        central_queue: asyncio.Queue to forward messages to
        monitor_id: Unique ID for this monitor's subscription
        shutdown_event: asyncio.Event to signal shutdown
    """
    msg_queue = None
    try:
        # Subscribe to all messages from this Subscriber
        msg_queue = await subscriber.subscribe_all(monitor_id)

        while not shutdown_event.is_set():
            try:
                # Read from Subscriber's internal queue with timeout
                msg = await asyncio.wait_for(msg_queue.get(), timeout=0.5)
                timestamp = datetime.now()
                formatted = format_message(queue_name, msg)

                # Forward to central queue for writing
                await central_queue.put((timestamp, queue_name, formatted))
            except asyncio.TimeoutError:
                # No message, check shutdown flag again
                continue

    except Exception as e:
        if not shutdown_event.is_set():
            error_msg = f"\n{'='*80}\n[{datetime.now().isoformat()}] ERROR in monitor for {queue_name}\n{'='*80}\n{e}\n"
            await central_queue.put((datetime.now(), queue_name, error_msg))
    finally:
        # Clean unsubscribe
        if msg_queue is not None:
            try:
                await subscriber.unsubscribe_all(monitor_id)
            except Exception:
                pass


async def log_writer(central_queue, file_handle, shutdown_event, console_output=True):
    """
    Write messages from central queue to file.

    Args:
        central_queue: asyncio.Queue containing (timestamp, queue_name, formatted_msg) tuples
        file_handle: Open file handle to write to
        shutdown_event: asyncio.Event to signal shutdown
        console_output: Whether to print abbreviated messages to console
    """
    try:
        while not shutdown_event.is_set():
            try:
                # Wait for messages with timeout to check shutdown flag
                timestamp, queue_name, formatted_msg = await asyncio.wait_for(
                    central_queue.get(), timeout=0.5
                )

                # Write to file
                file_handle.write(formatted_msg)
                file_handle.flush()

                # Print abbreviated message to console
                if console_output:
                    time_str = timestamp.strftime('%H:%M:%S')
                    print(f"[{time_str}] {queue_name}: Message received")
            except asyncio.TimeoutError:
                # No message, check shutdown flag again
                continue

    finally:
        # Flush remaining messages after shutdown
        while not central_queue.empty():
            try:
                timestamp, queue_name, formatted_msg = central_queue.get_nowait()
                file_handle.write(formatted_msg)
                file_handle.flush()
            except asyncio.QueueEmpty:
                break


async def async_main(queues, output_file, pulsar_host, listener_name, subscriber_name, append_mode):
    """
    Main async function to monitor multiple queues concurrently.

    Args:
        queues: List of queue names to monitor
        output_file: Path to output file
        pulsar_host: Pulsar connection URL
        listener_name: Pulsar listener name
        subscriber_name: Base name for subscribers
        append_mode: Whether to append to existing file
    """
    print(f"TrustGraph Queue Dumper")
    print(f"Monitoring {len(queues)} queue(s):")
    for q in queues:
        print(f"  - {q}")
    print(f"Output file: {output_file}")
    print(f"Mode: {'append' if append_mode else 'overwrite'}")
    print(f"Press Ctrl+C to stop\n")

    # Connect to Pulsar
    try:
        client = pulsar.Client(pulsar_host, listener_name=listener_name)
    except Exception as e:
        print(f"Error connecting to Pulsar at {pulsar_host}: {e}", file=sys.stderr)
        sys.exit(1)

    # Create Subscribers and central queue
    central_queue = asyncio.Queue()
    subscribers = []

    for queue_name in queues:
        try:
            sub = Subscriber(
                client=client,
                topic=queue_name,
                subscription=subscriber_name,
                consumer_name=f"{subscriber_name}-{queue_name}",
                schema=None,  # No schema - accept any message type
            )
            await sub.start()
            subscribers.append((queue_name, sub))
            print(f"✓ Subscribed to: {queue_name}")
        except Exception as e:
            print(f"✗ Error subscribing to {queue_name}: {e}", file=sys.stderr)

    if not subscribers:
        print("\nNo subscribers created. Exiting.", file=sys.stderr)
        client.close()
        sys.exit(1)

    print(f"\nListening for messages...\n")

    # Open output file
    mode = 'a' if append_mode else 'w'
    try:
        with open(output_file, mode) as f:
            f.write(f"\n{'#'*80}\n")
            f.write(f"# Session started: {datetime.now().isoformat()}\n")
            f.write(f"# Monitoring queues: {', '.join(queues)}\n")
            f.write(f"{'#'*80}\n")
            f.flush()

            # Create shutdown event for clean coordination
            shutdown_event = asyncio.Event()

            # Start monitoring tasks
            tasks = []
            try:
                # Create one monitor task per subscriber
                for queue_name, sub in subscribers:
                    task = asyncio.create_task(
                        monitor_queue(sub, queue_name, central_queue, "logger", shutdown_event)
                    )
                    tasks.append(task)

                # Create single writer task
                writer_task = asyncio.create_task(
                    log_writer(central_queue, f, shutdown_event)
                )
                tasks.append(writer_task)

                # Wait for all tasks (they check shutdown_event)
                await asyncio.gather(*tasks)

            except KeyboardInterrupt:
                print("\n\nStopping...")
            finally:
                # Signal shutdown to all tasks
                shutdown_event.set()

                # Wait for tasks to finish cleanly (with timeout)
                try:
                    await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=2.0)
                except asyncio.TimeoutError:
                    print("Warning: Shutdown timeout", file=sys.stderr)

                # Write session end marker
                f.write(f"\n{'#'*80}\n")
                f.write(f"# Session ended: {datetime.now().isoformat()}\n")
                f.write(f"{'#'*80}\n")

    except IOError as e:
        print(f"Error writing to {output_file}: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Clean shutdown of Subscribers
        for _, sub in subscribers:
            await sub.stop()
        client.close()

    print(f"\nMessages logged to: {output_file}")

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

IMPORTANT:
  This tool subscribes to queues without a schema (schema-less mode). To avoid
  schema conflicts, ensure that TrustGraph services and flows are already started
  before running this tool. If this tool subscribes first, the real services may
  encounter schema mismatch errors when they try to connect.

  Best practice: Start services → Set up flows → Run tg-dump-queues
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

    # Run async main
    try:
        asyncio.run(async_main(
            queues=queues,
            output_file=args.output,
            pulsar_host=args.pulsar_host,
            listener_name=args.listener_name,
            subscriber_name=args.subscriber,
            append_mode=args.append
        ))
    except KeyboardInterrupt:
        # Already handled in async_main
        pass
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
