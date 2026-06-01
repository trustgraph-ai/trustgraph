/**
 * OpenAI text completion service.
 *
 * Python reference: trustgraph-flow/trustgraph/model/text_completion/openai/llm.py
 */

import OpenAI from "openai";
import {
  Llm,
  LlmService,
  makeFlowProcessorProgram,
  makeLlmServiceShape,
  makeLlmSpecs,
  type ProcessorConfig,
  type LlmResult,
  type LlmChunk,
  tooManyRequestsError,
} from "@trustgraph/base";
import { Effect, Layer } from "effect";

export class OpenAIProcessor extends LlmService {
  private client: OpenAI;
  private readonly defaultModel: string;
  private readonly defaultTemperature: number;
  private readonly maxOutput: number;

  constructor(config: ProcessorConfig & {
    model?: string;
    apiKey?: string;
    baseUrl?: string;
    temperature?: number;
    maxOutput?: number;
  }) {
    super(config);

    this.defaultModel = config.model ?? "gpt-4o";
    this.defaultTemperature = config.temperature ?? 0.0;
    this.maxOutput = config.maxOutput ?? 4096;

    const apiKey = config.apiKey ?? process.env.OPENAI_TOKEN;
    if (apiKey === undefined || apiKey.length === 0) {
      throw new Error("OpenAI API key not specified");
    }

    this.client = new OpenAI({
      apiKey,
      baseURL: config.baseUrl ?? process.env.OPENAI_BASE_URL,
    });

    console.log("[OpenAI] LLM service initialized");
  }

  async generateContent(
    system: string,
    prompt: string,
    model?: string,
    temperature?: number,
  ): Promise<LlmResult> {
    const modelName = model ?? this.defaultModel;
    const temp = temperature ?? this.defaultTemperature;

    try {
      const resp = await this.client.chat.completions.create({
        model: modelName,
        messages: [
          { role: "system", content: system },
          { role: "user", content: prompt },
        ],
        temperature: temp,
        max_completion_tokens: this.maxOutput,
      });

      return {
        text: resp.choices[0].message.content ?? "",
        inToken: resp.usage?.prompt_tokens ?? 0,
        outToken: resp.usage?.completion_tokens ?? 0,
        model: modelName,
      };
    } catch (err) {
      if (err instanceof OpenAI.RateLimitError) {
        throw tooManyRequestsError();
      }
      throw err;
    }
  }

  override supportsStreaming(): boolean {
    return true;
  }

  async *generateContentStream(
    system: string,
    prompt: string,
    model?: string,
    temperature?: number,
  ): AsyncGenerator<LlmChunk> {
    const modelName = model ?? this.defaultModel;
    const temp = temperature ?? this.defaultTemperature;

    try {
      const stream = await this.client.chat.completions.create({
        model: modelName,
        messages: [
          { role: "system", content: system },
          { role: "user", content: prompt },
        ],
        temperature: temp,
        max_completion_tokens: this.maxOutput,
        stream: true,
        stream_options: { include_usage: true },
      });

      let totalInputTokens = 0;
      let totalOutputTokens = 0;

      for await (const chunk of stream) {
        const content = chunk.choices[0]?.delta?.content;
        if (content !== null && content !== undefined && content.length > 0) {
          yield {
            text: content,
            inToken: null,
            outToken: null,
            model: modelName,
            isFinal: false,
          };
        }

        if (chunk.usage !== null && chunk.usage !== undefined) {
          totalInputTokens = chunk.usage.prompt_tokens;
          totalOutputTokens = chunk.usage.completion_tokens;
        }
      }

      yield {
        text: "",
        inToken: totalInputTokens,
        outToken: totalOutputTokens,
        model: modelName,
        isFinal: true,
      };
    } catch (err) {
      if (err instanceof OpenAI.RateLimitError) {
        throw tooManyRequestsError();
      }
      throw err;
    }
  }
}

export const program = makeFlowProcessorProgram<ProcessorConfig, never, Llm>({
  id: "text-completion",
  specs: () => makeLlmSpecs(),
  layer: (config) =>
    Layer.succeed(
      Llm,
      Llm.of(makeLlmServiceShape(new OpenAIProcessor(config))),
    ),
});

export async function run(): Promise<void> {
  await Effect.runPromise(program);
}
