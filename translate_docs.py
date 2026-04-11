import argparse
import glob
import json
import math
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import requests


# ----------------------------
# Defaults / configuration
# ----------------------------

DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "translategemma:12b")
DEFAULT_DOCS_DIR = os.getenv("DOCS_DIR", "docs")

# With chunked translation, a smaller ctx is usually faster and more reliable.
DEFAULT_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "4096"))

# Critical: many incomplete translations come from low/default num_predict.
DEFAULT_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "4096"))

DEFAULT_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.1"))
DEFAULT_TOP_P = float(os.getenv("OLLAMA_TOP_P", "0.9"))
DEFAULT_REPEAT_PENALTY = float(os.getenv("OLLAMA_REPEAT_PENALTY", "1.1"))

DEFAULT_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "15m")

DEFAULT_CONNECT_TIMEOUT = int(os.getenv("OLLAMA_CONNECT_TIMEOUT", "30"))
# If Ollama stops streaming mid-response, we want to recover quickly.
# This is a *per-socket-read* timeout (it resets whenever a chunk arrives).
DEFAULT_READ_TIMEOUT = int(os.getenv("OLLAMA_READ_TIMEOUT", "180"))

DEFAULT_MAX_CHUNK_LINES = int(os.getenv("TG_TRANSLATE_MAX_CHUNK_LINES", "200"))
DEFAULT_MAX_CHUNK_CHARS = int(os.getenv("TG_TRANSLATE_MAX_CHUNK_CHARS", "12000"))
DEFAULT_RETRIES = int(os.getenv("TG_TRANSLATE_RETRIES", "2"))

LANGUAGES: Dict[str, str] = {
    "Spanish": "es",
    "Swahili": "sw",
    "Portuguese": "pt",
    "Turkish": "tr",
    "Hindi": "hi",
    "Hebrew": "he",
    "Arabic": "ar",
    "Chinese (simplified)": "zh-cn",
    "Russian": "ru",
}


# ----------------------------
# Markdown splitting helpers
# ----------------------------


@dataclass(frozen=True)
class Block:
    kind: str  # "text" | "code"
    lines: List[str]  # each element includes its original newline (if present)


FENCE_RE = re.compile(r"^[ \t]*(```+|~~~+)")


def _split_line_ending(line: str) -> Tuple[str, str]:
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n"):
        return line[:-1], "\n"
    return line, ""


def split_markdown_blocks(text: str) -> List[Block]:
    lines = text.splitlines(keepends=True)
    if not lines:
        return [Block(kind="text", lines=[])]

    blocks: List[Block] = []

    # YAML front-matter: treat as non-translatable.
    idx = 0
    if lines and lines[0].strip() == "---":
        for j in range(1, len(lines)):
            if lines[j].strip() in {"---", "..."}:
                blocks.append(Block(kind="code", lines=lines[: j + 1]))
                idx = j + 1
                break

    current: List[str] = []
    in_fence = False
    fence_marker: Optional[str] = None
    fence_len = 0

    def flush(kind: str) -> None:
        nonlocal current
        if current:
            blocks.append(Block(kind=kind, lines=current))
            current = []

    for line in lines[idx:]:
        m = FENCE_RE.match(line)
        if m:
            marker = m.group(1)
            if not in_fence:
                flush("text")
                in_fence = True
                fence_marker = marker[0:3]
                fence_len = len(marker)
                current.append(line)
                continue

            # Close if same fence char and len >= opener len
            if fence_marker and marker.startswith(fence_marker) and len(marker) >= fence_len:
                current.append(line)
                flush("code")
                in_fence = False
                fence_marker = None
                fence_len = 0
                continue

        current.append(line)

    flush("code" if in_fence else "text")
    return blocks


