"""
Monitor prompt request/response queues and log activity with timing.

Subscribes to prompt request and response Pulsar queues, correlates
them by message ID, and logs a summary of each request/response with
elapsed time.

Examples:
  tg-monitor-prompts
  tg-monitor-prompts --flow default --max-lines 5
  tg-monitor-prompts --queue-type prompt-rag
"""

import json
import asyncio
import sys
import argparse
from datetime import datetime
from collections import OrderedDict

from trustgraph.base.subscriber import Subscriber
from trustgraph.base.pubsub import get_pubsub

default_flow = "default"
default_queue_type = "prompt"
default_max_lines = 3
default_max_width = 80


def truncate_text(text, max_lines, max_width):
    """Truncate text to max_lines lines, each at most max_width chars."""
    if not text:
        return "(empty)"

    lines = text.splitlines()
    result = []
    for line in lines[:max_lines]:
        if len(line) > max_width:
            result.append(line[:max_width - 3] + "...")
        else:
            result.append(line)

    if len(lines) > max_lines:
        result.append(f"  ... ({len(lines) - max_lines} more lines)")

    return "\n".join(result)


def format_terms(terms, max_lines, max_width):
    """Format prompt terms for display."""
    if not terms:
        return "(no terms)"

    parts = []
    for key, value in terms.items():
        # Try to parse JSON-encoded values
        try:
            parsed = json.loads(value)
            if isinstance(parsed, str):
                value = parsed
            else:
                value = json.dumps(parsed, indent=2)
        except (json.JSONDecodeError, TypeError):
            pass

        truncated = truncate_text(str(value), max_lines, max_width)
        parts.append(f"  {key}: {truncated}")

    return "\n".join(parts)


async def monitor_queue(subscriber, queue_name, central_queue, monitor_id,
                        shutdown_event):
    """Monitor a single queue and forward messages to central queue."""
    msg_queue = None
    try:
        msg_queue = await subscriber.subscribe_all(monitor_id)

        while not shutdown_event.is_set():
            try:
                msg = await asyncio.wait_for(msg_queue.get(), timeout=0.5)
                timestamp = datetime.now()
                await central_queue.put((timestamp, queue_name, msg))
            except asyncio.TimeoutError:
                continue

    except Exception as e:
        if not shutdown_event.is_set():
            print(f"Error monitoring {queue_name}: {e}", file=sys.stderr)
    finally:
        if msg_queue is not None:
            try:
                await subscriber.unsubscribe_all(monitor_id)
            except Exception:
                pass


def parse_message(msg):
    """Parse a Pulsar message into (id, body_dict)."""
    # Get correlation ID from properties
    try:
        props = msg.properties()
        msg_id = props.get("id", "")
    except Exception:
        msg_id = ""

    # Parse body
    try:
        value = msg.value()
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        body = json.loads(value) if isinstance(value, str) else {}
    except Exception:
        body = {}

    return msg_id, body


async def process_messages(central_queue, request_queue_name,
                           response_queue_name, max_lines, max_width,
                           shutdown_event):
    """Process messages from central queue, correlating requests/responses."""

    # Track in-flight requests: id -> (timestamp, template_id)
    in_flight = OrderedDict()

    while not shutdown_event.is_set():
        try:
            timestamp, queue_name, msg = await asyncio.wait_for(
                central_queue.get(), timeout=0.5
            )
        except asyncio.TimeoutError:
            continue

        msg_id, body = parse_message(msg)
        time_str = timestamp.strftime("%H:%M:%S.%f")[:-3]

        if queue_name == request_queue_name:
            # Request
            template_id = body.get("id", "(unknown)")
            terms = body.get("terms", {})
            streaming = body.get("streaming", False)

            in_flight[msg_id] = (timestamp, template_id)

            # Limit in_flight size to avoid unbounded growth
            while len(in_flight) > 1000:
                in_flight.popitem(last=False)

            stream_flag = " [streaming]" if streaming else ""
            print(f"[{time_str}] REQ  {msg_id[:8]}  "
                  f"template={template_id}{stream_flag}")

            if terms:
                print(format_terms(terms, max_lines, max_width))

        elif queue_name == response_queue_name:
            # Response
            elapsed_str = ""
            template_id = ""

            if msg_id in in_flight:
                req_timestamp, template_id = in_flight.pop(msg_id)
                elapsed = (timestamp - req_timestamp).total_seconds()
                elapsed_str = f"  ({elapsed:.3f}s)"

            error = body.get("error")
            text = body.get("text", "")
            obj = body.get("object", "")
            eos = body.get("end_of_stream", False)

            if error:
                err_msg = error
                if isinstance(error, dict):
                    err_msg = error.get("message", str(error))
                print(f"[{time_str}] ERR  {msg_id[:8]}  "
                      f"{err_msg}{elapsed_str}")
            elif eos:
                print(f"[{time_str}] END  {msg_id[:8]}"
                      f"{elapsed_str}")
            elif text:
                truncated = truncate_text(text, max_lines, max_width)
                print(f"[{time_str}] RESP {msg_id[:8]}"
                      f"{elapsed_str}")
                print(f"  {truncated}")
            elif obj:
                truncated = truncate_text(obj, max_lines, max_width)
                print(f"[{time_str}] RESP {msg_id[:8]}  "
                      f"(object){elapsed_str}")
                print(f"  {truncated}")
            else:
                print(f"[{time_str}] RESP {msg_id[:8]}  "
                      f"(empty){elapsed_str}")


