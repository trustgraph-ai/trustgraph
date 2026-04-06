#!/usr/bin/env node

/**
 * Standalone test for GraphRAG streaming
 * Tests the question "What is a cat?" using GraphRAG streaming mode
 */

import { createTrustGraphSocket } from './dist/index.esm.js';

// Configuration
const USER = 'trustgraph';
const SOCKET_URL = 'ws://localhost:8088/api/v1/socket';
const QUESTION = 'What is a cat?';

console.log('GraphRAG Streaming Test');
console.log('======================');
console.log(`User: ${USER}`);
console.log(`Socket URL: ${SOCKET_URL}`);
console.log(`Question: "${QUESTION}"\n`);

// Create socket connection
const socket = createTrustGraphSocket(USER, undefined, SOCKET_URL);

// Wait for connection to establish
setTimeout(() => {
  console.log('Starting GraphRAG query...\n');

  let accumulated = '';
  let chunkCount = 0;

  // GraphRAG options
  const options = {
    entityLimit: 50,
    tripleLimit: 30,
    maxSubgraphSize: 1000,
    pathLength: 2,
  };

  // Streaming receiver callback
  const onChunk = (chunk, complete, metadata) => {
    chunkCount++;
    accumulated += chunk;

    if (chunk) {
      process.stdout.write(chunk);
    }

    if (complete) {
      console.log('\n\n--- Streaming Complete ---');
      console.log(`Total chunks received: ${chunkCount}`);
      console.log(`Total characters: ${accumulated.length}`);

      if (metadata) {
        console.log('\nMetadata:');
        if (metadata.model) console.log(`  Model: ${metadata.model}`);
        if (metadata.in_token) console.log(`  Input tokens: ${metadata.in_token}`);
        if (metadata.out_token) console.log(`  Output tokens: ${metadata.out_token}`);
      }

      console.log('\n--- Full Response ---');
      console.log(accumulated);

      // Close socket and exit
      socket.close();
      process.exit(0);
    }
  };

  // Error callback
  const onError = (error) => {
    console.error('\n\nERROR:', error);
    socket.close();
    process.exit(1);
  };

  // Execute GraphRAG streaming query
  socket
    .flow('default')
    .graphRagStreaming(
      QUESTION,
      onChunk,
      onError,
      options,
      'default' // collection
    );

}, 1000); // Wait 1 second for connection

// Handle process termination
process.on('SIGINT', () => {
  console.log('\n\nInterrupted. Closing socket...');
  socket.close();
  process.exit(0);
});
