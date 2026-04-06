/**
 * Base LLM service — handles message plumbing, subclasses implement the LLM call.
 *
 * Python reference: trustgraph-base/trustgraph/base/llm_service.py
 */

import { FlowProcessor } from "../processor/flow-processor.js";
import { ConsumerSpec } from "../spec/consumer-spec.js";
import { ProducerSpec } from "../spec/producer-spec.js";
import { ParameterSpec } from "../spec/parameter-spec.js";
import type { ProcessorConfig } from "../processor/async-processor.js";
import type { FlowContext } from "../messaging/consumer.js";
import type {
  TextCompletionRequest,
  TextCompletionResponse,
} from "../schema/messages.js";
import type { LlmResult, LlmChunk } from "../schema/primitives.js";

export abstract class LlmService extends FlowProcessor {
  constructor(config: ProcessorConfig) {
    super(config);

    this.registerSpecification(
      new ConsumerSpec<TextCompletionRequest>(
        "request",
        this.onRequest.bind(this),
      ),
    );
    this.registerSpecification(new ProducerSpec<TextCompletionResponse>("response"));
    this.registerSpecification(new ParameterSpec("model"));
    this.registerSpecification(new ParameterSpec("temperature"));
  }

  private async onRequest(
    msg: TextCompletionRequest,
    properties: Record<string, string>,
    flowCtx: FlowContext,
  ): Promise<void> {
    const requestId = properties.id;
    if (!requestId) return;

    const responseProducer = flowCtx.flow.producer<TextCompletionResponse>("response");

    try {
      if (msg.streaming && this.supportsStreaming()) {
        for await (const chunk of this.generateContentStream(
          msg.system,
          msg.prompt,
          msg.model,
          msg.temperature,
        )) {
          await responseProducer.send(requestId, {
            response: chunk.text,
            model: chunk.model,
            inToken: chunk.inToken ?? undefined,
            outToken: chunk.outToken ?? undefined,
            endOfStream: chunk.isFinal,
          });
        }
      } else {
        const result = await this.generateContent(
          msg.system,
          msg.prompt,
          msg.model,
          msg.temperature,
        );

        await responseProducer.send(requestId, {
          response: result.text,
          model: result.model,
          inToken: result.inToken,
          outToken: result.outToken,
          endOfStream: true,
        });
      }
    } catch (err) {
      console.error(`[LlmService] Error processing request:`, err);

      const message = err instanceof Error ? err.message : String(err);
      await responseProducer.send(requestId, {
        response: "",
        error: { type: "llm-error", message },
        endOfStream: true,
      });
    }
  }

  abstract generateContent(
    system: string,
    prompt: string,
    model?: string,
    temperature?: number,
  ): Promise<LlmResult>;

  abstract generateContentStream(
    system: string,
    prompt: string,
    model?: string,
    temperature?: number,
  ): AsyncGenerator<LlmChunk>;

  supportsStreaming(): boolean {
    return false;
  }
}
