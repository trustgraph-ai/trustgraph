#!/usr/bin/env node

/**
 * Test script for TrustGraph streaming APIs
 * Tests both streaming and non-streaming text completion
 *
 * Usage:
 *   node test-streaming.js
 *
 * Requirements:
 *   - TrustGraph backend running on http://localhost:8088
 *   - Built client library in ./dist/
 */

import { createTrustGraphSocket } from './dist/index.esm.js';

const USER = "test-user";
const SYSTEM_PROMPT = "You are a helpful AI assistant.";
const TEST_PROMPT = "Explain what streaming is in one paragraph.";
const SOCKET_URL = "ws://localhost:8888/api/socket";

console.log("=".repeat(80));
console.log("TrustGraph Streaming API Test");
console.log("=".repeat(80));
console.log(`Connecting to: ${SOCKET_URL}`);
console.log(`User: ${USER}`);
console.log("=".repeat(80));

// Create client connection with explicit WebSocket URL for Node.js
const client = createTrustGraphSocket(USER, undefined, SOCKET_URL);

// Wait a bit for connection to establish
await new Promise(resolve => setTimeout(resolve, 1000));

console.log("\n[1/2] Testing NON-STREAMING text completion...");
console.log("-".repeat(80));

try {
  const flowApi = client.flow("default");
  const response = await flowApi.textCompletion(SYSTEM_PROMPT, TEST_PROMPT);

  console.log("✓ Non-streaming response received:");
  console.log(response);
} catch (error) {
  console.error("✗ Non-streaming failed:", error.message);
}

console.log("\n[2/2] Testing STREAMING text completion...");
console.log("-".repeat(80));

try {
  const flowApi = client.flow("default");

  let accumulated = "";
  let chunkCount = 0;
  const startTime = Date.now();

  await new Promise((resolve, reject) => {
    flowApi.textCompletionStreaming(
      SYSTEM_PROMPT,
      TEST_PROMPT,
      (chunk, complete, metadata) => {
        chunkCount++;
        accumulated += chunk;

        // Show progress indicator
        if (chunk) {
          process.stdout.write(chunk);
        }

        if (complete) {
          const duration = Date.now() - startTime;
          console.log("\n");
          console.log("-".repeat(80));
          console.log(`✓ Streaming complete!`);
          console.log(`  Chunks received: ${chunkCount}`);
          console.log(`  Total length: ${accumulated.length} chars`);
          console.log(`  Duration: ${duration}ms`);
          console.log(`  First chunk: ~${(startTime - Date.now() + duration) / chunkCount}ms`);

          // Display token usage and model info if available
          if (metadata) {
            console.log("\n  Metadata:");
            if (metadata.model) console.log(`    Model: ${metadata.model}`);
            if (metadata.in_token !== undefined) console.log(`    Input tokens: ${metadata.in_token}`);
            if (metadata.out_token !== undefined) console.log(`    Output tokens: ${metadata.out_token}`);
            if (metadata.in_token && metadata.out_token) {
              console.log(`    Total tokens: ${metadata.in_token + metadata.out_token}`);
            }
          }

          resolve();
        }
      },
      (error) => {
        console.error("\n✗ Streaming error:", error);
        reject(new Error(error));
      }
    );
  });
} catch (error) {
  console.error("✗ Streaming failed:", error.message);
}

console.log("\n" + "=".repeat(80));
console.log("Test complete!");
console.log("=".repeat(80));

// Close connection
client.close();
process.exit(0);
