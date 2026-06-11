/**
 * Seed demo data — populates FalkorDB + Qdrant with a rich AI industry
 * knowledge graph for compelling demos.
 *
 * Seeds directly into the databases (no NATS/pipeline required).
 *
 * Prerequisites:
 *   - FalkorDB running on port 6380 (or FALKORDB_URL)
 *   - Qdrant running on port 6333 (or QDRANT_URL)
 *   - Ollama running on port 11434 (or OLLAMA_URL) with mxbai-embed-large
 *
 * Usage:
 *   pnpm seed:demo                    # seed everything
 *   FALKORDB_URL=redis://localhost:6380 pnpm seed:demo
 *
 * Also seeds config via the gateway if it's running.
 */

import { BunRuntime } from "@effect/platform-bun";
import * as BunHttpClient from "@effect/platform-bun/BunHttpClient";
import { Array as A, Config, Effect, Order, Schema as S } from "effect";
import { HttpClient, HttpClientRequest, HttpClientResponse } from "effect/unstable/http";
import { createClient, Graph } from "falkordb";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const DEFAULT_FALKORDB_URL = "redis://localhost:6380";
const DEFAULT_QDRANT_URL = "http://localhost:6333";
const DEFAULT_OLLAMA_URL = "http://localhost:11434";
const DEFAULT_GATEWAY_URL = "http://localhost:8088";
const DEFAULT_EMBED_MODEL = "mxbai-embed-large";

const USER = "default";
const COLLECTION = "default";
const DATABASE = "falkordb";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RawTriple {
  s: string;
  p: string;
  o: string;
  /** true if object is another entity (Node), false if it's a literal value */
  oIsEntity: boolean;
}

interface DemoConfig {
  readonly falkorDbUrl: string;
  readonly qdrantUrl: string;
  readonly ollamaUrl: string;
  readonly gatewayUrl: string;
  readonly embedModel: string;
}

class SeedDemoError extends S.TaggedErrorClass<SeedDemoError>()(
  "SeedDemoError",
  {
    operation: S.String,
    message: S.String,
  },
) {}

const GatewayErrorBody = S.Struct({
  message: S.optionalKey(S.String),
});

const ConfigPushResponse = S.Struct({
  version: S.optionalKey(S.Number),
  error: S.optionalKey(GatewayErrorBody),
});

const OllamaEmbedResponse = S.Struct({
  embeddings: S.Array(S.Array(S.Number)),
});

const loadConfig = Effect.fn("seed-demo.loadConfig")(function* () {
  return {
    falkorDbUrl: yield* Config.string("FALKORDB_URL").pipe(Config.withDefault(DEFAULT_FALKORDB_URL)),
    qdrantUrl: yield* Config.string("QDRANT_URL").pipe(Config.withDefault(DEFAULT_QDRANT_URL)),
    ollamaUrl: yield* Config.string("OLLAMA_URL").pipe(Config.withDefault(DEFAULT_OLLAMA_URL)),
    gatewayUrl: yield* Config.string("GATEWAY_URL").pipe(Config.withDefault(DEFAULT_GATEWAY_URL)),
    embedModel: yield* Config.string("EMBED_MODEL").pipe(Config.withDefault(DEFAULT_EMBED_MODEL)),
  } satisfies DemoConfig;
});

const scriptError = (operation: string, cause: unknown) =>
  SeedDemoError.make({
    operation,
    message: String(cause),
  });

const stringifyJson = (operation: string, value: unknown) =>
  S.encodeUnknownEffect(S.UnknownFromJsonString)(value).pipe(
    Effect.mapError((cause) => scriptError(operation, cause)),
  );

const decodeJsonText = (operation: string, value: string) =>
  S.decodeUnknownEffect(S.UnknownFromJsonString)(value).pipe(
    Effect.mapError((cause) => scriptError(operation, cause)),
  );

const decodeWith = <A, I, R>(operation: string, schema: S.Codec<A, I, R>) => (value: unknown) =>
  S.decodeUnknownEffect(schema)(value).pipe(
    Effect.mapError((cause) => scriptError(operation, cause)),
  );

const readResponseText = Effect.fn("seed-demo.readResponseText")(function* (
  operation: string,
  response: HttpClientResponse.HttpClientResponse,
) {
  return yield* response.text.pipe(
    Effect.mapError((cause) => scriptError(`${operation}.read-response`, cause)),
  );
});

const executeOkText = Effect.fn("seed-demo.executeOkText")(function* (
  operation: string,
  request: HttpClientRequest.HttpClientRequest,
) {
  const response = yield* HttpClient.execute(request).pipe(
    Effect.flatMap(HttpClientResponse.filterStatusOk),
    Effect.mapError((cause) => scriptError(`${operation}.http`, cause)),
  );
  return yield* readResponseText(operation, response);
});

const postJsonText = Effect.fn("seed-demo.postJsonText")(function* (
  operation: string,
  url: string,
  body: unknown,
) {
  const bodyText = yield* stringifyJson(`${operation}.encode-request`, body);
  const request = HttpClientRequest.post(url, { acceptJson: true }).pipe(
    HttpClientRequest.bodyText(bodyText, "application/json"),
  );
  return yield* executeOkText(operation, request);
});

const putJsonText = Effect.fn("seed-demo.putJsonText")(function* (
  operation: string,
  url: string,
  body: unknown,
) {
  const bodyText = yield* stringifyJson(`${operation}.encode-request`, body);
  const request = HttpClientRequest.put(url, { acceptJson: true }).pipe(
    HttpClientRequest.bodyText(bodyText, "application/json"),
  );
  return yield* executeOkText(operation, request);
});

const httpAvailable = Effect.fn("seed-demo.httpAvailable")(function* (url: string) {
  return yield* HttpClient.get(url).pipe(
    Effect.timeout("3 seconds"),
    Effect.map((response) => response.status >= 200 && response.status < 300),
    Effect.catch(() => Effect.succeed(false)),
  );
});

const resourceExists = Effect.fn("seed-demo.resourceExists")(function* (url: string) {
  return yield* HttpClient.get(url).pipe(
    Effect.map((response) => response.status >= 200 && response.status < 300),
    Effect.catch(() => Effect.succeed(false)),
  );
});

// ---------------------------------------------------------------------------
// Demo Knowledge Graph — AI Industry
// ---------------------------------------------------------------------------

