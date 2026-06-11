import { BunRuntime } from "@effect/platform-bun";
import * as BunFileSystem from "@effect/platform-bun/BunFileSystem";
import { Array as A, Effect, Layer, Order, Path, Schema as S } from "effect";
import * as FileSystem from "effect/FileSystem";
import type { PlatformError } from "effect/PlatformError";
import ts from "typescript";

type Scope = "production" | "non-production";
type Classification = "blocking" | "candidate-effect-exemption" | "non-blocking";

interface ClassFinding {
  readonly file: string;
  readonly line: number;
  readonly column: number;
  readonly name: string;
  readonly scope: Scope;
  readonly classification: Classification;
  readonly reason: string;
  readonly extendsText?: string;
}

const root = process.cwd();
const sourceExtensions = new Set([".ts", ".tsx", ".mts", ".cts"]);
const ignoredDirectories = new Set(["dist", "node_modules", ".turbo"]);
const effectClassPatterns = [
  /\bS\.(Class|TaggedClass|TaggedErrorClass|ErrorClass)\b/,
  /\bSchema\.(Class|TaggedClass|TaggedErrorClass|ErrorClass)\b/,
  /\bData\.TaggedError\b/,
  /\bContext\.Service\b/,
  /\bRpc\.make\b/,
  /\bHttpApi\.make\b/,
  /\bAtomHttpApi\.Service\b/,
  /\bAtomRpc\.Service\b/,
  /\bEffect\.Service\b/,
];

class InventoryFailed extends S.TaggedErrorClass<InventoryFailed>()(
  "InventoryFailed",
  { message: S.String },
) {}

function extensionOf(path: string): string {
  const match = path.match(/\.[cm]?tsx?$/);
  return match?.[0] ?? "";
}

function isSourceFile(path: string): boolean {
  return sourceExtensions.has(extensionOf(path));
}

const walk = Effect.fn("inventory.walk")(function*(
  dir: string,
): Effect.Effect<string[], PlatformError, FileSystem.FileSystem | Path.Path> {
  const fs = yield* FileSystem.FileSystem;
  const platformPath = yield* Path.Path;
  const exists = yield* fs.exists(dir);
  if (!exists) return [];

  const entries = yield* fs.readDirectory(dir);
  const chunks = yield* Effect.all(
    entries.map((entry) =>
      Effect.gen(function*() {
        if (ignoredDirectories.has(entry)) return [];
        const fullPath = platformPath.join(dir, entry);
        const stat = yield* fs.stat(fullPath);
        if (stat.type === "Directory") return yield* walk(fullPath);
        return stat.type === "File" && isSourceFile(fullPath) ? [fullPath] : [];
      })
    ),
    { concurrency: 16 },
  );
  return chunks.flat();
});

function isProductionPackageSource(path: string): boolean {
  const rel = path;
  return (
    rel.startsWith("packages/") &&
    rel.includes("/src/") &&
    !rel.includes("/__tests__/") &&
    !rel.endsWith(".test.ts") &&
    !rel.endsWith(".test.tsx") &&
    !rel.endsWith(".spec.ts") &&
    !rel.endsWith(".spec.tsx")
  );
}

function getClassName(node: ts.ClassLikeDeclarationBase): string {
  return node.name?.getText() ?? "<anonymous>";
}

function getExtendsText(node: ts.ClassLikeDeclarationBase, source: ts.SourceFile): string | undefined {
  const heritage = node.heritageClauses?.find((clause) => clause.token === ts.SyntaxKind.ExtendsKeyword);
  return heritage?.types.map((type) => type.expression.getText(source)).join(", ");
}

function classify(scope: Scope, extendsText?: string): Pick<ClassFinding, "classification" | "reason"> {
  if (scope === "non-production") {
    return {
      classification: "non-blocking",
      reason: "outside production runtime source",
    };
  }

  if (extendsText !== undefined && effectClassPatterns.some((pattern) => pattern.test(extendsText))) {
    return {
      classification: "candidate-effect-exemption",
      reason: "Effect class-shaped API requires proof or functional replacement",
    };
  }

  return {
    classification: "blocking",
    reason: "native class syntax in production runtime source",
  };
}

const inspectFile = Effect.fn("inventory.inspectFile")(function*(
  path: string,
  relativePath: string,
): Effect.Effect<ClassFinding[], PlatformError, FileSystem.FileSystem> {
  const fs = yield* FileSystem.FileSystem;
  const sourceText = yield* fs.readFileString(path);
  const source = ts.createSourceFile(
    path,
    sourceText,
    ts.ScriptTarget.Latest,
    true,
    path.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
  );
  const scope: Scope = isProductionPackageSource(relativePath) ? "production" : "non-production";
  const findings: ClassFinding[] = [];

  function visit(node: ts.Node): void {
    if (ts.isClassDeclaration(node) || ts.isClassExpression(node)) {
      const position = source.getLineAndCharacterOfPosition(node.getStart(source));
      const extendsText = getExtendsText(node, source);
      const { classification, reason } = classify(scope, extendsText);
      findings.push({
        file: relativePath,
        line: position.line + 1,
        column: position.character + 1,
        name: getClassName(node),
        scope,
        classification,
        reason,
        extendsText,
      });
    }

    ts.forEachChild(node, visit);
  }

  visit(source);
  return findings;
});

function printGroup(title: string, group: ClassFinding[]): void {
  console.log(`${title}: ${group.length}`);
  for (const finding of group) {
    const extendsPart = finding.extendsText === undefined ? "" : ` extends ${finding.extendsText}`;
    console.log(
      `  ${finding.file}:${finding.line}:${finding.column} ${finding.name}${extendsPart} - ${finding.reason}`,
    );
  }
}

const program = Effect.fn("inventory.main")(function*() {
  const platformPath = yield* Path.Path;
  const packageFiles = yield* walk(platformPath.join(root, "packages"));
  const scriptFiles = yield* walk(platformPath.join(root, "scripts"));
  const files = A.sort([...packageFiles, ...scriptFiles], Order.String);
  const findings = (yield* Effect.all(
    files.map((file) =>
      inspectFile(file, platformPath.relative(root, file).split(platformPath.sep).join("/"))
    ),
    { concurrency: 16 },
  )).flat();
  const productionFindings = findings.filter((finding) => finding.scope === "production");
  const blocking = productionFindings.filter((finding) => finding.classification === "blocking");
  const candidates = productionFindings.filter((finding) => finding.classification === "candidate-effect-exemption");
  const nonProduction = findings.filter((finding) => finding.scope === "non-production");

  printGroup("Blocking production native classes", blocking);
  printGroup("Candidate Effect class-shaped exemptions", candidates);
  printGroup("Non-production class declarations", nonProduction);

  if (blocking.length > 0) {
    const message = `Found ${blocking.length} blocking production native class declarations.`;
    console.error(`\n${message}`);
    return yield* InventoryFailed.make({ message });
  }

  console.log("\nNo blocking production native class declarations found.");
});

BunRuntime.runMain(
  program().pipe(
    Effect.provide(Layer.merge(BunFileSystem.layer, Path.layer)),
  ),
);
