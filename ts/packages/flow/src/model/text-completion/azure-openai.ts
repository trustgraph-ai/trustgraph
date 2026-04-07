/**
 * Azure OpenAI text completion service.
 *
 * Env:
 *   AZURE_TOKEN       (required – Azure OpenAI API key)
 *   AZURE_ENDPOINT    (required – e.g. https://my-resource.openai.azure.com)
 *   AZURE_MODEL       (default: gpt-4o)
 *   AZURE_API_VERSION (default: 2024-12-01-preview)
 */

import { AzureOpenAI } from "openai";
import {
  LlmService,
  type ProcessorConfig,
  type LlmResult,
  type LlmChunk,
  TooManyRequestsError,
} from "@trustgraph/base";

export class AzureOpenAIProcessor extends LlmService {
  private client: AzureOpenAI;
  private readonly defaultModel: string;
  private readonly defaultTemperature: number;
  private readonly maxOutput: number;

  constructor(
    config: ProcessorConfig & {
      model?: string;
      apiKey?: string;
      endpoint?: string;
      apiVersion?: string;
      temperature?: number;
      maxOutput?: number;
    },
  ) {
    super(config);

    this.defaultModel = config.model ?? process.env.AZURE_MODEL ?? "gpt-4o";
    this.defaultTemperature = config.temperature ?? 0.0;
    this.maxOutput = config.maxOutput ?? 4096;

    const apiKey = config.apiKey ?? process.env.AZURE_TOKEN;
    if (!apiKey) throw new Error("Azure OpenAI API key not specified");

    const endpoint = config.endpoint ?? process.env.AZURE_ENDPOINT;
    if (!endpoint) throw new Error("Azure OpenAI endpoint not specified");

    const apiVersion =
      config.apiVersion ??
      process.env.AZURE_API_VERSION ??
      "2024-12-01-preview";

    this.client = new AzureOpenAI({ apiKey, apiVersion, endpoint });

    console.log("[AzureOpenAI] LLM service initialized");
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
      if ((err as any)?.status === 429) {
        throw new TooManyRequestsError();
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
        if (chunk.choices?.[0]?.delta?.content) {
          yield {
            text: chunk.choices[0].delta.content,
            inToken: null,
            outToken: null,
            model: modelName,
            isFinal: false,
          };
        }

        if (chunk.usage) {
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
      if ((err as any)?.status === 429) {
        throw new TooManyRequestsError();
      }
      throw err;
    }
  }
}

export async function run(): Promise<void> {
  await AzureOpenAIProcessor.launch("text-completion");
}
