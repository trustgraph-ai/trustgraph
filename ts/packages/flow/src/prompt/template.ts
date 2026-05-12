/**
 * Prompt template service.
 *
 * A FlowProcessor that:
 * 1. Consumes prompt requests (name + variables)
 * 2. Looks up template by name from an in-memory template map (loaded via config)
 * 3. Renders template: replaces {variable} placeholders with values
 * 4. Returns { system, prompt } strings
 *
 * Template config shape (received via config push):
 * {
 *   "prompt": {
 *     "extract-concepts": {
 *       "system": "You are a helpful assistant.",
 *       "prompt": "Extract key concepts from: {query}"
 *     },
 *     "graph-rag-synthesize": {
 *       "system": "You are a knowledge graph assistant.",
 *       "prompt": "Given this context:\n{context}\n\nAnswer: {query}"
 *     }
 *   }
 * }
 *
 * Python reference: trustgraph-flow/trustgraph/prompt/template/service.py
 */

import {
  FlowProcessor,
  ConsumerSpec,
  ProducerSpec,
  type ProcessorConfig,
  type FlowContext,
  type PromptRequest,
  type PromptResponse,
} from "@trustgraph/base";
import { makeProcessorProgram } from "@trustgraph/base";

export interface PromptTemplate {
  system: string;
  prompt: string;
}

export interface PromptTemplateConfig extends ProcessorConfig {
  configKey?: string;
}

export class PromptTemplateService extends FlowProcessor {
  private templates = new Map<string, PromptTemplate>();
  private readonly configKey: string;

  constructor(config: PromptTemplateConfig) {
    super(config);

    this.configKey = config.configKey ?? "prompt";

    this.registerSpecification(
      ConsumerSpec.fromPromise<PromptRequest>(
        "prompt-request",
        this.onRequest.bind(this),
      ),
    );
    this.registerSpecification(new ProducerSpec<PromptResponse>("prompt-response"));

    this.registerConfigHandler(this.onPromptConfig.bind(this));

    console.log("[PromptTemplate] Service initialized");
  }

  private async onPromptConfig(
    config: Record<string, unknown>,
    version: number,
  ): Promise<void> {
    console.log(`[PromptTemplate] Loading prompt configuration version ${version}`);

    const promptConfig = config[this.configKey] as
      | Record<string, { system?: string; prompt?: string }>
      | undefined;

    if (promptConfig === undefined) {
      console.warn(`[PromptTemplate] No key "${this.configKey}" in config`);
      return;
    }

    try {
      this.templates.clear();

      for (const [name, template] of Object.entries(promptConfig)) {
        this.templates.set(name, {
          system: template.system ?? "",
          prompt: template.prompt ?? "",
        });
      }

      console.log(
        `[PromptTemplate] Loaded ${this.templates.size} template(s): ${[...this.templates.keys()].join(", ")}`,
      );
    } catch (err) {
      console.error("[PromptTemplate] Failed to load prompt configuration:", err);
    }
  }

  private async onRequest(
    msg: PromptRequest,
    properties: Record<string, string>,
    flowCtx: FlowContext,
  ): Promise<void> {
    const requestId = properties.id;
    if (requestId === undefined || requestId.length === 0) return;

    const responseProducer = flowCtx.flow.producer<PromptResponse>("prompt-response");

    try {
      const template = this.templates.get(msg.name);
      if (template === undefined) {
        throw new Error(`Unknown prompt template: "${msg.name}"`);
      }

      const variables = msg.variables ?? {};

      const system = renderTemplate(template.system, variables);
      const prompt = renderTemplate(template.prompt, variables);

      await responseProducer.send(requestId, { system, prompt });
    } catch (err) {
      console.error(`[PromptTemplate] Error processing request:`, err);

      const message = err instanceof Error ? err.message : String(err);
      await responseProducer.send(requestId, {
        system: "",
        prompt: "",
        error: { type: "prompt-error", message },
      });
    }
  }
}

/**
 * Simple template rendering: replaces {variable} placeholders with values.
 * Unmatched placeholders are left as-is.
 */
function renderTemplate(
  template: string,
  variables: Record<string, string>,
): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) => {
    if (key in variables) {
      return variables[key];
    }
    return match;
  });
}

export const program = makeProcessorProgram({
  id: "prompt",
  make: (config) => new PromptTemplateService(config),
});

export async function run(): Promise<void> {
  await PromptTemplateService.launch("prompt");
}
