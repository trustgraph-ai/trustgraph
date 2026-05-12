/**
 * Mistral text completion service.
 *
 * Env:
 *   MISTRAL_TOKEN (required – Mistral API key)
 *   MISTRAL_MODEL (default: ministral-8b-latest)
 */

import { Mistral } from "@mistralai/mistralai";
import {
  LlmService,
  type ProcessorConfig,
  type LlmResult,
  type LlmChunk,
  tooManyRequestsError,
} from "@trustgraph/base";
import { makeProcessorProgram } from "@trustgraph/base";

export class MistralProcessor extends LlmService {
  private client: Mistral;
  private readonly defaultModel: string;
  private readonly defaultTemperature: number;
  private readonly maxOutput: number;

  constructor(
    config: ProcessorConfig & {
      model?: string;
      apiKey?: string;
      temperature?: number;
      maxOutput?: number;
    },
  ) {
    super(config);

    this.defaultModel =
      config.model ?? process.env.MISTRAL_MODEL ?? "ministral-8b-latest";
    this.defaultTemperature = config.temperature ?? 0.0;
    this.maxOutput = config.maxOutput ?? 4096;

    const apiKey = config.apiKey ?? process.env.MISTRAL_TOKEN;
    if (apiKey === undefined || apiKey.length === 0) {
      throw new Error("Mistral API key not specified");
    }

    this.client = new Mistral({ apiKey });

    console.log("[Mistral] LLM service initialized");
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
      const resp = await this.client.chat.complete({
        model: modelName,
        messages: [
          { role: "system", content: system },
          { role: "user", content: prompt },
        ],
        temperature: temp,
        maxTokens: this.maxOutput,
      });

      return {
        text: (resp.choices?.[0]?.message?.content as string) ?? "",
        inToken: resp.usage?.promptTokens ?? 0,
        outToken: resp.usage?.completionTokens ?? 0,
        model: modelName,
      };
    } catch (err) {
      if ((err as any)?.statusCode === 429 || (err as any)?.status === 429) {
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
      const stream = await this.client.chat.stream({
        model: modelName,
        messages: [
          { role: "system", content: system },
          { role: "user", content: prompt },
        ],
        temperature: temp,
        maxTokens: this.maxOutput,
      });

      let totalInputTokens = 0;
      let totalOutputTokens = 0;

      for await (const chunk of stream) {
        const delta = chunk.data?.choices?.[0]?.delta;
        const content = delta?.content;
        if (typeof content === "string" && content.length > 0) {
          yield {
            text: content,
            inToken: null,
            outToken: null,
            model: modelName,
            isFinal: false,
          };
        }

        if (chunk.data?.usage !== undefined) {
          totalInputTokens = chunk.data.usage.promptTokens ?? 0;
          totalOutputTokens = chunk.data.usage.completionTokens ?? 0;
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
      if ((err as any)?.statusCode === 429 || (err as any)?.status === 429) {
        throw tooManyRequestsError();
      }
      throw err;
    }
  }
}

export const program = makeProcessorProgram({
  id: "text-completion",
  make: (config) => new MistralProcessor(config),
});

export async function run(): Promise<void> {
  await MistralProcessor.launch("text-completion");
}