def chunk_lines(lines: Sequence[str], *, max_lines: int, max_chars: int) -> List[List[str]]:
    """Split lines into reasonably-sized chunks.

    This prefers breaking at safe Markdown boundaries (blank lines, headings, rules)
    so the model stays focused and is less likely to drift.
    """

    def is_good_break(line: str) -> bool:
        s = line.strip()
        if s == "":
            return True
        if s.startswith("#"):
            return True
        if s in {"---", "***", "___"}:
            return True
        return False

    chunks: List[List[str]] = []
    n = len(lines)
    start = 0

    while start < n:
        end = start
        cur_chars = 0
        last_good_end: Optional[int] = None

        while end < n:
            line_len = len(lines[end])

            # Ensure progress even if a single line exceeds max_chars.
            if end == start and line_len > max_chars:
                end += 1
                last_good_end = end
                break

            if (end - start) >= max_lines:
                break
            if (cur_chars + line_len) > max_chars:
                break

            cur_chars += line_len
            end += 1
            if is_good_break(lines[end - 1]):
                last_good_end = end

        if end >= n:
            chunks.append(list(lines[start:end]))
            break

        cut = last_good_end if (last_good_end is not None and last_good_end > start) else end
        if cut <= start:
            cut = min(start + 1, n)

        chunks.append(list(lines[start:cut]))
        start = cut

    return chunks


# ----------------------------
# Ollama client
# ----------------------------


class OllamaClient:
    def __init__(
        self,
        *,
        url: str,
        model: str,
        num_ctx: int,
        num_predict: int,
        temperature: float,
        top_p: float,
        repeat_penalty: float,
        keep_alive: str,
        timeout: Tuple[int, int] = (DEFAULT_CONNECT_TIMEOUT, DEFAULT_READ_TIMEOUT),
    ) -> None:
        self.url = url
        self.model = model
        self.num_ctx = num_ctx
        self.num_predict = num_predict
        self.temperature = temperature
        self.top_p = top_p
        self.repeat_penalty = repeat_penalty
        self.keep_alive = keep_alive
        self.timeout = timeout
        self.session = requests.Session()

    def reset_session(self) -> None:
        try:
            self.session.close()
        except Exception:
            pass
        self.session = requests.Session()

    def generate(
        self,
        *,
        prompt: str,
        system: Optional[str] = None,
        stop: Optional[List[str]] = None,
        progress_dots: bool = False,
    ) -> str:
        payload: Dict[str, object] = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "keep_alive": self.keep_alive,
            "options": {
                "num_ctx": self.num_ctx,
                "num_predict": self.num_predict,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "repeat_penalty": self.repeat_penalty,
            },
        }
        if system:
            payload["system"] = system
        if stop:
            payload["options"]["stop"] = stop

        out: List[str] = []
        stream_error: Optional[str] = None
        dot_counter = 0

        # Ensure we always release the connection back to the pool.
        with self.session.post(self.url, json=payload, stream=True, timeout=self.timeout) as response:
            response.raise_for_status()

            for raw in response.iter_lines():
                if not raw:
                    continue
                try:
                    chunk = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                if "error" in chunk and chunk["error"]:
                    stream_error = str(chunk["error"])
                    break

                piece = chunk.get("response")
                if piece:
                    out.append(piece)
                    if progress_dots:
                        dot_counter += 1
                        if dot_counter % 50 == 0:
                            sys.stdout.write(".")
                            sys.stdout.flush()
                if chunk.get("done") is True:
                    break

        if stream_error:
            raise requests.exceptions.RequestException(f"Ollama error: {stream_error}")

        result = "".join(out)
        if result == "":
            raise requests.exceptions.RequestException("Empty response from Ollama")
        return result


# ----------------------------
# Translation (validated, line-indexed)
# ----------------------------


INLINE_CODE_RE = re.compile(r"`[^`]*`")
URL_RE = re.compile(r"https?://[^\s)>]+")
# Some models occasionally insert leading whitespace or a colon after the prefix.
PREFIX_RE = re.compile(r"^\s*\[\[(\d+)\]\]\s*[:\-]?\s*(.*)$")