function buildTriples(): RawTriple[] {
  const t: RawTriple[] = [];

  const entity = (s: string, p: string, o: string) =>
    t.push({ s, p, o, oIsEntity: true });
  const literal = (s: string, p: string, o: string) =>
    t.push({ s, p, o, oIsEntity: false });

  // ── Companies ──────────────────────────────────────────────────────────

  literal("OpenAI", "is a", "artificial intelligence research company");
  literal("OpenAI", "was founded in", "2015");
  literal("OpenAI", "is headquartered in", "San Francisco, California");
  entity("OpenAI", "develops", "GPT-4");
  entity("OpenAI", "develops", "GPT-4o");
  entity("OpenAI", "develops", "DALL-E 3");
  entity("OpenAI", "develops", "ChatGPT");
  entity("OpenAI", "was co-founded by", "Sam Altman");
  entity("OpenAI", "was co-founded by", "Elon Musk");
  entity("OpenAI", "was co-founded by", "Ilya Sutskever");
  entity("OpenAI", "received major investment from", "Microsoft");
  entity("OpenAI", "uses technique", "RLHF");
  literal("OpenAI", "mission is", "to ensure AGI benefits all of humanity");

  literal("Anthropic", "is a", "AI safety company");
  literal("Anthropic", "was founded in", "2021");
  literal("Anthropic", "is headquartered in", "San Francisco, California");
  entity("Anthropic", "develops", "Claude 3");
  entity("Anthropic", "develops", "Claude 4");
  entity("Anthropic", "was founded by", "Dario Amodei");
  entity("Anthropic", "was founded by", "Daniela Amodei");
  entity("Anthropic", "uses technique", "Constitutional AI");
  entity("Anthropic", "received investment from", "Google");
  entity("Anthropic", "received investment from", "Amazon");
  literal("Anthropic", "focuses on", "AI safety and alignment research");
  literal("Anthropic", "valuation exceeds", "$60 billion as of 2024");

  literal("Google DeepMind", "is a", "artificial intelligence research laboratory");
  literal("Google DeepMind", "was founded in", "2010");
  literal("Google DeepMind", "is headquartered in", "London, United Kingdom");
  entity("Google DeepMind", "develops", "Gemini");
  entity("Google DeepMind", "develops", "AlphaFold");
  entity("Google DeepMind", "develops", "AlphaGo");
  entity("Google DeepMind", "is led by", "Demis Hassabis");
  entity("Google DeepMind", "is a subsidiary of", "Google");
  literal("Google DeepMind", "pioneered", "reinforcement learning for games and science");
  literal("Google DeepMind", "won", "breakthrough in protein structure prediction");

  literal("Meta AI", "is a", "AI research division of Meta Platforms");
  entity("Meta AI", "is a division of", "Meta Platforms");
  literal("Meta AI", "is headquartered in", "Menlo Park, California");
  entity("Meta AI", "develops", "Llama 3");
  entity("Meta AI", "chief AI scientist is", "Yann LeCun");
  literal("Meta AI", "strategy is", "open-source AI development");
  entity("Meta AI", "open-sourced", "Llama 3");

  literal("NVIDIA", "is a", "semiconductor and AI computing company");
  literal("NVIDIA", "was founded in", "1993");
  literal("NVIDIA", "is headquartered in", "Santa Clara, California");
  entity("NVIDIA", "CEO is", "Jensen Huang");
  entity("NVIDIA", "manufactures", "H100 GPU");
  entity("NVIDIA", "manufactures", "A100 GPU");
  entity("NVIDIA", "manufactures", "B200 GPU");
  entity("NVIDIA", "developed", "CUDA");
  literal("NVIDIA", "dominates", "AI training hardware market with over 80% market share");
  literal("NVIDIA", "market capitalization exceeded", "$3 trillion in 2024");

  literal("Microsoft", "is a", "technology company");
  literal("Microsoft", "was founded in", "1975");
  literal("Microsoft", "is headquartered in", "Redmond, Washington");
  entity("Microsoft", "CEO is", "Satya Nadella");
  entity("Microsoft", "invested $13 billion in", "OpenAI");
  entity("Microsoft", "develops", "Azure AI");
  entity("Microsoft", "develops", "Copilot");
  entity("Microsoft", "integrated GPT-4 into", "Bing");
  literal("Microsoft", "cloud platform is", "Microsoft Azure");

  literal("Mistral AI", "is a", "French artificial intelligence company");
  literal("Mistral AI", "was founded in", "2023");
  literal("Mistral AI", "is headquartered in", "Paris, France");
  entity("Mistral AI", "was founded by", "Arthur Mensch");
  entity("Mistral AI", "develops", "Mixtral");
  entity("Mistral AI", "develops", "Mistral Large");
  entity("Mistral AI", "uses technique", "Mixture of Experts");
  literal("Mistral AI", "strategy is", "open-weight European AI development");

  literal("xAI", "is a", "artificial intelligence company");
  literal("xAI", "was founded in", "2023");
  literal("xAI", "is headquartered in", "Austin, Texas");
  entity("xAI", "was founded by", "Elon Musk");
  entity("xAI", "develops", "Grok");
  literal("xAI", "built", "the largest GPU training cluster called Colossus");

  literal("Stability AI", "is a", "generative AI company");
  literal("Stability AI", "was founded in", "2019");
  literal("Stability AI", "is headquartered in", "London, United Kingdom");
  entity("Stability AI", "develops", "Stable Diffusion");
  entity("Stability AI", "uses technique", "Diffusion Models");
  literal("Stability AI", "focuses on", "open-source image generation");

  literal("Cohere", "is a", "enterprise AI company");
  literal("Cohere", "was founded in", "2019");
  literal("Cohere", "is headquartered in", "Toronto, Canada");
  entity("Cohere", "develops", "Command R+");
  literal("Cohere", "specializes in", "enterprise search and RAG applications");

  // ── People ─────────────────────────────────────────────────────────────

  entity("Sam Altman", "is CEO of", "OpenAI");
  literal("Sam Altman", "previously led", "Y Combinator");
  literal("Sam Altman", "was briefly fired and reinstated as CEO in", "November 2023");

  entity("Dario Amodei", "is CEO of", "Anthropic");
  entity("Dario Amodei", "previously worked at", "OpenAI");
  literal("Dario Amodei", "led", "the AI safety team at OpenAI before founding Anthropic");

  entity("Daniela Amodei", "is President of", "Anthropic");
  entity("Daniela Amodei", "previously worked at", "OpenAI");

  entity("Demis Hassabis", "is CEO of", "Google DeepMind");
  literal("Demis Hassabis", "won", "Nobel Prize in Chemistry 2024 for AlphaFold");
  literal("Demis Hassabis", "background includes", "neuroscience and game design");

  entity("Yann LeCun", "is Chief AI Scientist at", "Meta");
  literal("Yann LeCun", "is known for", "pioneering convolutional neural networks");
  literal("Yann LeCun", "won", "Turing Award in 2018 alongside Hinton and Bengio");
  literal("Yann LeCun", "advocates for", "open-source AI and self-supervised learning");

  entity("Jensen Huang", "is CEO and co-founder of", "NVIDIA");
  literal("Jensen Huang", "co-founded NVIDIA in", "1993");
  literal("Jensen Huang", "is known for", "leather jacket keynotes and GPU computing vision");

  entity("Satya Nadella", "is CEO of", "Microsoft");
  literal("Satya Nadella", "championed", "the strategic partnership with OpenAI");

  entity("Elon Musk", "co-founded", "OpenAI");
  entity("Elon Musk", "founded", "xAI");
  entity("Elon Musk", "is CEO of", "Tesla");
  entity("Elon Musk", "is CEO of", "SpaceX");
  literal("Elon Musk", "departed from", "OpenAI board in 2018");

  entity("Ilya Sutskever", "co-founded", "OpenAI");
  entity("Ilya Sutskever", "founded", "Safe Superintelligence Inc");
  literal("Ilya Sutskever", "is known for", "key contributions to deep learning and sequence-to-sequence models");

  entity("Arthur Mensch", "is CEO of", "Mistral AI");
  entity("Arthur Mensch", "previously worked at", "Google DeepMind");

  entity("Geoffrey Hinton", "is known as", "the Godfather of AI");
  literal("Geoffrey Hinton", "won", "Nobel Prize in Physics 2024 for neural network foundations");
  literal("Geoffrey Hinton", "won", "Turing Award in 2018");
  literal("Geoffrey Hinton", "has warned about", "existential risks from advanced AI");

  // ── AI Models ──────────────────────────────────────────────────────────

  entity("GPT-4", "was developed by", "OpenAI");
  literal("GPT-4", "is a", "large language model");
  literal("GPT-4", "was released in", "March 2023");
  literal("GPT-4", "supports", "text and image input (multimodal)");
  entity("GPT-4", "uses architecture", "Transformer");

  entity("GPT-4o", "was developed by", "OpenAI");
  literal("GPT-4o", "is a", "natively multimodal AI model");
  literal("GPT-4o", "was released in", "May 2024");
  literal("GPT-4o", "supports", "text, image, and audio in a unified model");

  entity("ChatGPT", "is powered by", "GPT-4");
  entity("ChatGPT", "was created by", "OpenAI");
  literal("ChatGPT", "launched in", "November 2022");
  literal("ChatGPT", "reached", "100 million users in 2 months, fastest growing app in history");

  entity("Claude 3", "was developed by", "Anthropic");
  literal("Claude 3", "is a", "large language model family (Haiku, Sonnet, Opus)");
  literal("Claude 3", "was released in", "March 2024");
  entity("Claude 3", "was trained using", "Constitutional AI");

  entity("Claude 4", "was developed by", "Anthropic");
  literal("Claude 4", "is a", "large language model with extended thinking capabilities");
  literal("Claude 4", "was released in", "2025");
  literal("Claude 4", "features", "extended thinking and agentic coding abilities");

  entity("Gemini", "was developed by", "Google DeepMind");
  literal("Gemini", "is a", "natively multimodal AI model");
  literal("Gemini", "was released in", "December 2023");
  literal("Gemini", "supports", "text, image, video, audio, and code");
  literal("Gemini", "comes in variants", "Nano, Flash, Pro, and Ultra");

  entity("AlphaFold", "was developed by", "Google DeepMind");
  literal("AlphaFold", "is a", "protein structure prediction system");
  literal("AlphaFold", "predicted structures for", "over 200 million proteins");
  literal("AlphaFold", "won", "CASP14 competition in 2020");
  literal("AlphaFold", "revolutionized", "structural biology and drug discovery");

  entity("AlphaGo", "was developed by", "Google DeepMind");
  literal("AlphaGo", "is a", "Go-playing AI system");
  literal("AlphaGo", "defeated", "world champion Lee Sedol in 2016");
  literal("AlphaGo", "demonstrated", "superhuman performance in the ancient game of Go");

  entity("Llama 3", "was developed by", "Meta AI");
  literal("Llama 3", "is a", "open-source large language model");
  literal("Llama 3", "was released in", "April 2024");
  literal("Llama 3", "is available in", "8B and 70B parameter versions");
  literal("Llama 3", "license allows", "commercial use with acceptable use policy");

  entity("Mixtral", "was developed by", "Mistral AI");
  literal("Mixtral", "is a", "sparse mixture-of-experts language model");
  entity("Mixtral", "uses architecture", "Mixture of Experts");
  literal("Mixtral", "is licensed as", "open-weight under Apache 2.0");
  literal("Mixtral", "activates", "only 2 of 8 expert networks per token");

  entity("DALL-E 3", "was developed by", "OpenAI");
  literal("DALL-E 3", "is a", "text-to-image generation model");
  entity("DALL-E 3", "uses technique", "Diffusion Models");
  literal("DALL-E 3", "is integrated into", "ChatGPT for image generation");

  entity("Stable Diffusion", "was developed by", "Stability AI");
  literal("Stable Diffusion", "is a", "open-source text-to-image generation model");
  entity("Stable Diffusion", "uses technique", "Diffusion Models");
  literal("Stable Diffusion", "runs on", "consumer GPUs unlike many competitors");

  entity("Grok", "was developed by", "xAI");
  literal("Grok", "is a", "large language model");
  literal("Grok", "has access to", "real-time data from X (formerly Twitter)");

  entity("Command R+", "was developed by", "Cohere");
  literal("Command R+", "is a", "enterprise-focused language model optimized for RAG");
  literal("Command R+", "excels at", "retrieval-augmented generation and tool use");

  entity("Copilot", "was developed by", "Microsoft");
  literal("Copilot", "is a", "AI-powered coding and productivity assistant");
  entity("Copilot", "is powered by", "GPT-4");
  literal("Copilot", "is integrated into", "Windows, Office 365, and GitHub");

  // ── Technologies & Concepts ────────────────────────────────────────────

  literal("Transformer", "was introduced in", "2017 in the paper 'Attention Is All You Need'");
  entity("Transformer", "was invented at", "Google Research");
  literal("Transformer", "is the foundation of", "modern large language models");
  literal("Transformer", "key innovation is", "the self-attention mechanism");
  literal("Transformer", "replaced", "recurrent neural networks for sequence modeling");

  literal("RLHF", "stands for", "Reinforcement Learning from Human Feedback");
  entity("RLHF", "is used by", "OpenAI");
  entity("RLHF", "is used by", "Anthropic");
  literal("RLHF", "purpose is", "aligning AI outputs with human preferences");
  literal("RLHF", "involves", "training a reward model on human preference data");

  entity("Constitutional AI", "was developed by", "Anthropic");
  literal("Constitutional AI", "is a", "AI alignment technique");
  literal("Constitutional AI", "uses", "a set of principles for AI self-critique and revision");
  literal("Constitutional AI", "reduces need for", "human feedback labeling");

  literal("Mixture of Experts", "is a", "neural network architecture pattern");
  entity("Mixture of Experts", "is used by", "Mistral AI");
  literal("Mixture of Experts", "advantage is", "scaling model capacity without proportional compute cost");
  literal("Mixture of Experts", "works by", "routing each input to a subset of specialized sub-networks");

  entity("CUDA", "was developed by", "NVIDIA");
  literal("CUDA", "is a", "parallel computing platform and programming model");
  literal("CUDA", "enables", "GPU-accelerated computing for AI and scientific workloads");
  literal("CUDA", "created a", "dominant ecosystem lock-in for NVIDIA GPUs in AI");

  entity("H100 GPU", "was manufactured by", "NVIDIA");
  literal("H100 GPU", "is a", "data center GPU designed for AI training and inference");
  literal("H100 GPU", "uses", "Hopper architecture with 80 GB HBM3 memory");
  literal("H100 GPU", "costs approximately", "$30,000-$40,000 per unit");
  literal("H100 GPU", "is in", "extremely high demand for AI training clusters");

  entity("A100 GPU", "was manufactured by", "NVIDIA");
  literal("A100 GPU", "is a", "data center GPU for AI and high-performance computing");
  literal("A100 GPU", "uses", "Ampere architecture");

  entity("B200 GPU", "was manufactured by", "NVIDIA");
  literal("B200 GPU", "is a", "next-generation AI GPU using Blackwell architecture");
  literal("B200 GPU", "delivers", "significantly improved AI inference performance");

  literal("Diffusion Models", "are a class of", "generative AI models");
  literal("Diffusion Models", "work by", "learning to reverse a noise-adding process");
  literal("Diffusion Models", "are used for", "image, video, and audio generation");
  entity("Diffusion Models", "are used in", "DALL-E 3");
  entity("Diffusion Models", "are used in", "Stable Diffusion");

  // ── AI Safety & Governance ─────────────────────────────────────────────

  entity("AI Safety", "is a focus area of", "Anthropic");
  entity("AI Safety", "is researched by", "Google DeepMind");
  entity("AI Safety", "is researched by", "OpenAI");
  literal("AI Safety", "concerns include", "alignment, misuse, and existential risk");
  literal("AI Safety", "approaches include", "RLHF, Constitutional AI, interpretability, and red-teaming");
  entity("AI Safety", "advocate includes", "Geoffrey Hinton");
  entity("AI Safety", "advocate includes", "Dario Amodei");
  entity("AI Safety", "advocate includes", "Ilya Sutskever");

  // Anthropic's AI Safety approach (detailed)
  entity("Anthropic", "practices", "AI Safety");
  entity("Anthropic", "developed technique", "Constitutional AI");
  entity("Anthropic", "developed technique", "Interpretability Research");
  entity("Anthropic", "developed technique", "Red Teaming");
  entity("Anthropic", "published", "Responsible Scaling Policy");
  literal("Anthropic", "AI safety approach is", "training AI to be helpful, harmless, and honest through Constitutional AI and RLHF");
  literal("Anthropic", "conducts", "mechanistic interpretability research to understand neural network internals");
  entity("Dario Amodei", "advocates for", "AI Safety");
  literal("Dario Amodei", "approach to AI safety is", "responsible scaling with clear capability thresholds and safety evaluations");
  entity("Daniela Amodei", "advocates for", "AI Safety");
  literal("Daniela Amodei", "focuses on", "building safety-focused organizational culture at Anthropic");

  // OpenAI's AI Safety approach (detailed)
  entity("OpenAI", "practices", "AI Safety");
  entity("OpenAI", "developed technique", "RLHF");
  entity("OpenAI", "developed technique", "Red Teaming");
  entity("OpenAI", "developed technique", "Iterative Deployment");
  entity("OpenAI", "established", "Preparedness Framework");
  literal("OpenAI", "AI safety approach is", "iterative deployment with extensive red-teaming and RLHF alignment");
  literal("OpenAI", "conducts", "external red-team evaluations before major model releases");
  entity("Sam Altman", "advocates for", "AI Safety");
  literal("Sam Altman", "approach to AI safety is", "gradual deployment to learn from real-world feedback while maintaining safety guardrails");
  entity("Ilya Sutskever", "advocated for", "AI Safety");
  literal("Ilya Sutskever", "left OpenAI to found", "Safe Superintelligence Inc focused entirely on safe superintelligence");

  // DeepMind's AI Safety approach
  entity("Google DeepMind", "practices", "AI Safety");
  entity("Google DeepMind", "developed technique", "Scalable Oversight");
  entity("Google DeepMind", "developed technique", "Reward Modeling");
  literal("Google DeepMind", "AI safety approach is", "formal verification, reward modeling, and scalable oversight techniques");
  entity("Demis Hassabis", "advocates for", "AI Safety");
  literal("Demis Hassabis", "approach to AI safety is", "ensuring AI systems are robustly beneficial through scientific rigor");

  // Safety techniques (detailed)
  literal("Constitutional AI", "works by", "having AI critique and revise its own outputs according to a set of constitutional principles");
  literal("Constitutional AI", "advantage is", "reducing reliance on human feedback while maintaining alignment");
  literal("Constitutional AI", "was introduced in", "2022 by Anthropic researchers");

  literal("RLHF", "works by", "collecting human preference data, training a reward model, and optimizing the language model via reinforcement learning");
  literal("RLHF", "limitation is", "scalability of human feedback collection and reward hacking");
  literal("RLHF", "was pioneered by", "OpenAI and used in ChatGPT, InstructGPT");

  literal("Interpretability Research", "is a", "field studying how neural networks represent and process information internally");
  entity("Interpretability Research", "is led by", "Anthropic");
  literal("Interpretability Research", "uses techniques like", "sparse autoencoders, activation patching, and circuit analysis");
  literal("Interpretability Research", "goal is", "understanding AI decision-making to detect and prevent harmful behaviors");

  literal("Red Teaming", "is a", "security practice of adversarially testing AI systems to find vulnerabilities and harmful outputs");
  entity("Red Teaming", "is used by", "OpenAI");
  entity("Red Teaming", "is used by", "Anthropic");
  entity("Red Teaming", "is used by", "Google DeepMind");
  literal("Red Teaming", "involves", "external experts attempting to elicit harmful, biased, or dangerous responses");

  literal("Iterative Deployment", "is a", "strategy of gradually releasing AI systems to learn from real-world use");
  entity("Iterative Deployment", "is practiced by", "OpenAI");
  literal("Iterative Deployment", "advantage is", "building societal understanding and adaptation alongside AI capabilities");

  literal("Scalable Oversight", "is a", "research area focused on maintaining human oversight as AI systems become more capable");
  entity("Scalable Oversight", "is researched by", "Google DeepMind");
  literal("Scalable Oversight", "includes techniques like", "debate, recursive reward modeling, and amplification");

  literal("Responsible Scaling Policy", "is a", "framework published by Anthropic for scaling AI capabilities safely");
  literal("Responsible Scaling Policy", "defines", "AI Safety Levels (ASLs) with capability thresholds and required safeguards");
  entity("Responsible Scaling Policy", "was published by", "Anthropic");

  literal("Preparedness Framework", "is a", "framework published by OpenAI for tracking and mitigating catastrophic risks");
  literal("Preparedness Framework", "evaluates risks in", "cybersecurity, biological threats, persuasion, and model autonomy");
  entity("Preparedness Framework", "was published by", "OpenAI");

  entity("Safe Superintelligence Inc", "was founded by", "Ilya Sutskever");
  literal("Safe Superintelligence Inc", "is a", "company focused solely on building safe superintelligent AI");
  literal("Safe Superintelligence Inc", "was founded in", "2024");
  literal("Safe Superintelligence Inc", "approach is", "pursuing safety and capabilities in tandem, insulated from commercial pressures");

  literal("Artificial General Intelligence", "is defined as", "AI that matches or exceeds human-level intelligence across domains");
  entity("Artificial General Intelligence", "is pursued by", "OpenAI");
  literal("Artificial General Intelligence", "timeline estimates range from", "2027 to never, depending on the researcher");
  literal("Artificial General Intelligence", "is debated as", "both the greatest opportunity and risk of AI development");

  // ── Locations & Ecosystem ──────────────────────────────────────────────

  literal("San Francisco, California", "is home to", "the highest concentration of AI companies globally");
  entity("San Francisco, California", "hosts headquarters of", "OpenAI");
  entity("San Francisco, California", "hosts headquarters of", "Anthropic");

  literal("London, United Kingdom", "is a major hub for", "AI research in Europe");
  entity("London, United Kingdom", "hosts headquarters of", "Google DeepMind");

  literal("Paris, France", "is emerging as", "a European AI powerhouse");
  entity("Paris, France", "hosts headquarters of", "Mistral AI");

  // ── Industry Relationships ─────────────────────────────────────────────

  entity("Google", "is parent company of", "Google DeepMind");
  entity("Google", "invested in", "Anthropic");
  entity("Google Research", "invented", "Transformer");
  literal("Google", "competes with", "Microsoft and OpenAI in AI cloud services");

  entity("Amazon", "invested in", "Anthropic");
  literal("Amazon", "investment in Anthropic totals", "up to $4 billion");
  entity("Amazon", "offers", "Amazon Bedrock");
  literal("Amazon Bedrock", "is a", "managed service for accessing foundation models");

  entity("Meta Platforms", "operates", "Meta AI");
  literal("Meta Platforms", "strategy emphasizes", "open-source AI to counter closed-model competitors");

  entity("Azure AI", "is part of", "Microsoft");
  literal("Azure AI", "provides", "cloud-based AI services including OpenAI model access");

  entity("Tesla", "uses AI for", "autonomous driving (Full Self-Driving)");
  entity("Tesla", "CEO is", "Elon Musk");
  literal("Tesla", "trains AI on", "custom Dojo supercomputer and NVIDIA GPUs");

  entity("SpaceX", "CEO is", "Elon Musk");
  literal("SpaceX", "is a", "space exploration and satellite internet company");

  return t;
}

