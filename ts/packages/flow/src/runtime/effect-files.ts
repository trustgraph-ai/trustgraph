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

export function ensureDirectory(path: string): Promise<void> {
  return Bun.$`mkdir -p ${path}`.quiet().then(() => undefined);
}

export function readTextFile(path: string): Promise<string> {
  return Bun.file(path).text();
}

export function readBinaryFile(path: string): Promise<Uint8Array> {
  return Bun.file(path).arrayBuffer().then((buffer) => new Uint8Array(buffer));
}

export function writeTextFile(path: string, data: string): Promise<void> {
  return Bun.write(path, data).then(() => undefined);
}

export function writeBinaryFile(path: string, data: Uint8Array): Promise<void> {
  return Bun.write(path, data).then(() => undefined);
}

export function removePath(path: string): Promise<void> {
  return Bun.file(path).delete();
}