def _protect_spans(text: str) -> Tuple[str, Dict[str, str]]:
    """Protect inline code spans and URLs with placeholders that must be kept verbatim."""
    placeholders: Dict[str, str] = {}

    def repl_code(m: re.Match) -> str:
        key = f"⟦CODE_{len(placeholders)}⟧"
        placeholders[key] = m.group(0)
        return key

    def repl_url(m: re.Match) -> str:
        key = f"⟦URL_{len(placeholders)}⟧"
        placeholders[key] = m.group(0)
        return key

    text = INLINE_CODE_RE.sub(repl_code, text)
    text = URL_RE.sub(repl_url, text)
    return text, placeholders


def _restore_spans(text: str, placeholders: Dict[str, str]) -> str:
    for key, original in placeholders.items():
        text = text.replace(key, original)
    return text


def _build_numbered_input(lines: Sequence[str]) -> Tuple[str, List[Tuple[str, str, str, Dict[str, str]]]]:
    """Return (prompt_text, meta) where meta items are (leading_ws, newline, original_empty_marker, placeholders)."""
    meta: List[Tuple[str, str, str, Dict[str, str]]] = []
    width = max(4, len(str(len(lines))))
    numbered: List[str] = []

    for i, line in enumerate(lines, start=1):
        content, newline = _split_line_ending(line)
        leading_ws = re.match(r"^[\t ]*", content).group(0)
        rest = content[len(leading_ws) :]

        protected, placeholders = _protect_spans(rest)

        prefix = f"[[{i:0{width}d}]]"
        # NOTE: we do NOT send leading whitespace to the model; we reattach it to keep indentation exact.
        numbered.append(f"{prefix} {protected}")
        meta.append((leading_ws, newline, "", placeholders))

    return "\n".join(numbered), meta


def _parse_numbered_output(output: str) -> Dict[int, str]:
    parsed: Dict[int, str] = {}
    for raw_line in output.splitlines():
        m = PREFIX_RE.match(raw_line.strip("\r"))
        if not m:
            continue
        idx = int(m.group(1))
        parsed[idx] = m.group(2)
    return parsed


def _find_missing_indices(parsed: Dict[int, str], expected: int) -> List[int]:
    return [i for i in range(1, expected + 1) if i not in parsed]


def _repair_missing_numbered_lines(
    client: OllamaClient,
    *,
    missing_numbered_lines: Sequence[str],
    target_language_name: str,
    target_language_code: str,
    sentinel: str,
) -> Dict[int, str]:
    """Ask the model to translate only the missing numbered lines."""
    system = (
        "You are a meticulous translation engine. "
        "Never summarize, never omit content, and never add commentary. "
        "Follow the output format exactly."
    )

    prompt = (
        f"Translate ONLY the following missing Markdown lines into {target_language_name} ({target_language_code}).\n"
        "\n"
        "OUTPUT CONTRACT (must follow exactly):\n"
        "- Output ONLY the translated lines for the provided [[NNNN]] prefixes.\n"
        "- Preserve Markdown syntax exactly.\n"
        "- Do NOT translate placeholders like ⟦CODE_0⟧ or ⟦URL_0⟧; keep them exactly unchanged.\n"
        "- Do NOT add any additional lines or prefixes beyond those provided.\n"
        "- Do NOT wrap the output in code fences.\n"
        f"- After the last translated line, output a final line containing exactly: {sentinel}\n"
        "\n"
        "MISSING INPUT LINES:\n"
        + "\n".join(missing_numbered_lines)
        + "\n"
    )

    # Keep CLI output clean: the main generation already shows progress dots.
    raw = client.generate(prompt=prompt, system=system, stop=["\n" + sentinel], progress_dots=False)
    return _parse_numbered_output(raw)


