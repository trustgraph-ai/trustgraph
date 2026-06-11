import type {
  LlmChunk,
  LlmResult,
  LlmProvider,
} from "@trustgraph/base";
import {
  Llm,
  TooManyRequestsError,
  errorMessage,
  makeLlmServiceShape,
} from "@trustgraph/base";
import type { Context, } from "effect";
import { Config, Effect, Layer, Match, Ref, Result, Stream } from "effect";
import * as O from "effect/Option";
import * as Predicate from "effect/Predicate";
import * as S from "effect/Schema";
import type * as Scope from "effect/Scope";
import type { LanguageModel, Prompt, Response } from "effect/unstable/ai";
import { AiError, } from "effect/unstable/ai";

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

export class LanguageModelProviderRequest extends S.Class<LanguageModelProviderRequest>("LanguageModelProviderRequest")({
  model: S.String,
  temperature: S.Finite,
}, { description: "Resolved model id and temperature for a language-model call." }) {}

export interface LanguageModelProviderOptions<Requirements> {
  readonly provider: string;
  readonly defaultModel: string;
  readonly defaultTemperature: number;
  readonly context: Context.Context<Requirements>;
  readonly makeLanguageModel: (
    request: LanguageModelProviderRequest,
  ) => Effect.Effect<LanguageModel.Service, TextCompletionRuntimeError, Requirements>;
}

export const makeTextCompletionLayer = <ProviderError, E, R>(
  provider: Effect.Effect<LlmProvider<ProviderError>, E, R>,
): Layer.Layer<Llm, E, Exclude<R, Scope.Scope>> =>
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

const effectAiProviderError = (
  provider: string,
  error: unknown,
): TextCompletionRuntimeError => {
  if (
    AiError.isAiError(error) &&
    (error.reason._tag === "RateLimitError" || error.reason._tag === "QuotaExhaustedError")
  ) {
    return TooManyRequestsError.make({ message: "Rate limit exceeded" });
  }
  return providerRuntimeError(provider, error);
};

const usageInputTokens = (usage: Response.Usage): number =>
  usage.inputTokens.total ?? 0;

const usageOutputTokens = (usage: Response.Usage): number =>
  usage.outputTokens.total ?? 0;

const languageModelPrompt = (
  system: string,
  prompt: string,
): Prompt.RawInput => [
  { role: "system", content: system },
  { role: "user", content: [{ type: "text", text: prompt }] },
];

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

const languageModelResult = (
  response: LanguageModel.GenerateTextResponse<{}>,
  model: string,
): LlmResult => ({
  text: response.text,
  inToken: usageInputTokens(response.usage),
  outToken: usageOutputTokens(response.usage),
  model,
});

const languageModelStreamChunk = (
  provider: string,
  model: string,
  part: Response.StreamPart<{}>,
): Effect.Effect<Result.Result<LlmChunk, undefined>, TextCompletionRuntimeError> =>
  Match.value(part).pipe(
    Match.discriminators("type")({
      "text-delta": (part) => Effect.succeed(
        part.delta.length > 0
          ? Result.succeed(textChunk(model, part.delta))
          : Result.fail(undefined),
      ),
      finish: (part) => Effect.succeed(
        Result.succeed(
          finalChunk(model, {
            inToken: usageInputTokens(part.usage),
            outToken: usageOutputTokens(part.usage),
          }),
        ),
      ),
      error: (part) => Effect.fail(effectAiProviderError(provider, part.error)),
    }),
    Match.orElse(() => Effect.succeed(Result.fail(undefined))),
  );

export const makeLanguageModelProvider = <Requirements>(
  options: LanguageModelProviderOptions<Requirements>,
): LlmProvider<TextCompletionRuntimeError> => ({
  generateContent: (system, prompt, model, temperature) => {
    const modelName = model ?? options.defaultModel;
    const temp = temperature ?? options.defaultTemperature;
    return Effect.gen(function* () {
      const languageModel = yield* options.makeLanguageModel({
        model: modelName,
        temperature: temp,
      });
      const response = yield* languageModel.generateText({
        prompt: languageModelPrompt(system, prompt),
      }).pipe(
        Effect.mapError((error) => effectAiProviderError(options.provider, error)),
      );
      return languageModelResult(response, modelName);
    }).pipe(
      Effect.provideContext(options.context),
    );
  },
  supportsStreaming: () => true,
  generateContentStream: (system, prompt, model, temperature) => {
    const modelName = model ?? options.defaultModel;
    const temp = temperature ?? options.defaultTemperature;
    const stream = Stream.unwrap(
      Effect.gen(function* () {
        const languageModel = yield* options.makeLanguageModel({
          model: modelName,
          temperature: temp,
        });
        return languageModel.streamText({
          prompt: languageModelPrompt(system, prompt),
        }).pipe(
          Stream.mapError((error) => effectAiProviderError(options.provider, error)),
          Stream.filterMapEffect((part) =>
            languageModelStreamChunk(options.provider, modelName, part)
          ),
        );
      }),
    ).pipe(
      Stream.provideContext(options.context),
    );
    return stream;
  },
});
