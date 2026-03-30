"""
Monitor prompt request/response queues and log activity with timing.

Subscribes to prompt request and response Pulsar queues, correlates
them by message ID, and logs a summary of each request/response with
elapsed time. Streaming responses are accumulated and shown once at
completion.

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


def summarise_value(value, max_width):
    """Summarise a term value — show type and size for large values."""
    # Try to parse JSON
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        parsed = value

    if isinstance(parsed, list):
        return f"[{len(parsed)} items]"
    elif isinstance(parsed, dict):
        return f"{{{len(parsed)} keys}}"
    elif isinstance(parsed, str):
        if len(parsed) > max_width:
            return parsed[:max_width - 3] + "..."
        return parsed
    else:
        s = str(parsed)
        if len(s) > max_width:
            return s[:max_width - 3] + "..."
        return s


def format_terms(terms, max_lines, max_width):
    """Format prompt terms for display — concise summary."""
    if not terms:
        return ""

    parts = []
    for key, value in terms.items():
        summary = summarise_value(value, max_width - len(key) - 4)
        parts.append(f"  {key}: {summary}")

    return "\n".join(parts)


def parse_raw_message(msg):
    """Parse a raw Pulsar message into (correlation_id, body_dict)."""
    try:
        props = msg.properties()
        corr_id = props.get("id", "")
    except Exception:
        corr_id = ""

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

    # Accumulate streaming responses: corr_id -> list of text chunks
    streaming_chunks = {}

    print("Listening...\n")

    try:
        while True:
            got_message = False

            # Poll request queue
            msg = receive_with_timeout(req_consumer, 100)
            if msg:
                got_message = True
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

            # Poll response queue
            msg = receive_with_timeout(resp_consumer, 100)
            if msg:
                got_message = True
                timestamp = datetime.now()
                corr_id, body = parse_raw_message(msg)
                time_str = timestamp.strftime("%H:%M:%S.%f")[:-3]
                id_display = corr_id[:8] if corr_id else "--------"

                error = body.get("error")
                text = body.get("text", "")
                obj = body.get("object", "")
                eos = body.get("end_of_stream", False)

                if error:
                    # Error — show immediately
                    elapsed_str = ""
                    if corr_id in in_flight:
                        req_timestamp, _ = in_flight.pop(corr_id)
                        elapsed = (timestamp - req_timestamp).total_seconds()
                        elapsed_str = f"  ({elapsed:.3f}s)"
                    streaming_chunks.pop(corr_id, None)

                    err_msg = error
                    if isinstance(error, dict):
                        err_msg = error.get("message", str(error))
                    print(f"[{time_str}] ERR  {id_display}  "
                          f"{err_msg}{elapsed_str}")

                elif eos:
                    # End of stream — show accumulated text + timing
                    elapsed_str = ""
                    if corr_id in in_flight:
                        req_timestamp, _ = in_flight.pop(corr_id)
                        elapsed = (timestamp - req_timestamp).total_seconds()
                        elapsed_str = f"  ({elapsed:.3f}s)"

                    accumulated = streaming_chunks.pop(corr_id, [])
                    if text:
                        accumulated.append(text)

                    full_text = "".join(accumulated)
                    if full_text:
                        truncated = truncate_text(
                            full_text, max_lines, max_width
                        )
                        print(f"[{time_str}] RESP {id_display}"
                              f"{elapsed_str}")
                        print(f"  {truncated}")
                    else:
                        print(f"[{time_str}] RESP {id_display}"
                              f"{elapsed_str}  (empty)")

                elif text or obj:
                    # Streaming chunk or non-streaming response
                    if corr_id in streaming_chunks or (
                        corr_id in in_flight
                    ):
                        # Accumulate streaming chunk
                        if corr_id not in streaming_chunks:
                            streaming_chunks[corr_id] = []
                        streaming_chunks[corr_id].append(text or obj)
                    else:
                        # Non-streaming single response
                        elapsed_str = ""
                        if corr_id in in_flight:
                            req_timestamp, _ = in_flight.pop(corr_id)
                            elapsed = (
                                timestamp - req_timestamp
                            ).total_seconds()
                            elapsed_str = f"  ({elapsed:.3f}s)"

                        content = text or obj
                        label = "" if text else "  (object)"
                        truncated = truncate_text(
                            content, max_lines, max_width
                        )
                        print(f"[{time_str}] RESP {id_display}"
                              f"{label}{elapsed_str}")
                        print(f"  {truncated}")

                resp_consumer.acknowledge(msg)

            if not got_message:
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
