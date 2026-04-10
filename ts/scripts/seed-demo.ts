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

import { createClient, Graph } from "falkordb";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const FALKORDB_URL = process.env.FALKORDB_URL ?? "redis://localhost:6380";
const QDRANT_URL = process.env.QDRANT_URL ?? "http://localhost:6333";
const OLLAMA_URL = process.env.OLLAMA_URL ?? "http://localhost:11434";
const GATEWAY_URL = process.env.GATEWAY_URL ?? "http://localhost:8088";
const EMBED_MODEL = process.env.EMBED_MODEL ?? "mxbai-embed-large";

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
  literal("AI Safety", "concerns include", "alignment, misuse, and existential risk");
  literal("AI Safety", "approaches include", "RLHF, Constitutional AI, and interpretability research");
  entity("AI Safety", "advocate includes", "Geoffrey Hinton");

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
  return [...entities].sort();
}

// ---------------------------------------------------------------------------
// Connectivity checks
// ---------------------------------------------------------------------------

async function checkFalkorDB(): Promise<boolean> {
  try {
    const client = createClient({ url: FALKORDB_URL });
    await client.connect();
    await client.ping();
    await client.disconnect();
    return true;
  } catch {
    return false;
  }
}

async function checkQdrant(): Promise<boolean> {
  try {
    const res = await fetch(`${QDRANT_URL}/collections`, { signal: AbortSignal.timeout(3000) });
    return res.ok;
  } catch {
    return false;
  }
}

async function checkOllama(): Promise<boolean> {
  try {
    const res = await fetch(`${OLLAMA_URL}/api/tags`, { signal: AbortSignal.timeout(3000) });
    return res.ok;
  } catch {
    return false;
  }
}

async function checkGateway(): Promise<boolean> {
  try {
    const res = await fetch(`${GATEWAY_URL}/api/v1/metrics`, { signal: AbortSignal.timeout(3000) });
    return res.ok;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// FalkorDB seeding
// ---------------------------------------------------------------------------

async function seedFalkorDB(triples: RawTriple[]): Promise<void> {
  const client = createClient({ url: FALKORDB_URL });
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

async function embed(texts: string[]): Promise<number[][]> {
  const res = await fetch(`${OLLAMA_URL}/api/embed`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model: EMBED_MODEL, input: texts }),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Ollama embed failed (${res.status}): ${body}`);
  }
  const data = (await res.json()) as { embeddings: number[][] };
  return data.embeddings;
}

// ---------------------------------------------------------------------------
// Qdrant seeding (graph embeddings)
// ---------------------------------------------------------------------------

async function seedQdrant(entities: string[]): Promise<void> {
  // Batch embed in groups of 32
  const BATCH_SIZE = 32;
  const allVectors: number[][] = [];

  for (let i = 0; i < entities.length; i += BATCH_SIZE) {
    const batch = entities.slice(i, i + BATCH_SIZE);
    const vecs = await embed(batch);
    allVectors.push(...vecs);
    process.stdout.write(
      `\r  Embedding entities: ${Math.min(i + BATCH_SIZE, entities.length)}/${entities.length}`,
    );
  }
  console.log();

  const dim = allVectors[0].length;
  const collectionName = `t_${USER}_${COLLECTION}_${dim}`;

  // Create collection if needed
  const existsRes = await fetch(`${QDRANT_URL}/collections/${collectionName}`);
  if (!existsRes.ok) {
    await fetch(`${QDRANT_URL}/collections/${collectionName}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        vectors: { size: dim, distance: "Cosine" },
      }),
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

    const res = await fetch(`${QDRANT_URL}/collections/${collectionName}/points`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ points }),
    });

    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Qdrant upsert failed: ${body}`);
    }

    upserted += points.length;
    process.stdout.write(`\r  Upserting to Qdrant: ${upserted}/${entities.length}`);
  }
  console.log();
  console.log(`  Qdrant: ${upserted} entity embeddings stored`);
}

// ---------------------------------------------------------------------------
// Config seeding (via gateway)
// ---------------------------------------------------------------------------

async function seedConfig(): Promise<void> {
  async function pushConfig(keys: string[], values: Record<string, unknown>): Promise<void> {
    const res = await fetch(`${GATEWAY_URL}/api/v1/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ operation: "put", keys, values }),
    });
    const data = (await res.json()) as { error?: { message: string }; version?: number };
    if (data.error) throw new Error(`Config push failed: ${data.error.message}`);
    console.log(`  Config [${keys.join("/")}] → version ${data.version}`);
  }

  await pushConfig(["prompt"], {
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

  await pushConfig(["flows"], {
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
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  console.log("╔══════════════════════════════════════════════════════════╗");
  console.log("║       TrustGraph Demo Seeder — AI Industry KG          ║");
  console.log("╚══════════════════════════════════════════════════════════╝\n");

  // Check services
  const [hasFalkor, hasQdrant, hasOllama, hasGateway] = await Promise.all([
    checkFalkorDB(),
    checkQdrant(),
    checkOllama(),
    checkGateway(),
  ]);

  console.log("Service availability:");
  console.log(`  FalkorDB (${FALKORDB_URL}): ${hasFalkor ? "✓" : "✗"}`);
  console.log(`  Qdrant   (${QDRANT_URL}):   ${hasQdrant ? "✓" : "✗"}`);
  console.log(`  Ollama   (${OLLAMA_URL}):  ${hasOllama ? "✓" : "✗"}`);
  console.log(`  Gateway  (${GATEWAY_URL}):  ${hasGateway ? "✓" : "✗"}`);
  console.log();

  if (!hasFalkor && !hasQdrant && !hasGateway) {
    console.error("No services available. Start the TrustGraph stack first:");
    console.error("  cd ts/deploy && docker compose up -d falkordb qdrant ollama nats");
    process.exit(1);
  }

  const triples = buildTriples();
  const entities = collectEntities(triples);

  console.log(`Built ${triples.length} triples across ${entities.length} unique entities\n`);

  // Seed FalkorDB
  if (hasFalkor) {
    console.log("── Seeding FalkorDB ──");
    await seedFalkorDB(triples);
    console.log();
  } else {
    console.log("⚠ Skipping FalkorDB (not available)\n");
  }

  // Seed Qdrant (requires Ollama for embeddings)
  if (hasQdrant && hasOllama) {
    console.log("── Seeding Qdrant (entity embeddings) ──");
    await seedQdrant(entities);
    console.log();
  } else if (hasQdrant) {
    console.log("⚠ Skipping Qdrant embeddings (Ollama not available for embedding generation)\n");
  } else {
    console.log("⚠ Skipping Qdrant (not available)\n");
  }

  // Seed config via gateway
  if (hasGateway) {
    console.log("── Seeding Config (prompt templates + flows) ──");
    await seedConfig();
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
}

main().catch((err) => {
  console.error("\nSeed failed:", err);
  process.exit(1);
});
