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
  makeFlowProcessor,
  makeConsumerSpec,
  makeProducerSpec,
  type ProcessorConfig,
  type EffectConfigHandler,
  type FlowContext,
  type FlowProcessorRuntime,
  type FlowResourceNotFoundError,
  type MessagingDeliveryError,
  type PromptRequest,
  type PromptResponse,
  type Spec,
} from "@trustgraph/base";
import { NodeRuntime } from "@effect/platform-node";
import { makeFlowProcessorProgram } from "@trustgraph/base";
import { Effect, Layer, ManagedRuntime } from "effect";
import * as S from "effect/Schema";

export interface PromptTemplate {
  system: string;
  prompt: string;
}

export interface PromptTemplateConfig extends ProcessorConfig {
  configKey?: string;
}

const PromptTemplateEntry = S.Struct({
  system: S.optionalKey(S.String),
  prompt: S.optionalKey(S.String),
});

const PromptTemplateEntries = S.Record(S.String, PromptTemplateEntry);

interface PromptTemplateRuntime {
  readonly specs: ReadonlyArray<Spec<never>>;
  readonly configHandlers: ReadonlyArray<EffectConfigHandler>;
}

const programRuntimes = new WeakMap<PromptTemplateConfig, PromptTemplateRuntime>();

const makePromptTemplateRuntime = (config: PromptTemplateConfig): PromptTemplateRuntime => {
  const templates = new Map<string, PromptTemplate>();
  const configKey = config.configKey ?? "prompt";

  const onPromptConfig = Effect.fn("PromptTemplateService.onConfig")(function* (
    pushedConfig: Record<string, unknown>,
    version: number,
  ) {
    yield* Effect.log(`[PromptTemplate] Loading prompt configuration version ${version}`);

    const promptConfig = pushedConfig[configKey];
    if (promptConfig === undefined) {
      yield* Effect.logWarning(`[PromptTemplate] No key "${configKey}" in config`);
      return;
    }

    const decoded = yield* S.decodeUnknownEffect(PromptTemplateEntries)(promptConfig).pipe(
      Effect.catch((error) =>
        Effect.logError("[PromptTemplate] Failed to decode prompt configuration", {
          error: error.message,
          configKey,
        }).pipe(Effect.as(null)),
      ),
    );
    if (decoded === null) return;

    templates.clear();

    for (const [name, template] of Object.entries(decoded)) {
      templates.set(name, {
        system: template.system ?? "",
        prompt: template.prompt ?? "",
      });
    }

    yield* Effect.log(
      `[PromptTemplate] Loaded ${templates.size} template(s): ${[...templates.keys()].join(", ")}`,
    );
  });

  const onRequest = Effect.fn("PromptTemplateService.onRequest")(function* (
    msg: PromptRequest,
    properties: Record<string, string>,
    flowCtx: FlowContext,
  ) {
    const requestId = properties.id;
    if (requestId === undefined || requestId.length === 0) return;

    const responseProducer = yield* flowCtx.flow.producerEffect<PromptResponse>("prompt-response");
    const template = templates.get(msg.name);
    if (template === undefined) {
      yield* responseProducer.send(requestId, {
        system: "",
        prompt: "",
        error: {
          type: "prompt-error",
          message: `Unknown prompt template: "${msg.name}"`,
        },
      });
      return;
    }

    const variables = msg.variables ?? {};

    yield* responseProducer.send(requestId, {
      system: renderTemplate(template.system, variables),
      prompt: renderTemplate(template.prompt, variables),
    });
  });

  return {
    specs: [
      makeConsumerSpec<PromptRequest, FlowResourceNotFoundError | MessagingDeliveryError>(
        "prompt-request",
        onRequest,
      ),
      makeProducerSpec<PromptResponse>("prompt-response"),
    ],
    configHandlers: [onPromptConfig],
  };
};

const promptTemplateRuntime = (config: PromptTemplateConfig): PromptTemplateRuntime => {
  const existing = programRuntimes.get(config);
  if (existing !== undefined) return existing;
  const runtime = makePromptTemplateRuntime(config);
  programRuntimes.set(config, runtime);
  return runtime;
};

export type PromptTemplateService = FlowProcessorRuntime;

export function makePromptTemplateService(config: PromptTemplateConfig): PromptTemplateService {
  const runtime = makePromptTemplateRuntime(config);
  const service = makeFlowProcessor(config, {
    specifications: runtime.specs,
  });
  for (const handler of runtime.configHandlers) {
    service.registerConfigHandler((pushedConfig, version) =>
      Effect.runPromise(handler(pushedConfig, version)),
    );
  }
  Effect.runSync(Effect.log("[PromptTemplate] Service initialized"));
  return service;
}

export const PromptTemplateService = makePromptTemplateService;

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

export const program = makeFlowProcessorProgram({
  id: "prompt",
  specs: (config: PromptTemplateConfig) => promptTemplateRuntime(config).specs,
  configHandlers: (config: PromptTemplateConfig) => promptTemplateRuntime(config).configHandlers,
});

const promptRuntime = ManagedRuntime.make(Layer.empty);

export function run(): Promise<void> {
  return promptRuntime.runPromise(program);
}

export function runMain(): void {
  NodeRuntime.runMain(program);
}
