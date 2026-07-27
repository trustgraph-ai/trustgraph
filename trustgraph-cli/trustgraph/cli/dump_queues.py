"""
Multi-queue message dumper for debugging TrustGraph message flows.

This utility monitors multiple queues simultaneously and logs all messages
to a file with timestamps and pretty-printed formatting. Useful for debugging
message flows, diagnosing stuck services, and understanding system behavior.
"""

import sys
import json
import asyncio
from datetime import datetime
import argparse

from trustgraph.base.pubsub import get_async_pubsub, add_pubsub_args

def decode_json_strings(obj):
    """Recursively decode JSON-encoded string values within a dict/list."""
    if isinstance(obj, dict):
        return {k: decode_json_strings(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [decode_json_strings(v) for v in obj]
    if isinstance(obj, str):
        try:
            parsed = json.loads(obj)
            if isinstance(parsed, (dict, list)):
                return decode_json_strings(parsed)
        except (json.JSONDecodeError, TypeError):
            pass
    return obj


def to_dict(value):
    """Recursively convert a value to a JSON-serialisable structure."""

    if value is None or isinstance(value, (bool, int, float)):
        return value

    if isinstance(value, bytes):
        value = value.decode('utf-8')

    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    if isinstance(value, dict):
        return {k: to_dict(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [to_dict(v) for v in value]

    if hasattr(value, '__dict__'):
        return {
            k: to_dict(v) for k, v in value.__dict__.items()
            if not k.startswith('_')
        }

    return str(value)


def format_message(queue_name, msg):
    """Format a message with timestamp and queue name."""
    timestamp = datetime.now().isoformat()

    try:
        value = msg.value() if hasattr(msg, 'value') else msg
        parsed = to_dict(value)

        if isinstance(parsed, (dict, list)):
            parsed = decode_json_strings(parsed)
            body = json.dumps(parsed, indent=2, default=str)
        else:
            body = str(parsed)

    except Exception as e:
        body = f"<Error formatting message: {e}>\n{str(msg)}"

    header = f"\n{'='*80}\n[{timestamp}] Queue: {queue_name}\n{'='*80}\n"
    return header + body + "\n"


async def monitor_queue(consumer, queue_name, central_queue, shutdown_event):
    try:
        while not shutdown_event.is_set():
            try:
                msg = await asyncio.wait_for(
                    consumer.receive(), timeout=0.5,
                )
                timestamp = datetime.now()
                formatted = format_message(queue_name, msg)
                await consumer.acknowledge(msg)
                await central_queue.put((timestamp, queue_name, formatted))
            except asyncio.TimeoutError:
                continue

    except Exception as e:
        if not shutdown_event.is_set():
            error_msg = (
                f"\n{'='*80}\n"
                f"[{datetime.now().isoformat()}] "
                f"ERROR in monitor for {queue_name}\n"
                f"{'='*80}\n{e}\n"
            )
            await central_queue.put((datetime.now(), queue_name, error_msg))


async def log_writer(central_queue, file_handle, shutdown_event, console_output=True):
    try:
        while not shutdown_event.is_set():
            try:
                timestamp, queue_name, formatted_msg = await asyncio.wait_for(
                    central_queue.get(), timeout=0.5
                )

                file_handle.write(formatted_msg)
                file_handle.flush()

                if console_output:
                    time_str = timestamp.strftime('%H:%M:%S')
                    print(f"[{time_str}] {queue_name}: Message received")
            except asyncio.TimeoutError:
                continue

    finally:
        while not central_queue.empty():
            try:
                timestamp, queue_name, formatted_msg = central_queue.get_nowait()
                file_handle.write(formatted_msg)
                file_handle.flush()
            except asyncio.QueueEmpty:
                break


async def async_main(queues, output_file, subscriber_name, append_mode, **pubsub_config):
    print(f"TrustGraph Queue Dumper")
    print(f"Monitoring {len(queues)} queue(s):")
    for q in queues:
        print(f"  - {q}")
    print(f"Output file: {output_file}")
    print(f"Mode: {'append' if append_mode else 'overwrite'}")
    print(f"Press Ctrl+C to stop\n")

    try:
        backend = get_async_pubsub(**pubsub_config)
    except Exception as e:
        print(f"Error connecting to backend: {e}", file=sys.stderr)
        sys.exit(1)

    central_queue = asyncio.Queue()
    consumers = []

    for queue_name in queues:
        try:
            consumer = await backend.create_consumer(
                topic=queue_name,
                subscription=subscriber_name,
                schema=None,
                initial_position='latest',
            )
            consumers.append((queue_name, consumer))
            print(f"  Subscribed to: {queue_name}")
        except Exception as e:
            print(f"  Error subscribing to {queue_name}: {e}", file=sys.stderr)

    if not consumers:
        print("\nNo consumers created. Exiting.", file=sys.stderr)
        await backend.close()
        sys.exit(1)

    print(f"\nListening for messages...\n")

    mode = 'a' if append_mode else 'w'
    try:
        with open(output_file, mode) as f:
            f.write(f"\n{'#'*80}\n")
            f.write(f"# Session started: {datetime.now().isoformat()}\n")
            f.write(f"# Monitoring queues: {', '.join(queues)}\n")
            f.write(f"{'#'*80}\n")
            f.flush()

            shutdown_event = asyncio.Event()

            tasks = []
            try:
                for queue_name, consumer in consumers:
                    task = asyncio.create_task(
                        monitor_queue(
                            consumer, queue_name,
                            central_queue, shutdown_event,
                        )
                    )
                    tasks.append(task)

                writer_task = asyncio.create_task(
                    log_writer(central_queue, f, shutdown_event)
                )
                tasks.append(writer_task)

                await asyncio.gather(*tasks)

            except KeyboardInterrupt:
                print("\n\nStopping...")
            finally:
                shutdown_event.set()

                try:
                    await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout=2.0,
                    )
                except asyncio.TimeoutError:
                    print("Warning: Shutdown timeout", file=sys.stderr)

                f.write(f"\n{'#'*80}\n")
                f.write(f"# Session ended: {datetime.now().isoformat()}\n")
                f.write(f"{'#'*80}\n")

    except IOError as e:
        print(f"Error writing to {output_file}: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        for _, consumer in consumers:
            await consumer.close()
        await backend.close()

    print(f"\nMessages logged to: {output_file}")

def main():
    parser = argparse.ArgumentParser(
        prog='tg-dump-queues',
        description='Monitor and dump messages from multiple queues',
        epilog="""
Examples:
  # Monitor agent and prompt flow queues
  tg-dump-queues flow:tg:agent-request:default \\
                 flow:tg:prompt-request:default

  # Monitor with custom output file
  tg-dump-queues flow:tg:agent-request:default \\
                 --output debug.log

  # Append to existing log file
  tg-dump-queues flow:tg:agent-request:default \\
                 --output queue.log --append

IMPORTANT:
  This tool subscribes to queues without a schema (schema-less mode). To avoid
  schema conflicts, ensure that TrustGraph services and flows are already started
  before running this tool. If this tool subscribes first, the real services may
  encounter schema mismatch errors when they try to connect.

  Best practice: Start services -> Set up flows -> Run tg-dump-queues
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'queues',
        nargs='+',
        help='Queue names to monitor'
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

    add_pubsub_args(parser)
    parser.set_defaults(pulsar_listener='external')

    parser.add_argument(
        '--subscriber',
        default='debug',
        help='Subscriber name for queue subscription (default: debug)'
    )

    args = parser.parse_args()

    queues = [q for q in args.queues if not q.startswith('--')]

    if not queues:
        parser.error("No queues specified")

    try:
        asyncio.run(async_main(
            queues=queues,
            output_file=args.output,
            subscriber_name=args.subscriber,
            append_mode=args.append,
            **{k: v for k, v in vars(args).items()
               if k not in ('queues', 'output', 'subscriber', 'append')},
        ))
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