// ---------------------------------------------------------------------------
// All unique entities (subjects and entity-objects) for embedding
// ---------------------------------------------------------------------------

function collectEntities(triples: RawTriple[]): string[] {
  const entities = new Set<string>();
  for (const t of triples) {
    entities.add(t.s);
    if (t.oIsEntity) {
      entities.add(t.o);
    }
  }
  return A.sort(Array.from(entities), Order.String);
}

// ---------------------------------------------------------------------------
// Connectivity checks
// ---------------------------------------------------------------------------

async function checkFalkorDB(config: DemoConfig): Promise<boolean> {
  try {
    const client = createClient({ url: config.falkorDbUrl });
    await client.connect();
    await client.ping();
    await client.disconnect();
    return true;
  } catch {
    return false;
  }
}

const checkQdrant = (config: DemoConfig) => httpAvailable(`${config.qdrantUrl}/collections`);

const checkOllama = (config: DemoConfig) => httpAvailable(`${config.ollamaUrl}/api/tags`);

const checkGateway = (config: DemoConfig) => httpAvailable(`${config.gatewayUrl}/api/v1/metrics`);

// ---------------------------------------------------------------------------
// FalkorDB seeding
// ---------------------------------------------------------------------------

async function seedFalkorDB(config: DemoConfig, triples: RawTriple[]): Promise<void> {
  const client = createClient({ url: config.falkorDbUrl });
  await client.connect();
  const graph = new Graph(client, DATABASE);

  let nodeCount = 0;
  let literalCount = 0;
  let relCount = 0;

  for (const t of triples) {
    // Create subject node
    await graph.query(
      "MERGE (n:Node {uri: $uri, user: $user, collection: $collection})",
      { params: { uri: t.s, user: USER, collection: COLLECTION } },
    );
    nodeCount++;

    if (t.oIsEntity) {
      // Object is an entity → create Node + Rel→Node
      await graph.query(
        "MERGE (n:Node {uri: $uri, user: $user, collection: $collection})",
        { params: { uri: t.o, user: USER, collection: COLLECTION } },
      );
      nodeCount++;
      await graph.query(
        "MATCH (src:Node {uri: $src, user: $user, collection: $collection}) " +
        "MATCH (dest:Node {uri: $dest, user: $user, collection: $collection}) " +
        "MERGE (src)-[:Rel {uri: $uri, user: $user, collection: $collection}]->(dest)",
        { params: { src: t.s, dest: t.o, uri: t.p, user: USER, collection: COLLECTION } },
      );
    } else {
      // Object is a literal value
      await graph.query(
        "MERGE (n:Literal {value: $value, user: $user, collection: $collection})",
        { params: { value: t.o, user: USER, collection: COLLECTION } },
      );
      literalCount++;
      await graph.query(
        "MATCH (src:Node {uri: $src, user: $user, collection: $collection}) " +
        "MATCH (dest:Literal {value: $dest, user: $user, collection: $collection}) " +
        "MERGE (src)-[:Rel {uri: $uri, user: $user, collection: $collection}]->(dest)",
        { params: { src: t.s, dest: t.o, uri: t.p, user: USER, collection: COLLECTION } },
      );
    }
    relCount++;
  }

  await client.disconnect();
  console.log(
    `  FalkorDB: ${relCount} relationships, ` +
    `${nodeCount} node merges, ${literalCount} literal merges`,
  );
}