def translate_lines_strict(
    client: OllamaClient,
    *,
    lines: Sequence[str],
    target_language_name: str,
    target_language_code: str,
    retries: int,
) -> Optional[str]:
    """Translate the given lines (including newlines) and return the translated text for this chunk."""
    numbered_input, meta = _build_numbered_input(lines)
    expected = len(lines)
    sentinel = "[[__END_OF_TRANSLATION__]]"

    system = (
        "You are a meticulous translation engine. "
        "Never summarize, never omit content, and never add commentary. "
        "Follow the output format exactly."
    )

    prompt = (
        f"Translate the following Markdown lines into {target_language_name} ({target_language_code}).\n"
        "\n"
        "OUTPUT CONTRACT (must follow exactly):\n"
        "- Translate EVERY line; do not omit, reorder, merge, or split lines.\n"
        "- Preserve Markdown syntax exactly (headings, bullets, tables, links, HTML tags).\n"
        "- Do NOT translate placeholders like ⟦CODE_0⟧ or ⟦URL_0⟧; keep them exactly unchanged.\n"
        "- Return ONLY translated lines, each starting with its original [[NNNN]] prefix.\n"
        "- Do NOT wrap the output in code fences.\n"
        "- Do NOT add blank lines between numbered lines.\n"
        f"- After the last line, output a final line containing exactly: {sentinel}\n"
        "\n"
        "EXAMPLE FORMAT (illustrative):\n"
        "INPUT:\n"
        "[[0001]] Example line\n"
        "[[0002]] Another line\n"
        "OUTPUT:\n"
        "[[0001]] <translated line>\n"
        "[[0002]] <translated line>\n"
        f"{sentinel}\n"
        "\n"
        "INPUT LINES:\n"
        f"{numbered_input}\n"
    )

    last_error: Optional[str] = None
    for attempt in range(retries + 1):
        try:
            sys.stdout.write("      [Generating]")
            sys.stdout.flush()
            raw = client.generate(prompt=prompt, system=system, stop=["\n" + sentinel], progress_dots=True)
            sys.stdout.write(" Done!\n")
        except requests.exceptions.Timeout:
            sys.stdout.write(" Timeout!\n")
            last_error = "timeout"
            client.reset_session()
            continue
        except requests.exceptions.RequestException as e:
            sys.stdout.write(" Failed!\n")
            last_error = str(e)
            client.reset_session()
            continue

        parsed = _parse_numbered_output(raw)
        # Ignore harmless extra indices if the model repeats itself.
        parsed = {i: v for i, v in parsed.items() if 1 <= i <= expected}

        missing = _find_missing_indices(parsed, expected)
        if missing:
            # Fast path: repair only a small number of missing lines.
            # This avoids re-translating large chunks when we only missed a couple of prefixes.
            if len(missing) <= min(12, max(3, expected // 10)):
                numbered_lines = numbered_input.splitlines()
                if len(numbered_lines) == expected:
                    missing_input = [numbered_lines[i - 1] for i in missing]
                    try:
                        repaired = _repair_missing_numbered_lines(
                            client,
                            missing_numbered_lines=missing_input,
                            target_language_name=target_language_name,
                            target_language_code=target_language_code,
                            sentinel=sentinel,
                        )
                        repaired = {i: v for i, v in repaired.items() if i in missing}
                        parsed.update(repaired)
                        missing = _find_missing_indices(parsed, expected)
                    except requests.exceptions.Timeout:
                        client.reset_session()
                    except requests.exceptions.RequestException:
                        client.reset_session()

            if missing:
                last_error = f"missing lines ({expected - len(missing)}/{expected})"
                # Let the caller split smaller rather than retrying the same large prompt.
                break

        # Validate that protected placeholders were preserved.
        placeholder_missing = 0
        for i in range(1, expected + 1):
            _leading_ws, _newline, _unused, placeholders = meta[i - 1]
            if not placeholders:
                continue
            out_line = parsed.get(i, "")
            for key in placeholders.keys():
                if key not in out_line:
                    placeholder_missing += 1
        if placeholder_missing:
            last_error = f"placeholder lost ({placeholder_missing})"
            break

        # Reconstruct chunk, preserving indentation + original newlines.
        out_lines: List[str] = []
        for i in range(1, expected + 1):
            leading_ws, newline, _unused, placeholders = meta[i - 1]
            translated_rest = parsed[i]
            translated_rest = _restore_spans(translated_rest, placeholders)
            out_lines.append(leading_ws + translated_rest + newline)

        return "".join(out_lines)

    print(f"      [!] Chunk translation failed after retries: {last_error}")
    return None


def _is_good_split_boundary(line: str) -> bool:
    s = line.strip()
    if s == "":
        return True
    if s.startswith("#"):
        return True
    if s in {"---", "***", "___"}:
        return True
    return False


def _find_best_split_index(lines: Sequence[str]) -> int:
    """Pick a split point near the middle, preferably after a safe Markdown boundary."""
    n = len(lines)
    if n <= 1:
        return 1

    mid = n // 2
    candidates: List[int] = []
    for i in range(1, n):
        if _is_good_split_boundary(lines[i - 1]):
            candidates.append(i)
    if not candidates:
        return mid

    return min(candidates, key=lambda i: abs(i - mid))


def translate_single_line_fallback(
    client: OllamaClient,
    *,
    line: str,
    target_language_name: str,
    target_language_code: str,
    retries: int,
) -> Optional[str]:
    """Last-resort translation for one line when the numbered contract keeps failing."""
    content, newline = _split_line_ending(line)
    leading_ws = re.match(r"^[\t ]*", content).group(0)
    rest = content[len(leading_ws) :]

    # Empty/whitespace lines: keep as-is.
    if rest.strip() == "":
        return line

    protected, placeholders = _protect_spans(rest)

    system = (
        "You are a meticulous translation engine. "
        "Never summarize, never omit content, and never add commentary."
    )

    prompt = (
        f"Translate this SINGLE Markdown line into {target_language_name} ({target_language_code}).\n"
        "Rules:\n"
        "- Output EXACTLY one line (no surrounding quotes, no code fences, no prefixes).\n"
        "- Preserve Markdown punctuation exactly (e.g., `#`, `-`, `*`, `|`, links).\n"
        "- Do NOT translate placeholders like ⟦CODE_0⟧ or ⟦URL_0⟧; keep them unchanged.\n"
        "- Do NOT add explanations.\n"
        "\n"
        f"LINE: {protected}\n"
    )

    last_error: Optional[str] = None
    for _attempt in range(retries + 1):
        try:
            raw = client.generate(prompt=prompt, system=system)
        except requests.exceptions.Timeout:
            last_error = "timeout"
            client.reset_session()
            continue
        except requests.exceptions.RequestException as e:
            last_error = str(e)
            client.reset_session()
            continue

        candidate = raw.strip("\r\n")
        if "\n" in candidate:
            candidate = candidate.splitlines()[0]
        candidate = candidate.strip()
        if not candidate:
            last_error = "empty response"
            continue

        # Ensure placeholders survive for inline code/URLs.
        for key in placeholders.keys():
            if key not in candidate:
                last_error = "placeholder lost"
                candidate = ""
                break
        if candidate == "":
            continue

        candidate = _restore_spans(candidate, placeholders)
        return leading_ws + candidate + newline

    print(f"      [!] Single-line fallback failed: {last_error}")
    return None


def translate_lines_resilient(
    client: OllamaClient,
    *,
    lines: Sequence[str],
    target_language_name: str,
    target_language_code: str,
    retries: int,
    split_budget: Optional[int] = None,
) -> Optional[str]:
    """Translate lines, automatically splitting smaller if the strict contract fails.

    This prevents a single bad chunk from failing an entire language run.
    """
    if not lines:
        return ""

    # Adaptive budget: ensure we can always reach single-line fallback when needed.
    if split_budget is None:
        # Depth to reach 1 line by halving: ceil(log2(n)). Add a small buffer.
        split_budget = max(6, int(math.ceil(math.log2(len(lines)))) + 2)

    translated = translate_lines_strict(
        client,
        lines=lines,
        target_language_name=target_language_name,
        target_language_code=target_language_code,
        retries=retries,
    )
    if translated is not None:
        return translated

    if len(lines) == 1:
        return translate_single_line_fallback(
            client,
            line=lines[0],
            target_language_name=target_language_name,
            target_language_code=target_language_code,
            retries=retries,
        )

    if split_budget <= 0:
        return None

    split_at = _find_best_split_index(lines)
    left = translate_lines_resilient(
        client,
        lines=lines[:split_at],
        target_language_name=target_language_name,
        target_language_code=target_language_code,
        retries=retries,
        split_budget=split_budget - 1,
    )
    if left is None:
        return None

    right = translate_lines_resilient(
        client,
        lines=lines[split_at:],
        target_language_name=target_language_name,
        target_language_code=target_language_code,
        retries=retries,
        split_budget=split_budget - 1,
    )
    if right is None:
        return None

    return left + right


def translate_markdown_document(
    client: OllamaClient,
    *,
    content: str,
    target_language_name: str,
    target_language_code: str,
    max_chunk_lines: int,
    max_chunk_chars: int,
    retries: int,
) -> Optional[str]:
    blocks = split_markdown_blocks(content)
    out_parts: List[str] = []

    for block in blocks:
        if block.kind == "code":
            out_parts.append("".join(block.lines))
            continue

        # chunk and translate
        for chunk in chunk_lines(block.lines, max_lines=max_chunk_lines, max_chars=max_chunk_chars):
            translated = translate_lines_resilient(
                client,
                lines=chunk,
                target_language_name=target_language_name,
                target_language_code=target_language_code,
                retries=retries,
            )
            if translated is None:
                return None
            out_parts.append(translated)

    return "".join(out_parts)


def looks_incomplete(existing_translation: str, source: str) -> bool:
    """Conservative heuristic to detect summaries/truncation in already-generated files."""
    if not existing_translation.strip():
        return True

    src_len = len(source.strip())
    out_len = len(existing_translation.strip())
    if src_len >= 2000 and out_len < int(src_len * 0.35):
        return True

    src_lines = len([l for l in source.splitlines() if l.strip()])
    out_lines = len([l for l in existing_translation.splitlines() if l.strip()])
    if src_lines >= 80 and out_lines < int(src_lines * 0.45):
        return True

    # Obvious “assistant” preambles.
    lowered = existing_translation.lstrip().lower()
    if lowered.startswith("sure") or lowered.startswith("here is") or "summary" in lowered[:200]:
        return True

    return False


# ----------------------------
# CLI / main
# ----------------------------


def get_git_mtime(filepath: str) -> int:
    """Return the modification time of a file based on git history.
    If the file has local uncommitted changes, returns its filesystem mtime.
    If git is unavailable, falls back to filesystem mtime.
    """
    try:
        # Check for uncommitted changes first
        status = subprocess.check_output(["git", "status", "--porcelain", filepath], text=True).strip()
        if status:
            return int(os.path.getmtime(filepath))
        
        # Get the timestamp of the last commit that modified this file
        out = subprocess.check_output(["git", "log", "-1", "--format=%ct", filepath], text=True).strip()
        if out:
            return int(out)
    except Exception:
        pass
    
    # Fallback to local filesystem mtime
    try:
        return int(os.path.getmtime(filepath))
    except OSError:
        return 0


def _parse_langs(arg: Optional[str]) -> Dict[str, str]:
    if not arg:
        return dict(LANGUAGES)

    wanted = {a.strip().lower() for a in arg.split(",") if a.strip()}
    resolved: Dict[str, str] = {}

    for name, code in LANGUAGES.items():
        if name.lower() in wanted or code.lower() in wanted:
            resolved[name] = code

    unknown = wanted - {n.lower() for n in LANGUAGES.keys()} - {c.lower() for c in LANGUAGES.values()}
    if unknown:
        raise SystemExit(f"Unknown languages: {', '.join(sorted(unknown))}")
    return resolved


def main() -> None:
    parser = argparse.ArgumentParser(description="Translate docs/tech-specs markdown files using a local Ollama model.")
    parser.add_argument("--docs-dir", default=DEFAULT_DOCS_DIR, help="Directory containing source .md files")
    parser.add_argument("--model", default=DEFAULT_OLLAMA_MODEL, help="Ollama model name")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL, help="Ollama /api/generate URL")
    parser.add_argument("--langs", default=None, help="Comma-separated language names or codes (e.g. 'es,ru')")
    parser.add_argument("--files", default="*.md", help="Glob pattern within docs-dir to translate (default: *.md)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing translations")
    parser.add_argument("--max-chunk-lines", type=int, default=DEFAULT_MAX_CHUNK_LINES)
    parser.add_argument("--max-chunk-chars", type=int, default=DEFAULT_MAX_CHUNK_CHARS)
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    parser.add_argument("--num-ctx", type=int, default=DEFAULT_NUM_CTX)
    parser.add_argument("--num-predict", type=int, default=DEFAULT_NUM_PREDICT)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    args = parser.parse_args()

    langs = _parse_langs(args.langs)

    client = OllamaClient(
        url=args.ollama_url,
        model=args.model,
        num_ctx=args.num_ctx,
        num_predict=args.num_predict,
        temperature=args.temperature,
        top_p=DEFAULT_TOP_P,
        repeat_penalty=DEFAULT_REPEAT_PENALTY,
        keep_alive=DEFAULT_KEEP_ALIVE,
    )

    docs_dir = args.docs_dir
    patterns = [args.files]

    files: List[str] = []
    for pattern in patterns:
        for path in glob.glob(os.path.join(docs_dir, pattern)):
            # Skip files that are already translated (contain e.g. .es.md)
            if any(f".{code}." in path for code in LANGUAGES.values()):
                continue
            files.append(path)

    files = sorted(set(files))
    if not files:
        print(f"No source files found in {docs_dir}")
        return

    print(f"Found {len(files)} files to translate in '{docs_dir}'.")
    print(f"Using Ollama model: {client.model}")
    print(f"Chunking: <= {args.max_chunk_lines} lines, <= {args.max_chunk_chars} chars")
    print("-" * 40)

    for filepath in files:
        path_obj = Path(filepath)
        filename_without_ext = path_obj.stem
        extension = path_obj.suffix

        print(f"Processing: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            print("  Skipping empty file.")
            continue

        for lang_name, lang_code in langs.items():
            out_filename = f"{filename_without_ext}.{lang_code}{extension}"
            out_filepath = os.path.join(docs_dir, out_filename)

            if os.path.exists(out_filepath) and os.path.getsize(out_filepath) > 0 and not args.force:
                with open(out_filepath, "r", encoding="utf-8") as existing_f:
                    existing = existing_f.read()
                
                source_mtime = get_git_mtime(filepath)
                dest_mtime = get_git_mtime(out_filepath)
                
                is_outdated = source_mtime > dest_mtime
                is_inc = looks_incomplete(existing, content)

                if not is_outdated and not is_inc:
                    print(f"  [-] Skipping {lang_name} ({out_filename}) - already exists and up to date.")
                    continue
                
                if is_outdated:
                    print(f"  [!] Source file is newer than existing {lang_name} translation; re-translating...")
                elif is_inc:
                    print(f"  [!] Existing {lang_name} looks incomplete; re-translating...")

            print(f"  [+] Translating to {lang_name}...")
            translated = translate_markdown_document(
                client,
                content=content,
                target_language_name=lang_name,
                target_language_code=lang_code,
                max_chunk_lines=args.max_chunk_lines,
                max_chunk_chars=args.max_chunk_chars,
                retries=args.retries,
            )

            if translated:
                with open(out_filepath, "w", encoding="utf-8") as out_f:
                    out_f.write(translated)
                print(f"      Saved -> {out_filepath}")
            else:
                print(f"      Failed to translate {filepath} to {lang_name}.")


if __name__ == "__main__":
    main()
