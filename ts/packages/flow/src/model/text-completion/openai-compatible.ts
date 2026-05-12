/**
 * OpenAI-compatible text completion service (generic local server).
 *
 * Works with LM Studio, llama.cpp, vLLM, Ollama OpenAI-compat endpoint, etc.
 *
 * Env:
 *   OPENAI_COMPAT_URL   (required – e.g. http://localhost:1234/v1)
 *   OPENAI_COMPAT_KEY   (default: sk-no-key-required)
 *   OPENAI_COMPAT_MODEL (default: default)
 */

import OpenAI from "openai";
import {
  LlmService,
  type ProcessorConfig,
  type LlmResult,
  type LlmChunk,
} from "@trustgraph/base";
import { makeProcessorProgram } from "@trustgraph/base";

export class OpenAICompatibleProcessor extends LlmService {
  private client: OpenAI;
  private readonly defaultModel: string;
  private readonly defaultTemperature: number;
  private readonly maxOutput: number;

  constructor(
    config: ProcessorConfig & {
      model?: string;
      apiKey?: string;
      baseUrl?: string;
      temperature?: number;
      maxOutput?: number;
    },
  ) {
    super(config);

    this.defaultModel =
      config.model ?? process.env.OPENAI_COMPAT_MODEL ?? "default";
    this.defaultTemperature = config.temperature ?? 0.0;
    this.maxOutput = config.maxOutput ?? 4096;

    const baseURL = config.baseUrl ?? process.env.OPENAI_COMPAT_URL;
    if (baseURL === undefined || baseURL.length === 0) {
      throw new Error(
        "OpenAI-compatible server URL not specified (set OPENAI_COMPAT_URL)",
      );
    }

    const apiKey =
      config.apiKey ?? process.env.OPENAI_COMPAT_KEY ?? "sk-no-key-required";

    this.client = new OpenAI({ baseURL, apiKey });

    console.log("[OpenAI-Compatible] LLM service initialized");
  }

  async generateContent(
    system: string,
    prompt: string,
    model?: string,
    temperature?: number,
  ): Promise<LlmResult> {
    const modelName = model ?? this.defaultModel;
    const temp = temperature ?? this.defaultTemperature;

    const resp = await this.client.chat.completions.create({
      model: modelName,
      messages: [
        { role: "system", content: system },
        { role: "user", content: prompt },
      ],
      temperature: temp,
      max_tokens: this.maxOutput,
    });

    return {
      text: resp.choices[0].message.content ?? "",
      inToken: resp.usage?.prompt_tokens ?? 0,
      outToken: resp.usage?.completion_tokens ?? 0,
      model: modelName,
    };
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

    const stream = await this.client.chat.completions.create({
      model: modelName,
      messages: [
        { role: "system", content: system },
        { role: "user", content: prompt },
      ],
      temperature: temp,
      max_tokens: this.maxOutput,
      stream: true,
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
  }
}

export const program = makeProcessorProgram({
  id: "text-completion",
  make: (config) => new OpenAICompatibleProcessor(config),
});

export async function run(): Promise<void> {
  await OpenAICompatibleProcessor.launch("text-completion");
}