// ---------------------------------------------------------------------------
// Ollama embeddings
// ---------------------------------------------------------------------------

const embed = Effect.fn("seed-demo.embed")(function* (config: DemoConfig, texts: string[]) {
  const responseText = yield* postJsonText("ollama.embed", `${config.ollamaUrl}/api/embed`, {
    model: config.embedModel,
    input: texts,
  });
  const data = yield* decodeJsonText("ollama.embed.decode-json", responseText).pipe(
    Effect.flatMap(decodeWith("ollama.embed.decode-response", OllamaEmbedResponse)),
  );
  return data.embeddings;
});

// ---------------------------------------------------------------------------
// Document chunks for Doc RAG
// ---------------------------------------------------------------------------

const DOCUMENT_CHUNKS: Array<{ id: string; content: string }> = [
  {
    id: "chunk-constitutional-ai-1",
    content:
      "Constitutional AI (CAI) is an AI alignment technique developed by Anthropic in 2022. " +
      "It works by having AI systems critique and revise their own outputs according to a set of " +
      "constitutional principles, reducing the need for human feedback labeling. The technique " +
      "uses a two-phase approach: first, the AI generates and self-critiques responses using " +
      "constitutional principles; second, it trains on the revised outputs using reinforcement " +
      "learning from AI feedback (RLAIF) rather than human feedback.",
  },
  {
    id: "chunk-constitutional-ai-2",
    content:
      "The key advantage of Constitutional AI is that it reduces reliance on human feedback while " +
      "maintaining alignment with human values. The constitutional principles can include rules " +
      "about helpfulness, harmlessness, and honesty. Anthropic published the Constitutional AI " +
      "paper to demonstrate that AI systems can be made safer through self-supervision guided " +
      "by explicit principles, rather than requiring massive amounts of human feedback data.",
  },
  {
    id: "chunk-rlhf-1",
    content:
      "Reinforcement Learning from Human Feedback (RLHF) is a technique for training AI models " +
      "to follow human preferences. It was pioneered by OpenAI and used to train models like " +
      "ChatGPT and InstructGPT. The process involves three steps: first, a language model is " +
      "pre-trained on a large corpus; second, human evaluators rank model outputs to create a " +
      "reward model; third, the language model is fine-tuned using reinforcement learning with " +
      "the reward model providing the training signal.",
  },
  {
    id: "chunk-transformer-1",
    content:
      "The Transformer architecture was introduced in the 2017 paper 'Attention Is All You Need' " +
      "by researchers at Google Brain. It revolutionized natural language processing by replacing " +
      "recurrent neural networks with self-attention mechanisms, enabling much more efficient " +
      "parallel processing. Key innovations include multi-head attention, positional encoding, " +
      "and the encoder-decoder structure. The Transformer forms the foundation of modern LLMs " +
      "including GPT, Claude, Gemini, and LLaMA.",
  },
  {
    id: "chunk-openai-1",
    content:
      "OpenAI was founded in December 2015 as a non-profit AI research lab by Sam Altman, " +
      "Elon Musk, Greg Brockman, Ilya Sutskever, Wojciech Zaremba, and John Schulman. " +
      "The organization was created with the mission of ensuring that artificial general " +
      "intelligence benefits all of humanity. In 2019, OpenAI transitioned to a 'capped-profit' " +
      "model to attract the capital needed for large-scale AI research. OpenAI is headquartered " +
      "in San Francisco and is best known for developing the GPT series of language models.",
  },
  {
    id: "chunk-anthropic-1",
    content:
      "Anthropic was founded in 2021 by Dario Amodei and Daniela Amodei, along with several " +
      "former OpenAI researchers. The company focuses on AI safety research and develops the " +
      "Claude family of large language models. Anthropic is headquartered in San Francisco " +
      "and has raised significant funding from investors including Google and Spark Capital. " +
      "The company's research focuses on interpretability, Constitutional AI, and developing " +
      "methods to make AI systems more reliable and aligned with human values.",
  },
  {
    id: "chunk-ai-safety-1",
    content:
      "AI safety encompasses research and practices aimed at ensuring artificial intelligence " +
      "systems operate as intended without causing unintended harm. Key areas include alignment " +
      "(ensuring AI goals match human values), interpretability (understanding how AI makes " +
      "decisions), robustness (maintaining performance under distribution shift), and red " +
      "teaming (adversarial testing to find vulnerabilities). Organizations like Anthropic, " +
      "OpenAI, Google DeepMind, and the Center for AI Safety are major contributors to " +
      "AI safety research.",
  },
  {
    id: "chunk-gpu-ai-1",
    content:
      "NVIDIA's A100 and H100 GPUs are the dominant hardware for AI training and inference. " +
      "The A100, based on the Ampere architecture, delivers up to 312 TFLOPS of FP16 " +
      "performance. The H100, based on the Hopper architecture released in 2022, offers " +
      "roughly 3x the AI training performance of the A100. These GPUs are used by major " +
      "AI labs including OpenAI, Anthropic, Google DeepMind, and Meta AI for training " +
      "large language models and other AI systems.",
  },
  {
    id: "chunk-deepmind-1",
    content:
      "Google DeepMind was formed in April 2023 by merging Google Brain and DeepMind. " +
      "The original DeepMind was founded in 2010 by Demis Hassabis, Shane Legg, and " +
      "Mustafa Suleyman, and was acquired by Google in 2014. Notable achievements include " +
      "AlphaGo (defeating the world Go champion), AlphaFold (predicting protein structures), " +
      "and the Gemini family of multimodal AI models. Demis Hassabis was awarded the 2024 " +
      "Nobel Prize in Chemistry for the AlphaFold work.",
  },
  {
    id: "chunk-llama-1",
    content:
      "LLaMA (Large Language Model Meta AI) is Meta's family of open-source large language " +
      "models. LLaMA 2 was released in July 2023 and made available for both research and " +
      "commercial use. The open-source approach allows researchers and developers to fine-tune " +
      "and deploy the models for their own applications. LLaMA models have been widely adopted " +
      "by the AI community and have spawned numerous derivative models and applications.",
  },
];

