/**
 * Recursive character text splitter.
 *
 * Matches the behaviour of LangChain's RecursiveCharacterTextSplitter:
 * 1. Try separators in order: "\n\n", "\n", " ", ""
 * 2. Split on the best separator that exists in the text
 * 3. Merge small pieces until they approach chunkSize
 * 4. Recursively split pieces that exceed chunkSize with the next separator
 * 5. Apply overlap: include trailing chunkOverlap chars from the previous chunk
 *
 * Python reference: trustgraph-flow/trustgraph/chunking/recursive_splitter/service.py
 */

import * as Chunk from "effect/Chunk";

const DEFAULT_SEPARATORS: ReadonlyArray<string> = ["\n\n", "\n", " ", ""];

export function recursiveSplit(
  text: string,
  chunkSize: number,
  chunkOverlap: number,
): Chunk.Chunk<string> {
  return splitRecursive(text, chunkSize, chunkOverlap, DEFAULT_SEPARATORS);
}

function splitRecursive(
  text: string,
  chunkSize: number,
  chunkOverlap: number,
  separators: ReadonlyArray<string>,
): Chunk.Chunk<string> {
  if (text.length <= chunkSize) {
    return text.trim().length > 0 ? Chunk.of(text) : Chunk.empty();
  }

  // Find the best separator that exists in the text
  let separator = "";
  let remainingSeparators = separators;

  for (let i = 0; i < separators.length; i++) {
    const sep = separators[i];
    if (sep === "" || text.includes(sep)) {
      separator = sep;
      remainingSeparators = separators.slice(i + 1);
      break;
    }
  }

  // Split on the selected separator
  const pieces = separator === "" ? [...text] : text.split(separator);

  // Merge small pieces into chunks
  const merged = mergePieces(pieces, separator, chunkSize);

  // Recursively split oversized chunks with the next separator
  let results = Chunk.empty<string>();
  for (const chunk of merged) {
    if (chunk.length > chunkSize && remainingSeparators.length > 0) {
      const subChunks = splitRecursive(chunk, chunkSize, chunkOverlap, remainingSeparators);
      results = Chunk.appendAll(results, subChunks);
    } else if (chunk.trim().length > 0) {
      results = Chunk.append(results, chunk);
    }
  }

  // Apply overlap
  return applyOverlap(results, chunkOverlap);
}

function mergePieces(
  pieces: ReadonlyArray<string>,
  separator: string,
  chunkSize: number,
): Chunk.Chunk<string> {
  let chunks = Chunk.empty<string>();
  let current = "";

  for (const piece of pieces) {
    const candidate = current.length > 0 ? current + separator + piece : piece;

    if (candidate.length > chunkSize && current.length > 0) {
      chunks = Chunk.append(chunks, current);
      current = piece;
    } else {
      current = candidate;
    }
  }

  if (current.length > 0) {
    chunks = Chunk.append(chunks, current);
  }

  return chunks;
}

function applyOverlap(chunks: Chunk.Chunk<string>, overlapSize: number): Chunk.Chunk<string> {
  if (overlapSize <= 0 || chunks.length <= 1) return chunks;

  let result = Chunk.empty<string>();
  let previous: string | undefined;

  for (const chunk of chunks) {
    if (previous === undefined) {
      result = Chunk.append(result, chunk);
    } else {
      const overlapText = previous.slice(Math.max(0, previous.length - overlapSize));
      result = Chunk.append(result, overlapText + chunk);
    }
    previous = chunk;
  }

  return result;
}
