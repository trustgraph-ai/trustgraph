import {
  Llm,
  TooManyRequestsError,
  errorMessage,
  makeLlmServiceShape,
  type LlmChunk,
  type LlmProvider,
} from "@trustgraph/base";
import { Config, Effect, Layer, Ref, Result, Stream } from "effect";
import * as O from "effect/Option";
import * as Predicate from "effect/Predicate";
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

export const makeTextCompletionLayer = <E, R>(
  provider: Effect.Effect<LlmProvider, E, R>,
): Layer.Layer<Llm, E, R> =>
  Layer.effect(Llm)(
    provider.pipe(
      Effect.map((resolvedProvider) =>
        Llm.of(makeLlmServiceShape(resolvedProvider))
      ),
    ),
  );

type StreamingTokenTotals = {
  readonly inToken: number;
  readonly outToken: number;
};

type LlmStreamPart = {
  readonly text: O.Option<string>;
  readonly inToken: O.Option<number>;
  readonly outToken: O.Option<number>;
};

const initialTokenTotals = {
  inToken: 0,
  outToken: 0,
} satisfies StreamingTokenTotals;

const updateTokenTotals = (
  current: StreamingTokenTotals,
  part: LlmStreamPart,
): StreamingTokenTotals => ({
  inToken: O.getOrElse(part.inToken, () => current.inToken),
  outToken: O.getOrElse(part.outToken, () => current.outToken),
});

const finalChunk = (model: string, totals: StreamingTokenTotals): LlmChunk => ({
  text: "",
  inToken: totals.inToken,
  outToken: totals.outToken,
  model,
  isFinal: true,
});

const textChunk = (model: string, text: string): LlmChunk => ({
  text,
  inToken: null,
  outToken: null,
  model,
  isFinal: false,
});

const contentPartText = (part: unknown): O.Option<string> =>
  Predicate.isObject(part) &&
    Predicate.hasProperty(part, "text") &&
    Predicate.isString(part.text)
    ? O.some(part.text)
    : O.none();

export const textFromContent = (content: unknown): string => {
  if (Predicate.isString(content)) {
    return content;
  }

  return Array.isArray(content)
    ? content.flatMap((part) => O.toArray(contentPartText(part))).join("")
    : "";
};

export const llmStreamPart = (part: {
  readonly text?: string | null | undefined;
  readonly inToken?: number | null | undefined;
  readonly outToken?: number | null | undefined;
}): LlmStreamPart => ({
  text: O.fromNullishOr(part.text),
  inToken: O.fromNullishOr(part.inToken),
  outToken: O.fromNullishOr(part.outToken),
});

export const streamTextCompletionChunks = <A>(
  iterable: AsyncIterable<A>,
  options: {
    readonly model: string;
    readonly mapError: (error: unknown) => TextCompletionRuntimeError;
    readonly extract: (chunk: A) => LlmStreamPart;
    readonly finalTokens?: Effect.Effect<StreamingTokenTotals, TextCompletionRuntimeError>;
  },
): Stream.Stream<LlmChunk, TextCompletionRuntimeError> =>
  Stream.unwrap(Effect.gen(function* () {
    const totals = yield* Ref.make(initialTokenTotals);

    const chunks = Stream.fromAsyncIterable(iterable, options.mapError).pipe(
      Stream.mapEffect((chunk) =>
        Effect.gen(function* () {
          const part = options.extract(chunk);
          yield* Ref.update(totals, (current) => updateTokenTotals(current, part));
          return O.map(
            O.filter(part.text, (text) => text.length > 0),
            (text) => textChunk(options.model, text),
          );
        })
      ),
      Stream.filterMap((chunk) =>
        O.match(chunk, {
          onNone: () => Result.fail(undefined),
          onSome: Result.succeed,
        })
      ),
    );

    const tokenTotals = options.finalTokens ?? Ref.get(totals);
    return chunks.pipe(
      Stream.concat(Stream.fromEffect(tokenTotals.pipe(
        Effect.map((tokens) => finalChunk(options.model, tokens)),
      ))),
    );
  }));

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
  const status = Predicate.isObject(error) && Predicate.hasProperty(error, "status")
    ? error.status
    : undefined;
  const statusCode = Predicate.isObject(error) && Predicate.hasProperty(error, "statusCode")
    ? error.statusCode
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
    next: (value?: unknown) => iterator.next(value),
    return: (value?: unknown) =>
      iterator.return === undefined
        ? Promise.resolve({ done: true, value })
        : iterator.return(value),
    throw: (error?: unknown) =>
      iterator.throw === undefined
        ? Promise.reject(mapError(error))
        : iterator.throw(error),
    [Symbol.asyncIterator]: () => generator,
  };
  return generator;
};