// ---------------------------------------------------------------------------
// Qdrant seeding (document embeddings)
// ---------------------------------------------------------------------------

const seedDocumentChunks = Effect.fn("seed-demo.seedDocumentChunks")(function* (config: DemoConfig) {
  // Embed all chunk content
  const BATCH_SIZE = 32;
  const allVectors: number[][] = [];
  const texts = DOCUMENT_CHUNKS.map((c) => c.content);

  for (let i = 0; i < texts.length; i += BATCH_SIZE) {
    const batch = texts.slice(i, i + BATCH_SIZE);
    const vecs = yield* embed(config, batch);
    allVectors.push(...vecs);
    process.stdout.write(
      `\r  Embedding doc chunks: ${Math.min(i + BATCH_SIZE, texts.length)}/${texts.length}`,
    );
  }
  console.log();

  const dim = allVectors[0].length;
  const collectionName = `d_${USER}_${COLLECTION}_${dim}`;

  // Create collection if needed
  const exists = yield* resourceExists(`${config.qdrantUrl}/collections/${collectionName}`);
  if (!exists) {
    yield* putJsonText("qdrant.create-doc-collection", `${config.qdrantUrl}/collections/${collectionName}`, {
      vectors: { size: dim, distance: "Cosine" },
    });
    console.log(`  Created Qdrant collection: ${collectionName} (dim=${dim})`);
  } else {
    console.log(`  Qdrant collection exists: ${collectionName}`);
  }

  // Upsert all chunks with content in payload
  const points = DOCUMENT_CHUNKS.map((chunk, i) => ({
    id: crypto.randomUUID(),
    vector: allVectors[i],
    payload: {
      chunk_id: chunk.id,
      content: chunk.content,
    },
  }));

  yield* putJsonText("qdrant.upsert-doc-points", `${config.qdrantUrl}/collections/${collectionName}/points`, {
    points,
  });

  console.log(`  Qdrant: ${points.length} document chunk embeddings stored in ${collectionName}`);
});

