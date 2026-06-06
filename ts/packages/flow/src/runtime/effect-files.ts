/** @effect-diagnostics strictEffectProvide:skip-file */

import * as BunFileSystem from "@effect/platform-bun/BunFileSystem";
import { Effect } from "effect";
import * as FileSystem from "effect/FileSystem";
import type { PlatformError } from "effect/PlatformError";

export function joinPath(...segments: string[]): string {
  const joined = segments
    .filter((segment) => segment.length > 0)
    .join("/");

  return joined.replace(/\/+/g, "/");
}

export function dirnamePath(path: string): string {
  const normalized = path.replace(/\/+$/, "");
  const index = normalized.lastIndexOf("/");

  if (index < 0) return ".";
  if (index === 0) return "/";
  return normalized.slice(0, index);
}

const withFileSystem = <A, E>(
  effect: Effect.Effect<A, E, FileSystem.FileSystem>,
): Effect.Effect<A, E> =>
  effect.pipe(Effect.provide(BunFileSystem.layer));

export const ensureDirectoryEffect = (path: string): Effect.Effect<void, PlatformError> =>
  withFileSystem(Effect.flatMap(FileSystem.FileSystem, (fs) =>
    fs.makeDirectory(path, { recursive: true })
  ));

export const readTextFileEffect = (path: string): Effect.Effect<string, PlatformError> =>
  withFileSystem(Effect.flatMap(FileSystem.FileSystem, (fs) => fs.readFileString(path)));

export const readBinaryFileEffect = (path: string): Effect.Effect<Uint8Array, PlatformError> =>
  withFileSystem(Effect.flatMap(FileSystem.FileSystem, (fs) => fs.readFile(path)));

export const writeTextFileEffect = (
  path: string,
  data: string,
): Effect.Effect<void, PlatformError> =>
  withFileSystem(Effect.flatMap(FileSystem.FileSystem, (fs) => fs.writeFileString(path, data)));

export const writeBinaryFileEffect = (
  path: string,
  data: Uint8Array,
): Effect.Effect<void, PlatformError> =>
  withFileSystem(Effect.flatMap(FileSystem.FileSystem, (fs) => fs.writeFile(path, data)));

export const removePathEffect = (path: string): Effect.Effect<void, PlatformError> =>
  withFileSystem(Effect.flatMap(FileSystem.FileSystem, (fs) => fs.remove(path)));
