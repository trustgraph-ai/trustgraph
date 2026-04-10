# TrustGraph i18n & Documentation Translation Updates

The TrustGraph project has recently introduced comprehensive internationalization (i18n) support alongside powerful automated documentation translation capabilities. This update brings native language localization directly into the TrustGraph Command Line Interface (CLI) and includes an intelligent script designed to keep multi-language repository documentation fully synchronized with upstream changes.

## How the Translation & i18n Works

* **Native CLI i18n**: The TrustGraph CLI has built-in translation support that dynamically loads language strings. You can test and use different languages by simply passing the `--lang` flag (e.g., `--lang es` for Spanish, `--lang ru` for Russian) or by configuring your environment's `LANG` variable.
* **Automated LLM Translation**: The repository includes `translate_docs.py`, a script that leverages local Ollama models (such as `translategemma:12b`) to autonomously translate Markdown documentation into several target languages, including Spanish, Swahili, Portuguese, Turkish, Hindi, Hebrew, Arabic, Simplified Chinese, and Russian.
* **Intelligent Git-Aware Syncing**: The doc translator uses `git status` and `git log` modification timestamps to detect out-of-sync files. If a source file (like a core English `.md` file) receives newer commits or local edits, the script automatically flags the outdated translations and re-translates them to match the latest base version.
* **Safe Markdown Parsing**: To prevent the LLM from destroying technical formatting, the translation script chunks the text at safe boundaries, protects code fences, and uses placeholder tokens for inline code and URLs to ensure precision.

## Updated Documents

Because of the Git-aware translation capabilities, several core documents in the `docs/` folder have been successfully updated to parity across all supported languages, including:
* `python-api.md`
* API Gateway changelogs
* CLI changelogs
* Contributor License Agreements (CLAs)
* Assorted technical READMEs

*Note: The `translate_docs.py` translation engine will be moved out of the core TrustGraph repository into its own dedicated standalone repository in the near future.*