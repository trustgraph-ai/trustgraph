import {
  TooManyRequestsError,
  errorMessage,
  type LlmChunk,
} from "@trustgraph/base";
import { Config, Effect } from "effect";
import * as O from "effect/Option";
import * as S from "effect/Schema";

export class TextCompletionConfigError extends S.TaggedErrorClass<TextCompletionConfigError>()(
  "TextCompletionConfigError",
  {
    message: S.String,
    provider: S.String,
    key: S.String,
  },
) {}

export class TextCompletionProviderError extends S.TaggedErrorClass<TextCompletionProviderError>()(
  "TextCompletionProviderError",
  {
    message: S.String,
    provider: S.String,
  },
) {}

export type TextCompletionRuntimeError =
  | TextCompletionProviderError
  | TooManyRequestsError;

export const optionalStringConfig = Effect.fn("TextCompletion.optionalStringConfig")(function*(
  provider: string,
  name: string,
) {
  const value = yield* Config.string(name).pipe(
    Config.option,
    Effect.mapError((cause) =>
      TextCompletionConfigError.make({
        provider,
        key: name,
        message: errorMessage(cause),
      })
    ),
  );
  return O.getOrUndefined(value);
});

export const requiredString = (
  value: string | undefined,
  provider: string,
  key: string,
  message: string,
) =>
  value !== undefined && value.length > 0
    ? Effect.succeed(value)
    : Effect.fail(TextCompletionConfigError.make({ provider, key, message }));

export const providerRuntimeError = (
  provider: string,
  error: unknown,
): TextCompletionRuntimeError =>
  TextCompletionProviderError.make({
    provider,
    message: errorMessage(error),
  });

export const providerStatusError = (
  provider: string,
  error: unknown,
): TextCompletionRuntimeError => {
  const status = typeof error === "object" && error !== null && "status" in error
    ? (error as { readonly status?: unknown }).status
    : undefined;
  const statusCode = typeof error === "object" && error !== null && "statusCode" in error
    ? (error as { readonly statusCode?: unknown }).statusCode
    : undefined;
  return status === 429 || statusCode === 429
    ? TooManyRequestsError.make({ message: "Rate limit exceeded" })
    : providerRuntimeError(provider, error);
};

export const toAsyncGenerator = (
  iterable: AsyncIterable<LlmChunk>,
  mapError: (error: unknown) => TextCompletionRuntimeError,
): AsyncGenerator<LlmChunk> => {
  const iterator = iterable[Symbol.asyncIterator]();
  let generator: AsyncGenerator<LlmChunk>;
  generator = {
    next: (value?: unknown) => iterator.next(value as never),
    return: (value?: unknown) =>
      iterator.return === undefined
        ? Promise.resolve({ done: true, value: value as LlmChunk })
        : iterator.return(value as never) as Promise<IteratorResult<LlmChunk>>,
    throw: (error?: unknown) =>
      iterator.throw === undefined
        ? Effect.runPromise(Effect.fail(mapError(error))) as Promise<IteratorResult<LlmChunk>>
        : iterator.throw(error) as Promise<IteratorResult<LlmChunk>>,
    [Symbol.asyncIterator]: () => generator,
  } as AsyncGenerator<LlmChunk>;
  return generator;
};