// ---------------------------------------------------------------------------
// Qdrant seeding (graph embeddings)
// ---------------------------------------------------------------------------

const seedQdrant = Effect.fn("seed-demo.seedQdrant")(function* (
  config: DemoConfig,
  entities: string[],
) {
  // Batch embed in groups of 32
  const BATCH_SIZE = 32;
  const allVectors: number[][] = [];

  for (let i = 0; i < entities.length; i += BATCH_SIZE) {
    const batch = entities.slice(i, i + BATCH_SIZE);
    const vecs = yield* embed(config, batch);
    allVectors.push(...vecs);
    process.stdout.write(
      `\r  Embedding entities: ${Math.min(i + BATCH_SIZE, entities.length)}/${entities.length}`,
    );
  }
  console.log();

  const dim = allVectors[0].length;
  const collectionName = `t_${USER}_${COLLECTION}_${dim}`;

  // Create collection if needed
  const exists = yield* resourceExists(`${config.qdrantUrl}/collections/${collectionName}`);
  if (!exists) {
    yield* putJsonText("qdrant.create-entity-collection", `${config.qdrantUrl}/collections/${collectionName}`, {
      vectors: { size: dim, distance: "Cosine" },
    });
    console.log(`  Created Qdrant collection: ${collectionName} (dim=${dim})`);
  } else {
    console.log(`  Qdrant collection exists: ${collectionName}`);
  }

  // Upsert points in batches
  const UPSERT_BATCH = 64;
  let upserted = 0;

  for (let i = 0; i < entities.length; i += UPSERT_BATCH) {
    const points = entities.slice(i, i + UPSERT_BATCH).map((entity, j) => ({
      id: crypto.randomUUID(),
      vector: allVectors[i + j],
      payload: { entity },
    }));

    yield* putJsonText("qdrant.upsert-entity-points", `${config.qdrantUrl}/collections/${collectionName}/points`, {
      points,
    });

    upserted += points.length;
    process.stdout.write(`\r  Upserting to Qdrant: ${upserted}/${entities.length}`);
  }
  console.log();
  console.log(`  Qdrant: ${upserted} entity embeddings stored`);
});

