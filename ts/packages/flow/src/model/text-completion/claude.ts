/**
 * Anthropic Claude text completion service.
 *
 * Python reference: trustgraph-flow/trustgraph/model/text_completion/claude/llm.py
 */

import Anthropic from "@anthropic-ai/sdk";
import { LlmService, type ProcessorConfig, type LlmResult, type LlmChunk, TooManyRequestsError } from "@trustgraph/base";

export class ClaudeProcessor extends LlmService {
  private client: Anthropic;
  private defaultModel: string;
  private defaultTemperature: number;
  private maxOutput: number;

  constructor(config: ProcessorConfig & {
    model?: string;
    apiKey?: string;
    temperature?: number;
    maxOutput?: number;
  }) {
    super(config);

    this.defaultModel = config.model ?? "claude-sonnet-4-20250514";
    this.defaultTemperature = config.temperature ?? 0.0;
    this.maxOutput = config.maxOutput ?? 8192;

    const apiKey = config.apiKey ?? process.env.CLAUDE_KEY;
    if (!apiKey) throw new Error("Claude API key not specified");

    this.client = new Anthropic({ apiKey });

    console.log("[Claude] LLM service initialized");
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
      const response = await this.client.messages.create({
        model: modelName,
        max_tokens: this.maxOutput,
        temperature: temp,
        system,
        messages: [
          { role: "user", content: prompt },
        ],
      });

      const text = response.content[0].type === "text"
        ? response.content[0].text
        : "";

      return {
        text,
        inToken: response.usage.input_tokens,
        outToken: response.usage.output_tokens,
        model: modelName,
      };
    } catch (err) {
      if (err instanceof Anthropic.RateLimitError) {
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
      const stream = this.client.messages.stream({
        model: modelName,
        max_tokens: this.maxOutput,
        temperature: temp,
        system,
        messages: [
          { role: "user", content: prompt },
        ],
      });

      for await (const event of stream) {
        if (event.type === "content_block_delta" && event.delta.type === "text_delta") {
          yield {
            text: event.delta.text,
            inToken: null,
            outToken: null,
            model: modelName,
            isFinal: false,
          };
        }
      }

      const finalMessage = await stream.finalMessage();
      yield {
        text: "",
        inToken: finalMessage.usage.input_tokens,
        outToken: finalMessage.usage.output_tokens,
        model: modelName,
        isFinal: true,
      };
    } catch (err) {
      if (err instanceof Anthropic.RateLimitError) {
        throw new TooManyRequestsError();
      }
      throw err;
    }
  }
}

export async function run(): Promise<void> {
  await ClaudeProcessor.launch("text-completion");
}
