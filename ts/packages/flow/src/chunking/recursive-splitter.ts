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

const DEFAULT_SEPARATORS = ["\n\n", "\n", " ", ""];

export function recursiveSplit(
  text: string,
  chunkSize: number,
  chunkOverlap: number,
): string[] {
  return splitRecursive(text, chunkSize, chunkOverlap, DEFAULT_SEPARATORS);
}

function splitRecursive(
  text: string,
  chunkSize: number,
  chunkOverlap: number,
  separators: string[],
): string[] {
  if (text.length <= chunkSize) {
    return text.trim().length > 0 ? [text] : [];
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
  const results: string[] = [];
  for (const chunk of merged) {
    if (chunk.length > chunkSize && remainingSeparators.length > 0) {
      const subChunks = splitRecursive(chunk, chunkSize, chunkOverlap, remainingSeparators);
      results.push(...subChunks);
    } else if (chunk.trim().length > 0) {
      results.push(chunk);
    }
  }

  // Apply overlap
  return applyOverlap(results, chunkOverlap);
}

function mergePieces(
  pieces: string[],
  separator: string,
  chunkSize: number,
): string[] {
  const chunks: string[] = [];
  let current = "";

  for (const piece of pieces) {
    const candidate = current.length > 0 ? current + separator + piece : piece;

    if (candidate.length > chunkSize && current.length > 0) {
      chunks.push(current);
      current = piece;
    } else {
      current = candidate;
    }
  }

  if (current.length > 0) {
    chunks.push(current);
  }

  return chunks;
}

function applyOverlap(chunks: string[], overlapSize: number): string[] {
  if (overlapSize <= 0 || chunks.length <= 1) return chunks;

  const result: string[] = [chunks[0]];

  for (let i = 1; i < chunks.length; i++) {
    const prev = chunks[i - 1];
    const overlapText = prev.slice(Math.max(0, prev.length - overlapSize));
    result.push(overlapText + chunks[i]);
  }

  return result;
}