// ---------------------------------------------------------------------------
// Config seeding (via gateway)
// ---------------------------------------------------------------------------

const seedConfig = Effect.fn("seed-demo.seedConfig")(function* (config: DemoConfig) {
  const pushConfig = Effect.fn("seed-demo.seedConfig.pushConfig")(function* (
    keys: ReadonlyArray<string>,
    values: Record<string, unknown>,
  ) {
    const responseText = yield* postJsonText("config.put", `${config.gatewayUrl}/api/v1/config`, {
      operation: "put",
      keys,
      values,
    });
    const data = yield* decodeJsonText("config.put.decode-json", responseText).pipe(
      Effect.flatMap(decodeWith("config.put.decode-response", ConfigPushResponse)),
    );
    if (data.error !== undefined) {
      return yield* SeedDemoError.make({
        operation: "config.put",
        message: data.error.message ?? "unknown gateway error",
      });
    }
    console.log(`  Config [${keys.join("/")}] → version ${data.version ?? "unknown"}`);
  });

  yield* pushConfig(["prompt"], {
    "extract-relationships": {
      system: "You are a helpful assistant that extracts structured knowledge from text.",
      prompt: [
        "Study the following text and derive entity relationships.",
        "For each relationship, derive the subject, predicate and object.",
        "", "Output as a JSON array of objects with keys:",
        "- subject: the subject of the relationship",
        "- predicate: the predicate",
        "- object: the object of the relationship",
        "", "Here is the text:", "{text}",
        "", "Requirements:",
        "- Respond only with a valid JSON array.",
        "- Do not include explanations or markdown formatting.",
      ].join("\n"),
    },
    "extract-definitions": {
      system: "You are a helpful assistant that extracts entity definitions from text.",
      prompt: [
        "Study the following text and derive definitions for any discovered entities.",
        "", "Output as a JSON array of objects with keys:",
        "- entity: the name of the entity",
        "- definition: English text which defines the entity",
        "", "Here is the text:", "{text}",
        "", "Requirements:",
        "- Respond only with a valid JSON array.",
        "- Do not include null or unknown definitions.",
      ].join("\n"),
    },
    "extract-concepts": {
      system: "You extract key concepts and entities from questions.",
      prompt: "Extract the key concepts and entities from the following question.\nReturn one concept per line, no numbering or bullets.\n\nQuestion: {query}",
    },
    "kg-edge-scoring": {
      system: "You are a knowledge graph expert that scores the relevance of graph edges to a query.",
      prompt: [
        "Given the following question and a list of knowledge graph edges,",
        "score each edge for relevance to answering the question.",
        "Return a JSON array of objects with 'id' and 'score' (0.0 to 1.0).",
        "", "Question: {query}", "", "Edges:", "{knowledge}",
        "", "Requirements:", "- Respond only with a valid JSON array.",
      ].join("\n"),
    },
    "graph-rag-synthesize": {
      system: "You are a helpful assistant that answers questions using knowledge graph data. Only use the provided context.",
      prompt: [
        "Use the following knowledge graph relationships to answer the question.",
        "Do not speculate if the answer is not found in the context.",
        "", "Knowledge:", "{context}", "", "Question: {query}",
      ].join("\n"),
    },
    "document-rag-synthesize": {
      system: "You are a helpful assistant. Use only the provided document context to answer questions.",
      prompt: [
        "Use the following document excerpts to answer the question.",
        "Do not speculate if the answer is not found in the context.",
        "", "Documents:", "{context}", "", "Question: {query}",
      ].join("\n"),
    },
    "document-prompt": {
      system: "You are a helpful assistant. Use only the provided context to answer questions.",
      prompt: "Use the following context to answer the question.\n\nContext:\n{documents}\n\nQuestion: {query}",
    },
    "kg-prompt": {
      system: "You are a helpful assistant that answers questions using knowledge graph data.",
      prompt: "Use the following knowledge graph information to answer the question.\n\nKnowledge:\n{knowledge}\n\nQuestion: {query}",
    },
  });

  yield* pushConfig(["flows"], {
    default: {
      topics: {
        "decode-input": "tg.flow.document",
        "decode-output": "tg.flow.text-document",
        "decode-triples": "tg.flow.triples",
        "chunk-input": "tg.flow.text-document",
        "chunk-output": "tg.flow.chunk",
        "chunk-triples": "tg.flow.triples",
        "extract-input": "tg.flow.chunk",
        "extract-triples": "tg.flow.triples",
        "extract-entity-contexts": "tg.flow.entity-contexts",
        "store-triples-input": "tg.flow.triples",
        "store-graph-embeddings-input": "tg.flow.entity-contexts",
        "text-completion-request": "tg.flow.text-completion-request",
        "text-completion-response": "tg.flow.text-completion-response",
        "prompt-request": "tg.flow.prompt-request",
        "prompt-response": "tg.flow.prompt-response",
        "graph-rag-request": "tg.flow.graph-rag-request",
        "graph-rag-response": "tg.flow.graph-rag-response",
        "document-rag-request": "tg.flow.document-rag-request",
        "document-rag-response": "tg.flow.document-rag-response",
        "triples-request": "tg.flow.triples-request",
        "triples-response": "tg.flow.triples-response",
        "agent-request": "tg.flow.agent-request",
        "agent-response": "tg.flow.agent-response",
        "embeddings-request": "tg.flow.embeddings-request",
        "embeddings-response": "tg.flow.embeddings-response",
        "graph-embeddings-request": "tg.flow.graph-embeddings-request",
        "graph-embeddings-response": "tg.flow.graph-embeddings-response",
        "document-embeddings-request": "tg.flow.document-embeddings-request",
        "document-embeddings-response": "tg.flow.document-embeddings-response",
        "librarian-request": "tg.flow.librarian-request",
        "librarian-response": "tg.flow.librarian-response",
      },
    },
  });
});

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