async def async_main(flow, queue_type, max_lines, max_width,
                     pulsar_host, listener_name):

    request_queue = f"non-persistent://tg/request/{queue_type}:{flow}"
    response_queue = f"non-persistent://tg/response/{queue_type}:{flow}"

    print(f"Monitoring prompt queues:")
    print(f"  Request:  {request_queue}")
    print(f"  Response: {response_queue}")
    print(f"Press Ctrl+C to stop\n")

    backend = get_pubsub(
        pulsar_host=pulsar_host,
        pulsar_listener=listener_name,
        pubsub_backend="pulsar",
    )

    central_queue = asyncio.Queue()
    shutdown_event = asyncio.Event()
    subscribers = []

    try:
        for queue_name in [request_queue, response_queue]:
            sub = Subscriber(
                backend=backend,
                topic=queue_name,
                subscription="prompt-monitor",
                consumer_name=f"prompt-monitor-{queue_name}",
                schema=None,
            )
            await sub.start()
            subscribers.append((queue_name, sub))

        tasks = []
        for queue_name, sub in subscribers:
            task = asyncio.create_task(
                monitor_queue(sub, queue_name, central_queue,
                              "prompt-monitor", shutdown_event)
            )
            tasks.append(task)

        processor_task = asyncio.create_task(
            process_messages(central_queue, request_queue, response_queue,
                             max_lines, max_width, shutdown_event)
        )
        tasks.append(processor_task)

        print("Listening...\n")
        await asyncio.gather(*tasks)

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        shutdown_event.set()
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=2.0,
            )
        except asyncio.TimeoutError:
            pass

        for _, sub in subscribers:
            await sub.stop()
        backend.close()


def main():
    parser = argparse.ArgumentParser(
        prog="tg-monitor-prompts",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-f", "--flow",
        default=default_flow,
        help=f"Flow ID (default: {default_flow})",
    )

    parser.add_argument(
        "-q", "--queue-type",
        default=default_queue_type,
        help=f"Queue type: prompt or prompt-rag (default: {default_queue_type})",
    )

    parser.add_argument(
        "-l", "--max-lines",
        type=int,
        default=default_max_lines,
        help=f"Max lines of text to show per term/response (default: {default_max_lines})",
    )

    parser.add_argument(
        "-w", "--max-width",
        type=int,
        default=default_max_width,
        help=f"Max width per line (default: {default_max_width})",
    )

    parser.add_argument(
        "--pulsar-host",
        default="pulsar://localhost:6650",
        help="Pulsar host URL (default: pulsar://localhost:6650)",
    )

    parser.add_argument(
        "--listener-name",
        default="localhost",
        help="Pulsar listener name (default: localhost)",
    )

    args = parser.parse_args()

    try:
        asyncio.run(async_main(
            flow=args.flow,
            queue_type=args.queue_type,
            max_lines=args.max_lines,
            max_width=args.max_width,
            pulsar_host=args.pulsar_host,
            listener_name=args.listener_name,
        ))
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
