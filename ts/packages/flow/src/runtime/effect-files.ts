import * as BunFileSystem from "@effect/platform-bun/BunFileSystem";
import { Effect, ManagedRuntime } from "effect";
import * as FileSystem from "effect/FileSystem";
import type { PlatformError } from "effect/PlatformError";

const fileSystemRuntime = ManagedRuntime.make(BunFileSystem.layer);

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

export const ensureDirectoryEffect = (path: string): Effect.Effect<void, PlatformError, FileSystem.FileSystem> =>
  Effect.flatMap(FileSystem.FileSystem, (fs) =>
    fs.makeDirectory(path, { recursive: true })
  );

export function ensureDirectory(path: string): Promise<void> {
  return fileSystemRuntime.runPromise(ensureDirectoryEffect(path));
}

export const readTextFileEffect = (path: string): Effect.Effect<string, PlatformError, FileSystem.FileSystem> =>
  Effect.flatMap(FileSystem.FileSystem, (fs) => fs.readFileString(path));

export function readTextFile(path: string): Promise<string> {
  return fileSystemRuntime.runPromise(readTextFileEffect(path));
}

export const readBinaryFileEffect = (path: string): Effect.Effect<Uint8Array, PlatformError, FileSystem.FileSystem> =>
  Effect.flatMap(FileSystem.FileSystem, (fs) => fs.readFile(path));

export function readBinaryFile(path: string): Promise<Uint8Array> {
  return fileSystemRuntime.runPromise(readBinaryFileEffect(path));
}

export const writeTextFileEffect = (
  path: string,
  data: string,
): Effect.Effect<void, PlatformError, FileSystem.FileSystem> =>
  Effect.flatMap(FileSystem.FileSystem, (fs) => fs.writeFileString(path, data));

export function writeTextFile(path: string, data: string): Promise<void> {
  return fileSystemRuntime.runPromise(writeTextFileEffect(path, data));
}

export const writeBinaryFileEffect = (
  path: string,
  data: Uint8Array,
): Effect.Effect<void, PlatformError, FileSystem.FileSystem> =>
  Effect.flatMap(FileSystem.FileSystem, (fs) => fs.writeFile(path, data));

export function writeBinaryFile(path: string, data: Uint8Array): Promise<void> {
  return fileSystemRuntime.runPromise(writeBinaryFileEffect(path, data));
}

export const removePathEffect = (path: string): Effect.Effect<void, PlatformError, FileSystem.FileSystem> =>
  Effect.flatMap(FileSystem.FileSystem, (fs) => fs.remove(path));

export function removePath(path: string): Promise<void> {
  return fileSystemRuntime.runPromise(removePathEffect(path));
}