const main = Effect.fn("seed-demo.main")(function* () {
  const config = yield* loadConfig();

  console.log("╔══════════════════════════════════════════════════════════╗");
  console.log("║       TrustGraph Demo Seeder — AI Industry KG          ║");
  console.log("╚══════════════════════════════════════════════════════════╝\n");

  // Check services
  const availability = yield* Effect.all({
    falkor: Effect.tryPromise({
      try: () => checkFalkorDB(config),
      catch: (cause) => scriptError("check-falkordb", cause),
    }).pipe(Effect.catch(() => Effect.succeed(false))),
    qdrant: checkQdrant(config),
    ollama: checkOllama(config),
    gateway: checkGateway(config),
  }, { concurrency: "unbounded" });

  const hasFalkor = availability.falkor;
  const hasQdrant = availability.qdrant;
  const hasOllama = availability.ollama;
  const hasGateway = availability.gateway;

  console.log("Service availability:");
  console.log(`  FalkorDB (${config.falkorDbUrl}): ${hasFalkor ? "✓" : "✗"}`);
  console.log(`  Qdrant   (${config.qdrantUrl}):   ${hasQdrant ? "✓" : "✗"}`);
  console.log(`  Ollama   (${config.ollamaUrl}):  ${hasOllama ? "✓" : "✗"}`);
  console.log(`  Gateway  (${config.gatewayUrl}):  ${hasGateway ? "✓" : "✗"}`);
  console.log();

  if (!hasFalkor && !hasQdrant && !hasGateway) {
    console.error("No services available. Start the TrustGraph stack first:");
    console.error("  cd ts/deploy && docker compose up -d falkordb qdrant ollama nats");
    return yield* SeedDemoError.make({
      operation: "service-check",
      message: "no seed targets available",
    });
  }

  const triples = buildTriples();
  const entities = collectEntities(triples);

  console.log(`Built ${triples.length} triples across ${entities.length} unique entities\n`);

  // Seed FalkorDB
  if (hasFalkor) {
    console.log("── Seeding FalkorDB ──");
    yield* Effect.tryPromise({
      try: () => seedFalkorDB(config, triples),
      catch: (cause) => scriptError("seed-falkordb", cause),
    });
    console.log();
  } else {
    console.log("⚠ Skipping FalkorDB (not available)\n");
  }

  // Seed Qdrant (requires Ollama for embeddings)
  if (hasQdrant && hasOllama) {
    console.log("── Seeding Qdrant (entity embeddings) ──");
    yield* seedQdrant(config, entities);
    console.log();

    console.log("── Seeding Qdrant (document chunk embeddings) ──");
    yield* seedDocumentChunks(config);
    console.log();
  } else if (hasQdrant) {
    console.log("⚠ Skipping Qdrant embeddings (Ollama not available for embedding generation)\n");
  } else {
    console.log("⚠ Skipping Qdrant (not available)\n");
  }

  // Seed config via gateway
  if (hasGateway) {
    console.log("── Seeding Config (prompt templates + flows) ──");
    yield* seedConfig(config);
    console.log();
  } else {
    console.log("⚠ Skipping config (gateway not available — run `pnpm seed` separately)\n");
  }

  // Summary
  console.log("═══════════════════════════════════════════════════════════");
  console.log("  Done! Demo queries to try:");
  console.log();
  console.log("  • Who founded OpenAI?");
  console.log("  • What AI models does Anthropic develop?");
  console.log("  • How are Elon Musk and OpenAI related?");
  console.log("  • What is Constitutional AI?");
  console.log("  • Which companies are headquartered in San Francisco?");
  console.log("  • What GPU does NVIDIA manufacture for AI training?");
  console.log("  • Who won the Nobel Prize related to AI?");
  console.log("  • Compare open-source and closed-source AI models");
  console.log("  • What is the Transformer architecture?");
  console.log("  • Tell me about Demis Hassabis and his achievements");
  console.log("═══════════════════════════════════════════════════════════");
});

BunRuntime.runMain(main().pipe(Effect.provide(BunHttpClient.layer)));
