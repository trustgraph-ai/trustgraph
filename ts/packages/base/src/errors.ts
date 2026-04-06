/**
 * Custom error types.
 *
 * Python reference: trustgraph-base/trustgraph/exceptions.py
 */

export class TooManyRequestsError extends Error {
  constructor(message = "Rate limit exceeded") {
    super(message);
    this.name = "TooManyRequestsError";
  }
}

export class LlmError extends Error {
  constructor(
    message: string,
    public readonly errorType: string = "llm-error",
  ) {
    super(message);
    this.name = "LlmError";
  }
}

export class ParseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ParseError";
  }
}
