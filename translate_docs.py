import os
import requests
import glob
from pathlib import Path

# Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "translategemma:12b" # CHANGE THIS to your preferred local model (e.g., 'mistral', 'llama3', 'qwen')

LANGUAGES = {
    "Spanish": "es",
    "Swahili": "sw",
    "Hindi": "hi",
    "Hebrew": "he",
    "Arabic": "ar",
    "Chinese (simplified)": "zh-cn",
    "Russian": "ru"
}

DOCS_DIR = "docs/tech-specs"

def translate_text(text, target_language):
    prompt = f"""Translate the following documentation into {target_language}. 
CRITICAL INSTRUCTIONS:
- Provide a STRICT 1:1 translation. Every sentence of the provided text MUST be translated.
- You MUST use the native and correct alphabet/script for the target language (e.g., Cyrillic for Russian, Arabic script for Arabic, Devanagari for Hindi, Hebrew script for Hebrew, Simplified Chinese for Chinese). Swahili and Spanish use the Latin alphabet.
- Preserve ALL Markdown formatting, headers, links, and HTML tags precisely.
- Do NOT translate code inside backticks or code blocks.
- Output ONLY the translated text without any conversational preamble or explanations.

Text to translate:
{text}"""
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        # Reduced timeout to 180 seconds (3 minutes) to prevent endless freezing
        response = requests.post(OLLAMA_URL, json=payload, timeout=180)
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.exceptions.Timeout:
        print(f"  [!] Translation timed out (took longer than 3 minutes). Skipping to next.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"  [!] Failed to connect to Ollama or process translation: {e}")
        return None

def main():
    # Find all English markdown and html files in docs folder
    # Assuming original files don't have language suffixes
    files = []
    for ext in ['*.md']:
        for path in glob.glob(os.path.join(DOCS_DIR, ext)):
            # Skip files that are already translated (contain e.g. .es.md)
            if any(f".{code}." in path for code in LANGUAGES.values()):
                continue
            files.append(path)

    if not files:
        print("No source files found in docs/")
        return

    print(f"Found {len(files)} files to translate in '{DOCS_DIR}'.")
    print(f"Using Ollama model: {OLLAMA_MODEL}")
    print("-" * 40)

    for filepath in files:
        path_obj = Path(filepath)
        filename_without_ext = path_obj.stem
        extension = path_obj.suffix

        print(f"Processing: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        if not content.strip():
            print("  Skipping empty file.")
            continue

        for lang_name, lang_code in LANGUAGES.items():
            out_filename = f"{filename_without_ext}.{lang_code}{extension}"
            out_filepath = os.path.join(DOCS_DIR, out_filename)
            
            # Skip if file already exists AND has content (handles empty corrupted files from timeouts)
            if os.path.exists(out_filepath) and os.path.getsize(out_filepath) > 0:
                print(f"  [-] Skipping {lang_name} ({out_filename}) - already exists.")
                continue

            print(f"  [+] Translating to {lang_name}...")
            translated_content = translate_text(content, lang_name)
            
            if translated_content:
                with open(out_filepath, 'w', encoding='utf-8') as out_f:
                    out_f.write(translated_content)
                print(f"      Saved -> {out_filepath}")
            else:
                print(f"      Failed to translate {filepath} to {lang_name}.")

if __name__ == "__main__":
    main()
