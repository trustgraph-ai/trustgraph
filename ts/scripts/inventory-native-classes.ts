import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";
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
const packagesSrc = join(root, "packages");
const scriptsDir = join(root, "scripts");

const sourceExtensions = new Set([".ts", ".tsx", ".mts", ".cts"]);
const effectClassPatterns = [
  /\bS\.(Class|TaggedClass|TaggedErrorClass|ErrorClass)\b/,
  /\bSchema\.(Class|TaggedClass|TaggedErrorClass|ErrorClass)\b/,
  /\bData\.TaggedError\b/,
  /\bContext\.Service\b/,
  /\bRpc\.make\b/,
  /\bHttpApi\.make\b/,
  /\bEffect\.Service\b/,
];

function extensionOf(path: string): string {
  const match = path.match(/\.[cm]?tsx?$/);
  return match?.[0] ?? "";
}

function isSourceFile(path: string): boolean {
  return sourceExtensions.has(extensionOf(path));
}

function walk(dir: string): string[] {
  if (!existsSync(dir)) {
    return [];
  }

  const files: string[] = [];
  for (const entry of readdirSync(dir)) {
    if (entry === "dist" || entry === "node_modules" || entry === ".turbo") {
      continue;
    }

    const path = join(dir, entry);
    const stat = statSync(path);
    if (stat.isDirectory()) {
      files.push(...walk(path));
    } else if (stat.isFile() && isSourceFile(path)) {
      files.push(path);
    }
  }
  return files;
}

function isProductionPackageSource(path: string): boolean {
  const rel = relative(root, path).split(sep).join("/");
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

function inspectFile(path: string): ClassFinding[] {
  const sourceText = readFileSync(path, "utf8");
  const source = ts.createSourceFile(
    path,
    sourceText,
    ts.ScriptTarget.Latest,
    true,
    path.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
  );
  const scope: Scope = isProductionPackageSource(path) ? "production" : "non-production";
  const findings: ClassFinding[] = [];

  function visit(node: ts.Node): void {
    if (ts.isClassDeclaration(node) || ts.isClassExpression(node)) {
      const position = source.getLineAndCharacterOfPosition(node.getStart(source));
      const extendsText = getExtendsText(node, source);
      const { classification, reason } = classify(scope, extendsText);
      findings.push({
        file: relative(root, path).split(sep).join("/"),
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
}

const files = [...walk(packagesSrc), ...walk(scriptsDir)].sort();
const findings = files.flatMap(inspectFile);
const productionFindings = findings.filter((finding) => finding.scope === "production");
const blocking = productionFindings.filter((finding) => finding.classification === "blocking");
const candidates = productionFindings.filter((finding) => finding.classification === "candidate-effect-exemption");
const nonProduction = findings.filter((finding) => finding.scope === "non-production");

function printGroup(title: string, group: ClassFinding[]): void {
  console.log(`${title}: ${group.length}`);
  for (const finding of group) {
    const extendsPart = finding.extendsText === undefined ? "" : ` extends ${finding.extendsText}`;
    console.log(
      `  ${finding.file}:${finding.line}:${finding.column} ${finding.name}${extendsPart} - ${finding.reason}`,
    );
  }
}

printGroup("Blocking production native classes", blocking);
printGroup("Candidate Effect class-shaped exemptions", candidates);
printGroup("Non-production class declarations", nonProduction);

if (blocking.length > 0) {
  console.error(`\nFound ${blocking.length} blocking production native class declarations.`);
  process.exit(1);
}

console.log("\nNo blocking production native class declarations found.");
