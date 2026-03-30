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

import pulsar
from pulsar.schema import BytesSchema


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
        return ""

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


def parse_raw_message(msg):
    """Parse a raw Pulsar message into (correlation_id, body_dict)."""
    # Get correlation ID from properties
    try:
        props = msg.properties()
        corr_id = props.get("id", "")
    except Exception:
        corr_id = ""

    # Parse body
    try:
        value = msg.value()
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        body = json.loads(value) if isinstance(value, str) else {}
    except Exception:
        body = {}

    return corr_id, body


def receive_with_timeout(consumer, timeout_ms=500):
    """Receive a message with timeout, returning None on timeout."""
    try:
        return consumer.receive(timeout_millis=timeout_ms)
    except Exception:
        return None


async def monitor(flow, queue_type, max_lines, max_width,
                  pulsar_host, listener_name):

    request_queue = f"non-persistent://tg/request/{queue_type}:{flow}"
    response_queue = f"non-persistent://tg/response/{queue_type}:{flow}"

    print(f"Monitoring prompt queues:")
    print(f"  Request:  {request_queue}")
    print(f"  Response: {response_queue}")
    print(f"Press Ctrl+C to stop\n")

    client = pulsar.Client(
        pulsar_host,
        listener_name=listener_name,
    )

    req_consumer = client.subscribe(
        request_queue,
        subscription_name="prompt-monitor-req",
        consumer_type=pulsar.ConsumerType.Shared,
        schema=BytesSchema(),
        initial_position=pulsar.InitialPosition.Latest,
    )

    resp_consumer = client.subscribe(
        response_queue,
        subscription_name="prompt-monitor-resp",
        consumer_type=pulsar.ConsumerType.Shared,
        schema=BytesSchema(),
        initial_position=pulsar.InitialPosition.Latest,
    )

    # Track in-flight requests: corr_id -> (timestamp, template_id)
    in_flight = OrderedDict()

    print("Listening...\n")

    try:
        while True:
            # Poll both queues
            msg = receive_with_timeout(req_consumer, 100)
            if msg:
                timestamp = datetime.now()
                corr_id, body = parse_raw_message(msg)
                time_str = timestamp.strftime("%H:%M:%S.%f")[:-3]

                template_id = body.get("id", "(unknown)")
                terms = body.get("terms", {})
                streaming = body.get("streaming", False)

                in_flight[corr_id] = (timestamp, template_id)

                # Limit size
                while len(in_flight) > 1000:
                    in_flight.popitem(last=False)

                stream_flag = " [streaming]" if streaming else ""
                id_display = corr_id[:8] if corr_id else "--------"
                print(f"[{time_str}] REQ  {id_display}  "
                      f"template={template_id}{stream_flag}")

                if terms:
                    print(format_terms(terms, max_lines, max_width))

                req_consumer.acknowledge(msg)

            msg = receive_with_timeout(resp_consumer, 100)
            if msg:
                timestamp = datetime.now()
                corr_id, body = parse_raw_message(msg)
                time_str = timestamp.strftime("%H:%M:%S.%f")[:-3]

                elapsed_str = ""
                if corr_id in in_flight:
                    req_timestamp, template_id = in_flight.pop(corr_id)
                    elapsed = (timestamp - req_timestamp).total_seconds()
                    elapsed_str = f"  ({elapsed:.3f}s)"

                id_display = corr_id[:8] if corr_id else "--------"

                error = body.get("error")
                text = body.get("text", "")
                obj = body.get("object", "")
                eos = body.get("end_of_stream", False)

                if error:
                    err_msg = error
                    if isinstance(error, dict):
                        err_msg = error.get("message", str(error))
                    print(f"[{time_str}] ERR  {id_display}  "
                          f"{err_msg}{elapsed_str}")
                elif eos:
                    print(f"[{time_str}] END  {id_display}"
                          f"{elapsed_str}")
                elif text:
                    truncated = truncate_text(text, max_lines, max_width)
                    print(f"[{time_str}] RESP {id_display}"
                          f"{elapsed_str}")
                    print(f"  {truncated}")
                elif obj:
                    truncated = truncate_text(obj, max_lines, max_width)
                    print(f"[{time_str}] RESP {id_display}  "
                          f"(object){elapsed_str}")
                    print(f"  {truncated}")
                else:
                    print(f"[{time_str}] RESP {id_display}  "
                          f"(empty){elapsed_str}")

                resp_consumer.acknowledge(msg)

            # Small sleep if no messages from either queue
            if not msg:
                await asyncio.sleep(0.05)

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        req_consumer.close()
        resp_consumer.close()
        client.close()


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
        help=f"Max lines of text per term/response (default: {default_max_lines})",
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
        asyncio.run(monitor(
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
