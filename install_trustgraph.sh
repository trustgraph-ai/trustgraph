#!/usr/bin/env bash

set -Eeuo pipefail

APP_NAME="TrustGraph"
DEFAULT_API_URL="http://localhost:8088/"
DEFAULT_UI_URL="http://localhost:8888"
DEFAULT_INSTALL_DIR="trustgraph-deploy"
DEFAULT_OLLAMA_MODEL="granite4:350m"
DEFAULT_OLLAMA_EMBEDDINGS_MODEL="mxbai-embed-large"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${TG_INSTALL_DIR:-$SCRIPT_DIR/$DEFAULT_INSTALL_DIR}"
VENV_DIR="${TG_VENV_DIR:-$INSTALL_DIR/.venv}"
NLTK_DATA_DIR="${TG_NLTK_DATA_DIR:-$INSTALL_DIR/nltk_data}"
TIKTOKEN_CACHE_DIR_VALUE="${TIKTOKEN_CACHE_DIR:-$INSTALL_DIR/tiktoken_cache}"
PYTHON_BIN="python3"
API_URL="${TRUSTGRAPH_URL:-$DEFAULT_API_URL}"
UI_URL="${TRUSTGRAPH_UI_URL:-$DEFAULT_UI_URL}"

RUN_TESTS=1
AUTO_LAUNCH=1
NON_INTERACTIVE=0
DRY_RUN=0
YES=0
FRESH_INSTALL=0
REMOVE_ALL=0
USE_EXISTING_COMPOSE=""
HEALTH_TIMEOUT="${TG_HEALTH_TIMEOUT:-240}"
AUTH_CHECK_TIMEOUT="${TG_AUTH_CHECK_TIMEOUT:-45}"

AUTH_TOKEN="${TRUSTGRAPH_TOKEN:-}"
LLM_MODE=""
OPENAI_TOKEN_VALUE="${OPENAI_TOKEN:-}"
OPENAI_BASE_URL_VALUE="${OPENAI_BASE_URL:-https://api.openai.com/v1}"
OLLAMA_BASE_URL_VALUE="${OLLAMA_HOST:-${OLLAMA_BASE_URL:-}}"
OLLAMA_MODEL="${OLLAMA_MODEL:-$DEFAULT_OLLAMA_MODEL}"
OLLAMA_EMBEDDINGS_MODEL="${OLLAMA_EMBEDDINGS_MODEL:-$DEFAULT_OLLAMA_EMBEDDINGS_MODEL}"

HW_OS=""
HW_ARCH=""
HW_CPU_CORES="unknown"
HW_MEMORY_GB="unknown"
HW_GPU="none detected"
HW_CONTAINER_HINT=""
RECOMMENDED_LLM_MODE="openai"
RECOMMENDATION_REASON=""
COMPOSE_CMD=()
COLOR_RESET=""
COLOR_HEADING=""
COLOR_INFO=""
COLOR_WARN=""
COLOR_ERROR=""
COLOR_ACCENT=""

usage() {
    cat <<'USAGE'
Usage: ./install_trustgraph.sh [options]

Guided local installer for TrustGraph. It detects the machine hardware,
recommends a local or hosted LLM path, asks for the few required values,
enumerates local Ollama models when relevant, runs the repo tests, generates
a deployment with the existing config tool, starts the stack, checks health,
and opens the Workbench UI.

Options:
  --install-dir PATH        Directory for generated deployment files.
  --api-url URL             API gateway URL for health checks.
  --ui-url URL              Workbench UI URL to open.
  --use-existing-compose F  Skip config generation and start this compose file.
  --skip-tests              Do not run the full pytest suite.
  --no-launch               Do not open the Workbench UI at the end.
  --non-interactive         Use defaults where possible. Best with --dry-run or
                            --use-existing-compose.
  --yes                     Accept confirmation prompts.
  --fresh                   Remove installer-managed files in --install-dir
                            before generating a new deployment.
  --remove-all              Uninstall the installer-managed deployment:
                            stop containers, remove compose volumes, and
                            delete only installer-managed files.
  --dry-run                 Show detected hardware and planned defaults only.
  -h, --help                Show this help.

Environment defaults:
  TRUSTGRAPH_TOKEN, TRUSTGRAPH_URL, OPENAI_TOKEN, OPENAI_BASE_URL,
  OLLAMA_HOST, OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_EMBEDDINGS_MODEL,
  TG_INSTALL_DIR, TG_VENV_DIR, TG_NLTK_DATA_DIR, TIKTOKEN_CACHE_DIR,
  TG_HEALTH_TIMEOUT
USAGE
}

say() {
    printf '\n%b%s%b\n' "$COLOR_HEADING" "$*" "$COLOR_RESET"
}

info() {
    printf '  %b%s%b\n' "$COLOR_INFO" "$*" "$COLOR_RESET"
}

warn() {
    printf '%bWarning:%b %s\n' "$COLOR_WARN" "$COLOR_RESET" "$*" >&2
}

die() {
    printf '%bError:%b %s\n' "$COLOR_ERROR" "$COLOR_RESET" "$*" >&2
    exit 1
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

spinner_enabled() {
    [[ "${TG_NO_SPINNER:-0}" != "1" ]] && { [[ -t 2 ]] || [[ "${TG_FORCE_SPINNER:-0}" == "1" ]]; }
}

clear_spinner_line() {
    printf '\r\033[K' >&2
}

run_with_spinner() {
    local message="$1"
    shift
    local frames=('|' '/' '-' '\')
    local frame=0
    local pid
    local status

    if ! spinner_enabled; then
        "$@"
        return
    fi

    "$@" &
    pid=$!
    while kill -0 "$pid" 2>/dev/null; do
        printf '\r  %b%s%b %s' "$COLOR_ACCENT" "${frames[$frame]}" "$COLOR_RESET" "$message" >&2
        frame=$(((frame + 1) % ${#frames[@]}))
        sleep 0.2
    done

    if wait "$pid"; then
        status=0
    else
        status=$?
    fi

    clear_spinner_line
    if [[ "$status" -eq 0 ]]; then
        info "Done: $message"
    else
        warn "Failed: $message"
    fi
    return "$status"
}

run_with_spinner_logged() {
    local message="$1"
    local log_file="$2"
    shift 2
    local frames=('|' '/' '-' '\')
    local frame=0
    local pid
    local status

    if ! spinner_enabled; then
        "$@"
        return
    fi

    mkdir -p "$(dirname "$log_file")"
    "$@" >"$log_file" 2>&1 &
    pid=$!
    while kill -0 "$pid" 2>/dev/null; do
        printf '\r  %b%s%b %s' "$COLOR_ACCENT" "${frames[$frame]}" "$COLOR_RESET" "$message" >&2
        frame=$(((frame + 1) % ${#frames[@]}))
        sleep 0.2
    done

    if wait "$pid"; then
        status=0
    else
        status=$?
    fi

    clear_spinner_line
    if [[ "$status" -eq 0 ]]; then
        info "Done: $message"
    else
        warn "Failed: $message"
        warn "Last log lines from $log_file:"
        tail -n 40 "$log_file" >&2 || true
    fi
    return "$status"
}

installer_log_file() {
    local name="$1"
    mkdir -p "$INSTALL_DIR/logs"
    printf '%s/logs/%s.log\n' "$INSTALL_DIR" "$name"
}

command_to_text() {
    local arg
    local out=""

    for arg in "$@"; do
        if [[ -n "$out" ]]; then
            out="$out "
        fi
        out="$out$(printf '%q' "$arg")"
    done

    printf '%s\n' "$out"
}

root_command_to_text() {
    if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
        command_to_text "$@"
    elif command_exists sudo; then
        command_to_text sudo "$@"
    else
        command_to_text "$@"
    fi
}

run_root_command() {
    if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
        "$@"
    elif command_exists sudo; then
        sudo "$@"
    else
        warn "Could not find sudo. Run this installer as an administrator or install the prerequisite manually."
        return 1
    fi
}

confirm_install_command() {
    local question="$1"
    local command_text="$2"

    info "Command: $command_text"

    if [[ "$YES" -eq 1 ]]; then
        return 0
    fi

    if [[ "$NON_INTERACTIVE" -eq 1 ]]; then
        return 1
    fi

    confirm "$question" 1
}

init_colors() {
    if [[ -n "${NO_COLOR:-}" || ! -t 1 ]]; then
        return
    fi

    if command_exists tput && tput colors >/dev/null 2>&1 && [[ "$(tput colors)" -ge 8 ]]; then
        COLOR_RESET="$(tput sgr0)"
        COLOR_HEADING="$(tput bold)$(tput setaf 6)"
        COLOR_INFO="$(tput setaf 2)"
        COLOR_WARN="$(tput setaf 3)"
        COLOR_ERROR="$(tput bold)$(tput setaf 1)"
        COLOR_ACCENT="$(tput bold)$(tput setaf 5)"
    fi
}

print_banner() {
    printf '\n%b+---------------------------+%b\n' "$COLOR_ACCENT" "$COLOR_RESET"
    printf '%b| Touchgraph Easy Installer |%b\n' "$COLOR_ACCENT" "$COLOR_RESET"
    printf '%b+---------------------------+%b\n' "$COLOR_ACCENT" "$COLOR_RESET"
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --install-dir)
                [[ $# -ge 2 ]] || die "--install-dir needs a path"
                INSTALL_DIR="$2"
                shift 2
                ;;
            --api-url)
                [[ $# -ge 2 ]] || die "--api-url needs a URL"
                API_URL="$2"
                shift 2
                ;;
            --ui-url)
                [[ $# -ge 2 ]] || die "--ui-url needs a URL"
                UI_URL="$2"
                shift 2
                ;;
            --use-existing-compose)
                [[ $# -ge 2 ]] || die "--use-existing-compose needs a file path"
                USE_EXISTING_COMPOSE="$2"
                shift 2
                ;;
            --skip-tests)
                RUN_TESTS=0
                shift
                ;;
            --no-launch)
                AUTO_LAUNCH=0
                shift
                ;;
            --non-interactive)
                NON_INTERACTIVE=1
                shift
                ;;
            --yes)
                YES=1
                shift
                ;;
            --fresh)
                FRESH_INSTALL=1
                shift
                ;;
            --remove-all)
                REMOVE_ALL=1
                shift
                ;;
            --dry-run)
                DRY_RUN=1
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                die "Unknown option: $1"
                ;;
        esac
    done

    case "$API_URL" in
        */) ;;
        *) API_URL="$API_URL/" ;;
    esac
}

prompt_value() {
    local label="$1"
    local default="$2"
    local helper="$3"
    local answer=""

    if [[ -n "$helper" ]]; then
        printf '  %s\n' "$helper" >&2
    fi

    if [[ "$NON_INTERACTIVE" -eq 1 ]]; then
        printf '%s\n' "$default"
        return
    fi

    if [[ -n "$default" ]]; then
        read -r -p "$label [$default]: " answer
        printf '%s\n' "${answer:-$default}"
    else
        read -r -p "$label: " answer
        printf '%s\n' "$answer"
    fi
}

looks_like_embedding_ollama_model() {
    local model
    model="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"

    case "$model" in
        *embed*|*embedding*|*nomic*|*mxbai*|*bge*|*e5*|*gte*|*minilm*|*snowflake-arctic*)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

ollama_model_candidates() {
    local kind="$1"
    shift
    local model
    local selected=()

    for model in "$@"; do
        case "$kind" in
            embeddings)
                if looks_like_embedding_ollama_model "$model"; then
                    selected+=("$model")
                fi
                ;;
            chat)
                if ! looks_like_embedding_ollama_model "$model"; then
                    selected+=("$model")
                fi
                ;;
            *)
                selected+=("$model")
                ;;
        esac
    done

    if [[ "${#selected[@]}" -eq 0 ]]; then
        selected=("$@")
    fi

    for model in "${selected[@]}"; do
        printf '%s\n' "$model"
    done
}

ollama_api_bases_for_host() {
    local base="${OLLAMA_BASE_URL_VALUE%/}"
    base="${base%/v1}"

    [[ -n "$base" ]] || base="http://localhost:11434"
    printf '%s\n' "$base"

    case "$base" in
        *host.docker.internal*)
            printf '%s\n' "${base//host.docker.internal/localhost}"
            ;;
        *0.0.0.0*)
            printf '%s\n' "${base//0.0.0.0/localhost}"
            ;;
    esac
}

list_ollama_models_from_cli_for_host() {
    local host="${1:-}"

    command_exists ollama || return 0

    if [[ -n "$host" ]]; then
        OLLAMA_HOST="$host" ollama list 2>/dev/null | awk 'NR > 1 && $1 != "" { print $1 }' || true
    else
        ollama list 2>/dev/null | awk 'NR > 1 && $1 != "" { print $1 }' || true
    fi
}

list_ollama_models_from_cli() {
    local base

    list_ollama_models_from_cli_for_host

    if [[ -n "$OLLAMA_BASE_URL_VALUE" ]]; then
        while IFS= read -r base; do
            [[ -n "$base" ]] || continue
            list_ollama_models_from_cli_for_host "$base"
        done < <(ollama_api_bases_for_host)
    fi
}

list_ollama_models_from_api() {
    command_exists curl || return 0
    command_exists python3 || return 0

    local base
    local response

    while IFS= read -r base; do
        [[ -n "$base" ]] || continue
        response="$(curl -fsS --max-time 2 "${base%/}/api/tags" 2>/dev/null || true)"
        [[ -n "$response" ]] || continue

        printf '%s' "$response" | python3 -c 'import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    raise SystemExit(0)
for model in data.get("models", []):
    name = model.get("name") or model.get("model")
    if name:
        print(name)
' 2>/dev/null || true
    done < <(ollama_api_bases_for_host)
}

list_ollama_models() {
    {
        list_ollama_models_from_cli
        list_ollama_models_from_api
    } | awk 'NF && !seen[$0]++'
}

ollama_model_name_matches() {
    local installed="$1"
    local target="$2"

    [[ "$installed" == "$target" ]] && return 0
    [[ "$target" != *:* && "$installed" == "$target:latest" ]] && return 0
    [[ "$installed" != *:* && "$target" == "$installed:latest" ]] && return 0

    return 1
}

find_reachable_ollama_cli_host() {
    local base

    command_exists ollama || return 1

    if ollama list >/dev/null 2>&1; then
        printf '\n'
        return 0
    fi

    while IFS= read -r base; do
        [[ -n "$base" ]] || continue
        if OLLAMA_HOST="$base" ollama list >/dev/null 2>&1; then
            printf '%s\n' "$base"
            return 0
        fi
    done < <(ollama_api_bases_for_host)

    return 1
}

ollama_model_available_via_cli_host() {
    local host="$1"
    local target="$2"
    local model

    while IFS= read -r model; do
        ollama_model_name_matches "$model" "$target" && return 0
    done < <(list_ollama_models_from_cli_for_host "$host")

    return 1
}

pull_ollama_model() {
    local host="$1"
    local model="$2"
    local log_file
    log_file="$(installer_log_file "ollama-pull-${model//\//-}")"

    if [[ -n "$host" ]]; then
        run_with_spinner_logged "Downloading Ollama model $model" "$log_file" env OLLAMA_HOST="$host" ollama pull "$model"
    else
        run_with_spinner_logged "Downloading Ollama model $model" "$log_file" ollama pull "$model"
    fi
}

wait_for_ollama_service() {
    local timeout="${1:-30}"
    local deadline=$((SECONDS + timeout))

    while (( SECONDS < deadline )); do
        if find_reachable_ollama_cli_host >/dev/null 2>&1; then
            return 0
        fi
        sleep 2
    done

    return 1
}

start_ollama_service_if_possible() {
    local command_text
    local log_file="$INSTALL_DIR/ollama.log"

    say "Ollama service is not running"

    if [[ "$HW_OS" == "Darwin" ]] && command_exists open && [[ -d /Applications/Ollama.app ]]; then
        command_text="$(command_to_text open -a Ollama)"
        if confirm_install_command "Start the Ollama app now?" "$command_text"; then
            open -a Ollama
            wait_for_ollama_service 45
            return
        fi
    fi

    if command_exists brew; then
        command_text="$(command_to_text brew services start ollama)"
        if confirm_install_command "Start the Ollama service with Homebrew now?" "$command_text"; then
            brew services start ollama
            wait_for_ollama_service 45
            return
        fi
    fi

    command_text="$(command_to_text ollama serve) > $(printf '%q' "$log_file") 2>&1 &"
    if confirm_install_command "Start Ollama in the background now?" "$command_text"; then
        mkdir -p "$INSTALL_DIR"
        nohup ollama serve > "$log_file" 2>&1 &
        wait_for_ollama_service 45
        return
    fi

    return 1
}

offer_single_ollama_model_download() {
    local kind="$1"
    local default_model="$2"
    local selected_model="$3"
    local processor_label="$4"
    local cli_host="$5"
    local question

    say "Preparing Ollama $kind model"
    info "TrustGraph's Ollama $processor_label default is $default_model."

    if ollama_model_available_via_cli_host "$cli_host" "$selected_model"; then
        info "Ollama $kind model already available: $selected_model"
        return 0
    fi

    if [[ "$selected_model" == "$default_model" ]]; then
        question="Download TrustGraph's preferred Ollama $kind model ($selected_model) now?"
    else
        question="Download the selected Ollama $kind model ($selected_model) now?"
    fi

    if confirm "$question" 1; then
        info "Downloading $selected_model with Ollama. This may take a while."
        if ! pull_ollama_model "$cli_host" "$selected_model"; then
            die "Ollama could not download $selected_model. Try running: ollama pull $selected_model"
        fi
    else
        warn "Skipping Ollama $kind model download. TrustGraph's Ollama processor will try to pull $selected_model on first use."
    fi
}

offer_ollama_model_downloads() {
    local cli_host

    [[ "$LLM_MODE" == "ollama" ]] || return 0

    if ! command_exists ollama; then
        warn "Ollama was selected, but the ollama CLI was not found. Install Ollama and run: ollama pull $OLLAMA_MODEL && ollama pull $OLLAMA_EMBEDDINGS_MODEL"
        return 0
    fi

    if ! cli_host="$(find_reachable_ollama_cli_host)"; then
        start_ollama_service_if_possible || true
        if ! cli_host="$(find_reachable_ollama_cli_host)"; then
            warn "Ollama CLI is installed, but the Ollama service is not reachable. Start Ollama and run: ollama pull $OLLAMA_MODEL && ollama pull $OLLAMA_EMBEDDINGS_MODEL"
            return 0
        fi
    fi

    if [[ -n "$cli_host" ]]; then
        info "Ollama service: $cli_host"
    else
        info "Ollama service: local Ollama default"
    fi

    offer_single_ollama_model_download \
        "chat" \
        "$DEFAULT_OLLAMA_MODEL" \
        "$OLLAMA_MODEL" \
        "text-completion" \
        "$cli_host"

    offer_single_ollama_model_download \
        "embeddings" \
        "$DEFAULT_OLLAMA_EMBEDDINGS_MODEL" \
        "$OLLAMA_EMBEDDINGS_MODEL" \
        "embeddings" \
        "$cli_host"
}

prompt_ollama_model_choice() {
    local label="$1"
    local default="$2"
    local kind="$3"
    local helper="$4"
    shift 4
    local all_models=("$@")
    local candidates=()
    local options=()
    local model
    local answer
    local idx
    local found_default=0
    local detected_default=""

    if [[ "$NON_INTERACTIVE" -eq 1 ]]; then
        printf '%s\n' "$default"
        return
    fi

    if [[ -n "$helper" ]]; then
        printf '  %s\n' "$helper" >&2
    fi

    if [[ "${#all_models[@]}" -eq 0 ]]; then
        prompt_value \
            "$label" \
            "$default" \
            "No local Ollama models were detected. Pull the recommended default with: ollama pull $default"
        return
    fi

    while IFS= read -r model; do
        [[ -n "$model" ]] && candidates+=("$model")
    done < <(ollama_model_candidates "$kind" "${all_models[@]}")

    if [[ "${#candidates[@]}" -eq 0 ]]; then
        candidates=("${all_models[@]}")
    fi

    for model in "${candidates[@]}"; do
        if ollama_model_name_matches "$model" "$default"; then
            found_default=1
            detected_default="$model"
            break
        fi
    done

    options+=("$default")
    for model in "${candidates[@]}"; do
        ollama_model_name_matches "$model" "$default" && continue
        options+=("$model")
    done

    say "Local Ollama ${kind} model choices" >&2
    if [[ "$found_default" -eq 1 ]]; then
        if [[ "$detected_default" != "$default" ]]; then
            info "1) $default (recommended, detected as $detected_default)" >&2
        else
            info "1) $default (recommended, detected)" >&2
        fi
    else
        info "1) $default (recommended default, not detected locally)" >&2
    fi

    idx=2
    for model in "${options[@]:1}"; do
        info "$idx) $model" >&2
        idx=$((idx + 1))
    done
    if [[ "$found_default" -eq 0 ]]; then
        info "If you choose a missing model, the installer will offer to download it before startup." >&2
    fi
    info "Or type another model name, for example one you plan to pull before startup." >&2

    read -r -p "$label [1: $default]: " answer
    answer="${answer:-1}"

    if [[ "$answer" =~ ^[0-9]+$ ]]; then
        if (( answer >= 1 && answer <= ${#options[@]} )); then
            printf '%s\n' "${options[$((answer - 1))]}"
            return
        fi
        warn "Selection '$answer' is not in the list; using $default."
        printf '%s\n' "$default"
        return
    fi

    printf '%s\n' "$answer"
}

prompt_secret() {
    local label="$1"
    local default="$2"
    local helper="$3"
    local answer=""
    local masked="${4:-}"

    if [[ -z "$masked" && -n "$default" ]]; then
        masked="set in environment"
    elif [[ -z "$masked" ]]; then
        masked="blank"
    fi

    if [[ -n "$helper" ]]; then
        printf '  %s\n' "$helper" >&2
    fi

    if [[ "$NON_INTERACTIVE" -eq 1 ]]; then
        printf '%s\n' "$default"
        return
    fi

    read -r -s -p "$label [$masked]: " answer
    printf '\n' >&2
    printf '%s\n' "${answer:-$default}"
}

confirm() {
    local question="$1"
    local default_yes="$2"
    local answer=""
    local prompt="[y/N]"

    if [[ "$YES" -eq 1 ]]; then
        return 0
    fi

    if [[ "$NON_INTERACTIVE" -eq 1 ]]; then
        [[ "$default_yes" -eq 1 ]]
        return
    fi

    if [[ "$default_yes" -eq 1 ]]; then
        prompt="[Y/n]"
    fi

    read -r -p "$question $prompt " answer
    answer="${answer:-}"
    if [[ -z "$answer" ]]; then
        [[ "$default_yes" -eq 1 ]]
        return
    fi
    [[ "$answer" =~ ^[Yy] ]]
}

path_within_install_dir() {
    local path="$1"
    case "$path" in
        "$INSTALL_DIR"/*) return 0 ;;
        *) return 1 ;;
    esac
}

safe_existing_path_within_install_dir() {
    local path="$1"
    local resolved_install
    local resolved_parent
    local resolved_path
    local parent
    local base

    [[ -d "$INSTALL_DIR" ]] || return 1
    [[ -e "$path" || -L "$path" ]] || return 1

    resolved_install="$(cd "$INSTALL_DIR" && pwd -P)"
    parent="$(dirname "$path")"
    base="$(basename "$path")"
    [[ -d "$parent" ]] || return 1
    resolved_parent="$(cd "$parent" && pwd -P)"
    resolved_path="$resolved_parent/$base"

    case "$resolved_path" in
        "$resolved_install"/*) return 0 ;;
        *) return 1 ;;
    esac
}

installer_artifact_paths() {
    local candidates=(
        "$INSTALL_DIR/deploy.zip"
        "$INSTALL_DIR/deploy"
        "$INSTALL_DIR/INSTALLATION.md"
        "$INSTALL_DIR/trustgraph-installer.env"
        "$INSTALL_DIR/iam-bootstrap.log"
        "$INSTALL_DIR/ollama.log"
        "$INSTALL_DIR/logs"
        "$INSTALL_DIR/pip_cache"
    )
    local path

    for path in "$VENV_DIR" "$NLTK_DATA_DIR" "$TIKTOKEN_CACHE_DIR_VALUE"; do
        if path_within_install_dir "$path"; then
            candidates+=("$path")
        fi
    done

    for path in "${candidates[@]}"; do
        if [[ -e "$path" || -L "$path" ]]; then
            printf '%s\n' "$path"
        fi
    done
}

installer_artifacts_present() {
    local path
    while IFS= read -r path; do
        [[ -n "$path" ]] && return 0
    done < <(installer_artifact_paths)
    return 1
}

assert_safe_cleanup_target() {
    local resolved_install
    local resolved_script
    local resolved_home=""

    [[ -n "$INSTALL_DIR" ]] || die "Install directory is empty; refusing cleanup."
    case "$INSTALL_DIR" in
        /|.|..) die "Install directory '$INSTALL_DIR' is too broad; refusing cleanup." ;;
    esac

    if [[ -d "$INSTALL_DIR" ]]; then
        resolved_install="$(cd "$INSTALL_DIR" && pwd -P)"
    else
        return 0
    fi
    resolved_script="$(cd "$SCRIPT_DIR" && pwd -P)"
    if [[ -n "${HOME:-}" && -d "$HOME" ]]; then
        resolved_home="$(cd "$HOME" && pwd -P)"
    fi

    [[ "$resolved_install" != "$resolved_script" ]] || die "Install directory resolves to the source checkout; refusing cleanup."
    [[ -z "$resolved_home" || "$resolved_install" != "$resolved_home" ]] || die "Install directory resolves to your home directory; refusing cleanup."
}

find_existing_compose_file() {
    [[ -d "$INSTALL_DIR" ]] || return 0

    find "$INSTALL_DIR/deploy" "$INSTALL_DIR" \
        \( -name 'docker-compose.yaml' -o -name 'docker-compose.yml' -o -name 'compose.yaml' -o -name 'compose.yml' \) \
        -type f 2>/dev/null | head -n 1
}

stop_previous_stack_if_possible() {
    local compose_file
    compose_file="$(find_existing_compose_file || true)"
    [[ -n "$compose_file" ]] || return 0

    if ! confirm "Stop any containers from the previous deployment first? Docker volumes will be kept." 1; then
        info "Leaving any previous containers untouched."
        return
    fi

    if ! detect_compose_command; then
        warn "Could not find Docker Compose or podman-compose, so previous containers were not stopped."
        return
    fi

    if "${COMPOSE_CMD[@]}" -f "$compose_file" down --remove-orphans; then
        info "Stopped previous compose deployment using $compose_file"
    else
        warn "Could not stop previous compose deployment. Continuing with file cleanup only."
    fi
}

remove_installer_artifacts_only() {
    local path

    say "Removing installer-managed files"
    while IFS= read -r path; do
        [[ -n "$path" ]] || continue
        if ! safe_existing_path_within_install_dir "$path"; then
            warn "Skipping cleanup path outside install directory: $path"
            continue
        fi
        info "Removing $path"
        rm -rf -- "$path"
    done < <(installer_artifact_paths)

    rmdir "$INSTALL_DIR" 2>/dev/null || true
}

cleanup_installer_artifacts() {
    assert_safe_cleanup_target
    stop_previous_stack_if_possible
    remove_installer_artifacts_only
}

find_uninstall_compose_file() {
    if [[ -n "$USE_EXISTING_COMPOSE" ]]; then
        [[ -f "$USE_EXISTING_COMPOSE" ]] || die "Compose file does not exist: $USE_EXISTING_COMPOSE"
        printf '%s\n' "$USE_EXISTING_COMPOSE"
        return
    fi

    find_existing_compose_file || true
}

print_uninstall_plan() {
    local compose_file="$1"
    local path
    local found=0

    say "Uninstall plan"
    info "Install directory: $INSTALL_DIR"
    if [[ -n "$compose_file" ]]; then
        info "Compose file: $compose_file"
        info "Will stop containers and remove compose-managed volumes for this deployment."
    else
        info "No compose file was found, so no containers or volumes can be removed automatically."
    fi

    info "Installer-managed files to remove:"
    while IFS= read -r path; do
        [[ -n "$path" ]] || continue
        found=1
        info "- $path"
    done < <(installer_artifact_paths)
    if [[ "$found" -eq 0 ]]; then
        info "- none found"
    fi

    info "Will not remove Docker/Podman, container images, external volumes, Ollama, Ollama models, or this source checkout."
}

remove_compose_stack_for_uninstall() {
    local compose_file="$1"

    [[ -n "$compose_file" ]] || return 0

    say "Stopping TrustGraph containers and volumes"
    if ! detect_compose_command; then
        warn "Could not find Docker Compose or podman-compose, so containers and volumes were not removed."
        return
    fi

    if "${COMPOSE_CMD[@]}" -f "$compose_file" down --remove-orphans --volumes; then
        info "Removed compose containers, networks, and compose-managed volumes."
        return
    fi

    warn "Compose did not accept the volume removal command; trying to stop containers without removing volumes."
    if "${COMPOSE_CMD[@]}" -f "$compose_file" down --remove-orphans; then
        warn "Containers were stopped, but compose volumes may remain."
    else
        warn "Could not stop the compose deployment. Installer-managed files will still be removed."
    fi
}

remove_all_installation() {
    local compose_file

    assert_safe_cleanup_target
    compose_file="$(find_uninstall_compose_file || true)"

    print_uninstall_plan "$compose_file"

    if [[ "$DRY_RUN" -eq 1 ]]; then
        say "Dry run complete"
        return 0
    fi

    if [[ -z "$compose_file" ]] && ! installer_artifacts_present; then
        say "Nothing to remove"
        info "No installer-managed files or compose deployment were found."
        return 0
    fi

    if ! confirm "Remove the TrustGraph deployment listed above?" 0; then
        die "Uninstall cancelled."
    fi

    remove_compose_stack_for_uninstall "$compose_file"
    remove_installer_artifacts_only

    say "TrustGraph installer-managed deployment removed"
    info "Ollama models were left in place because they may be shared with other tools."
}

handle_existing_install() {
    local path
    local found=0

    [[ -z "$USE_EXISTING_COMPOSE" ]] || return 0
    installer_artifacts_present || return 0

    say "Existing installer output detected"
    info "Install directory: $INSTALL_DIR"
    while IFS= read -r path; do
        [[ -n "$path" ]] || continue
        found=1
        info "Found: $path"
    done < <(installer_artifact_paths)

    [[ "$found" -eq 1 ]] || return 0

    if [[ "$DRY_RUN" -eq 1 ]]; then
        if [[ "$FRESH_INSTALL" -eq 1 ]]; then
            info "Dry run: --fresh would remove the files listed above."
        else
            info "Dry run: existing files would be kept unless you choose --fresh."
        fi
        return 0
    fi

    if [[ "$FRESH_INSTALL" -eq 1 ]]; then
        cleanup_installer_artifacts
        return 0
    fi

    if confirm "Treat this as a fresh install and delete only the installer-managed files listed above?" 0; then
        cleanup_installer_artifacts
    else
        info "Continuing with the existing installer output."
    fi
}

load_saved_answers() {
    local env_file="$INSTALL_DIR/trustgraph-installer.env"

    [[ -f "$env_file" ]] || return 0

    local current_api_url="$API_URL"
    local current_ui_url="$UI_URL"
    local current_auth_token="$AUTH_TOKEN"
    local current_venv_dir="$VENV_DIR"
    local current_nltk_data_dir="$NLTK_DATA_DIR"
    local current_tiktoken_cache_dir="$TIKTOKEN_CACHE_DIR_VALUE"
    local current_llm_mode="$LLM_MODE"
    local current_openai_base_url="$OPENAI_BASE_URL_VALUE"
    local current_openai_token="$OPENAI_TOKEN_VALUE"
    local current_ollama_base_url="$OLLAMA_BASE_URL_VALUE"
    local current_ollama_model="$OLLAMA_MODEL"
    local current_ollama_embeddings_model="$OLLAMA_EMBEDDINGS_MODEL"

    # The file is generated by this installer with shell-escaped exports and 0600 permissions.
    # shellcheck disable=SC1090
    source "$env_file"

    if [[ "$current_api_url" == "$DEFAULT_API_URL" && -n "${TRUSTGRAPH_URL:-}" ]]; then
        API_URL="$TRUSTGRAPH_URL"
    else
        API_URL="$current_api_url"
    fi

    if [[ "$current_ui_url" == "$DEFAULT_UI_URL" && -n "${TRUSTGRAPH_UI_URL:-}" ]]; then
        UI_URL="$TRUSTGRAPH_UI_URL"
    else
        UI_URL="$current_ui_url"
    fi

    if [[ -z "$current_auth_token" && -n "${TRUSTGRAPH_TOKEN:-}" ]]; then
        AUTH_TOKEN="$TRUSTGRAPH_TOKEN"
    elif [[ -z "$current_auth_token" && -n "${IAM_BOOTSTRAP_TOKEN:-}" ]]; then
        AUTH_TOKEN="$IAM_BOOTSTRAP_TOKEN"
    else
        AUTH_TOKEN="$current_auth_token"
    fi

    if [[ -z "${TG_VENV_DIR:-}" && -n "${current_venv_dir:-}" ]]; then
        VENV_DIR="$current_venv_dir"
    elif [[ -n "${TG_VENV_DIR:-}" ]]; then
        VENV_DIR="$TG_VENV_DIR"
    fi

    if [[ -z "${TG_NLTK_DATA_DIR:-}" && -n "$current_nltk_data_dir" ]]; then
        NLTK_DATA_DIR="$current_nltk_data_dir"
    elif [[ -n "${TG_NLTK_DATA_DIR:-}" ]]; then
        NLTK_DATA_DIR="$TG_NLTK_DATA_DIR"
    fi

    if [[ -z "${TIKTOKEN_CACHE_DIR:-}" && -n "$current_tiktoken_cache_dir" ]]; then
        TIKTOKEN_CACHE_DIR_VALUE="$current_tiktoken_cache_dir"
    elif [[ -n "${TIKTOKEN_CACHE_DIR:-}" ]]; then
        TIKTOKEN_CACHE_DIR_VALUE="$TIKTOKEN_CACHE_DIR"
    fi

    if [[ -z "$current_llm_mode" && -n "${TRUSTGRAPH_LLM_MODE:-}" ]]; then
        LLM_MODE="$TRUSTGRAPH_LLM_MODE"
    else
        LLM_MODE="$current_llm_mode"
    fi

    if [[ "$current_openai_base_url" == "https://api.openai.com/v1" && -n "${OPENAI_BASE_URL:-}" ]]; then
        OPENAI_BASE_URL_VALUE="$OPENAI_BASE_URL"
    else
        OPENAI_BASE_URL_VALUE="$current_openai_base_url"
    fi

    if [[ -z "$current_openai_token" && -n "${OPENAI_TOKEN:-}" ]]; then
        OPENAI_TOKEN_VALUE="$OPENAI_TOKEN"
    else
        OPENAI_TOKEN_VALUE="$current_openai_token"
    fi

    if [[ -z "$current_ollama_base_url" ]]; then
        OLLAMA_BASE_URL_VALUE="${OLLAMA_HOST:-${OLLAMA_BASE_URL:-}}"
    else
        OLLAMA_BASE_URL_VALUE="$current_ollama_base_url"
    fi

    if [[ "$current_ollama_model" == "$DEFAULT_OLLAMA_MODEL" && -n "${OLLAMA_MODEL:-}" ]]; then
        OLLAMA_MODEL="$OLLAMA_MODEL"
    else
        OLLAMA_MODEL="$current_ollama_model"
    fi

    if [[ "$current_ollama_embeddings_model" == "$DEFAULT_OLLAMA_EMBEDDINGS_MODEL" && -n "${OLLAMA_EMBEDDINGS_MODEL:-}" ]]; then
        OLLAMA_EMBEDDINGS_MODEL="$OLLAMA_EMBEDDINGS_MODEL"
    else
        OLLAMA_EMBEDDINGS_MODEL="$current_ollama_embeddings_model"
    fi

    case "$API_URL" in
        */) ;;
        *) API_URL="$API_URL/" ;;
    esac

    info "Loaded saved answers from $env_file"
}

bytes_to_gb() {
    local bytes="$1"
    awk "BEGIN { printf \"%.0f\", $bytes / 1024 / 1024 / 1024 }"
}

detect_hardware() {
    HW_OS="$(uname -s 2>/dev/null || printf 'unknown')"
    HW_ARCH="$(uname -m 2>/dev/null || printf 'unknown')"

    if [[ "$HW_OS" == "Darwin" ]]; then
        HW_CPU_CORES="$(sysctl -n hw.logicalcpu 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || python3 -c 'import os; print(os.cpu_count() or "unknown")' 2>/dev/null || printf 'unknown')"
        local mem_bytes
        mem_bytes="$(sysctl -n hw.memsize 2>/dev/null || true)"
        if [[ -z "$mem_bytes" ]] && command_exists python3; then
            mem_bytes="$(python3 -c 'import os; print(os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE"))' 2>/dev/null || true)"
        fi
        if [[ -n "$mem_bytes" ]]; then
            HW_MEMORY_GB="$(bytes_to_gb "$mem_bytes")"
        fi
        if [[ "$HW_ARCH" == "arm64" ]]; then
            HW_GPU="Apple Silicon unified GPU"
        fi
        HW_CONTAINER_HINT="Docker Desktop or Podman Desktop works well on macOS."
    elif [[ "$HW_OS" == "Linux" ]]; then
        HW_CPU_CORES="$(nproc 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || python3 -c 'import os; print(os.cpu_count() or "unknown")' 2>/dev/null || printf 'unknown')"
        if [[ -r /proc/meminfo ]]; then
            local mem_kb
            mem_kb="$(awk '/MemTotal/ { print $2 }' /proc/meminfo)"
            if [[ -n "$mem_kb" ]]; then
                HW_MEMORY_GB="$(awk "BEGIN { printf \"%.0f\", $mem_kb / 1024 / 1024 }")"
            fi
        fi
        if command_exists nvidia-smi; then
            HW_GPU="$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -n 1 || true)"
            [[ -n "$HW_GPU" ]] || HW_GPU="NVIDIA GPU detected"
        elif command_exists lspci; then
            HW_GPU="$(lspci 2>/dev/null | awk 'BEGIN{IGNORECASE=1} /VGA|3D|Display/ {print; exit}')"
            [[ -n "$HW_GPU" ]] || HW_GPU="none detected"
        fi
        HW_CONTAINER_HINT="Docker Engine, Docker Desktop, or Podman can run the compose stack."
    else
        HW_CONTAINER_HINT="Use Docker or Podman with compose support."
    fi
}

is_number() {
    [[ "$1" =~ ^[0-9]+$ ]]
}

choose_recommendations() {
    local mem=0
    local cores=0

    if is_number "$HW_MEMORY_GB"; then
        mem="$HW_MEMORY_GB"
    fi
    if is_number "$HW_CPU_CORES"; then
        cores="$HW_CPU_CORES"
    fi

    if [[ -z "$OLLAMA_BASE_URL_VALUE" ]]; then
        if [[ "$HW_OS" == "Darwin" ]]; then
            OLLAMA_BASE_URL_VALUE="http://host.docker.internal:11434"
        else
            OLLAMA_BASE_URL_VALUE="http://localhost:11434"
        fi
    fi

    if [[ -n "$LLM_MODE" ]]; then
        RECOMMENDED_LLM_MODE="$LLM_MODE"
        RECOMMENDATION_REASON="Using the LLM provider saved from the previous installer run."
        return
    fi

    if (( mem >= 16 )) && { [[ "$HW_GPU" != "none detected" ]] || (( cores >= 8 )); }; then
        RECOMMENDED_LLM_MODE="ollama"
        RECOMMENDATION_REASON="This machine looks comfortable for a small local Ollama model."
    elif (( mem >= 8 )); then
        RECOMMENDED_LLM_MODE="openai"
        RECOMMENDATION_REASON="Local Ollama may work with a small model, but a hosted OpenAI-compatible endpoint is smoother on this hardware."
    else
        RECOMMENDED_LLM_MODE="openai"
        RECOMMENDATION_REASON="Memory looks tight for local LLMs, so a hosted OpenAI-compatible endpoint is the friendlier default."
    fi

    if [[ -n "${OPENAI_TOKEN:-}" && "${OPENAI_TOKEN:-}" != "ollama" ]]; then
        RECOMMENDED_LLM_MODE="openai"
        RECOMMENDATION_REASON="OPENAI_TOKEN is already set, so the hosted/OpenAI-compatible path is ready to use."
    fi
}

print_hardware_summary() {
    say "Detected hardware"
    info "OS: $HW_OS"
    info "Architecture: $HW_ARCH"
    info "CPU cores: $HW_CPU_CORES"
    info "Memory: $HW_MEMORY_GB GB"
    info "GPU: $HW_GPU"
    info "$HW_CONTAINER_HINT"

    say "Recommended install shape"
    info "LLM path: $RECOMMENDED_LLM_MODE"
    info "$RECOMMENDATION_REASON"
    info "Default Workbench UI: $UI_URL"
    info "Default API gateway: $API_URL"
}

generate_token() {
    if command_exists openssl; then
        printf 'tg_%s\n' "$(openssl rand -base64 24 | tr '+/' '-_' | tr -d '=')"
    elif command_exists python3; then
        python3 -c 'import secrets; print("tg_" + secrets.token_urlsafe(24))'
    else
        die "Need openssl or python3 to generate a secure TrustGraph API key."
    fi
}

ensure_compliant_api_key() {
    local token="$1"

    if [[ "$token" == tg_* ]]; then
        printf '%s\n' "$token"
        return
    fi

    warn "TrustGraph API keys must start with 'tg_'; the provided value will not authenticate at the gateway."

    if [[ "$NON_INTERACTIVE" -eq 1 ]]; then
        warn "Non-interactive mode: replacing the non-compliant key with a generated TrustGraph API key."
        generate_token
        return
    fi

    if confirm "Generate a compliant TrustGraph API key now?" 1; then
        generate_token
        return
    fi

    die "TrustGraph API key must start with 'tg_'."
}

collect_answers() {
    local generated_token
    local token_default
    local token_mask
    generated_token="$(generate_token)"
    if [[ -n "$AUTH_TOKEN" ]]; then
        token_default="$AUTH_TOKEN"
        token_mask="set in environment"
    else
        token_default="$generated_token"
        token_mask="generated tg_ key"
    fi
    AUTH_TOKEN="$(prompt_secret \
        "TrustGraph admin/bootstrap API key" \
        "$token_default" \
        "Recommendation: press Enter to use a generated TrustGraph API key beginning with tg_; it will be stored in the installer env file with restricted permissions." \
        "$token_mask")"
    AUTH_TOKEN="$(ensure_compliant_api_key "$AUTH_TOKEN")"

    LLM_MODE="$(prompt_value \
        "LLM provider: ollama, openai, or none" \
        "${LLM_MODE:-$RECOMMENDED_LLM_MODE}" \
        "Recommendation: $RECOMMENDED_LLM_MODE. $RECOMMENDATION_REASON")"
    LLM_MODE="$(printf '%s' "$LLM_MODE" | tr '[:upper:]' '[:lower:]')"

    case "$LLM_MODE" in
        ollama)
            OLLAMA_BASE_URL_VALUE="$(prompt_value \
                "Ollama base URL" \
                "$OLLAMA_BASE_URL_VALUE" \
                "If Ollama runs on your laptop and TrustGraph runs in Docker, host.docker.internal is usually the right host on macOS/Windows.")"
            local ollama_models=()
            local ollama_model
            if [[ "$NON_INTERACTIVE" -ne 1 ]]; then
                while IFS= read -r ollama_model; do
                    [[ -n "$ollama_model" ]] && ollama_models+=("$ollama_model")
                done < <(list_ollama_models)
            fi
            if [[ "${#ollama_models[@]}" -gt 0 ]]; then
                OLLAMA_MODEL="$(prompt_ollama_model_choice \
                    "Ollama chat model" \
                    "$OLLAMA_MODEL" \
                    "chat" \
                    "Recommendation from the local Ollama processor defaults: $DEFAULT_OLLAMA_MODEL for a quick first run." \
                    "${ollama_models[@]}")"
                OLLAMA_EMBEDDINGS_MODEL="$(prompt_ollama_model_choice \
                    "Ollama embeddings model" \
                    "$OLLAMA_EMBEDDINGS_MODEL" \
                    "embeddings" \
                    "Recommendation from the local Ollama embeddings defaults: $DEFAULT_OLLAMA_EMBEDDINGS_MODEL." \
                    "${ollama_models[@]}")"
            else
                OLLAMA_MODEL="$(prompt_ollama_model_choice \
                    "Ollama chat model" \
                    "$OLLAMA_MODEL" \
                    "chat" \
                    "Recommendation from the local Ollama processor defaults: $DEFAULT_OLLAMA_MODEL for a quick first run.")"
                OLLAMA_EMBEDDINGS_MODEL="$(prompt_ollama_model_choice \
                    "Ollama embeddings model" \
                    "$OLLAMA_EMBEDDINGS_MODEL" \
                    "embeddings" \
                    "Recommendation from the local Ollama embeddings defaults: $DEFAULT_OLLAMA_EMBEDDINGS_MODEL.")"
            fi
            OPENAI_BASE_URL_VALUE="${OLLAMA_BASE_URL_VALUE%/}/v1"
            OPENAI_TOKEN_VALUE="${OPENAI_TOKEN_VALUE:-ollama}"
            ;;
        openai)
            OPENAI_BASE_URL_VALUE="$(prompt_value \
                "OpenAI-compatible base URL" \
                "$OPENAI_BASE_URL_VALUE" \
                "Use https://api.openai.com/v1 for OpenAI, or your provider's OpenAI-compatible /v1 endpoint.")"
            OPENAI_TOKEN_VALUE="$(prompt_secret \
                "OpenAI-compatible API key" \
                "$OPENAI_TOKEN_VALUE" \
                "Press Enter to reuse OPENAI_TOKEN if set; leave blank only if your endpoint does not require a key.")"
            ;;
        none|skip)
            LLM_MODE="none"
            warn "Continuing without an LLM key. The platform can start, but agent/RAG calls will need an LLM configured later."
            ;;
        *)
            warn "Unknown LLM provider '$LLM_MODE'; using '$RECOMMENDED_LLM_MODE'."
            LLM_MODE="$RECOMMENDED_LLM_MODE"
            ;;
    esac

    INSTALL_DIR="$(prompt_value \
        "Installer output directory" \
        "$INSTALL_DIR" \
        "This keeps deploy.zip, compose files, logs, and saved answers together.")"

    if [[ -z "${TG_VENV_DIR:-}" ]]; then
        VENV_DIR="$INSTALL_DIR/.venv"
    fi
    if [[ -z "${TG_NLTK_DATA_DIR:-}" ]]; then
        NLTK_DATA_DIR="$INSTALL_DIR/nltk_data"
    fi
    if [[ -z "${TIKTOKEN_CACHE_DIR:-}" ]]; then
        TIKTOKEN_CACHE_DIR_VALUE="$INSTALL_DIR/tiktoken_cache"
    fi
}

print_plan_summary() {
    say "Install plan"
    info "Install directory: $INSTALL_DIR"
    info "Python venv: $VENV_DIR"
    info "NLTK data: $NLTK_DATA_DIR"
    info "Tokenizer cache: $TIKTOKEN_CACHE_DIR_VALUE"
    info "Run all tests: $([[ "$RUN_TESTS" -eq 1 ]] && printf yes || printf no)"
    if [[ -n "$USE_EXISTING_COMPOSE" ]]; then
        info "Compose file: $USE_EXISTING_COMPOSE"
    else
        info "Config generator: npx @trustgraph/config"
    fi
    info "LLM provider: $LLM_MODE"
    if [[ "$LLM_MODE" == "ollama" ]]; then
        info "Ollama URL: $OLLAMA_BASE_URL_VALUE"
        info "Ollama model: $OLLAMA_MODEL"
        info "Ollama embeddings model: $OLLAMA_EMBEDDINGS_MODEL"
    elif [[ "$LLM_MODE" == "openai" ]]; then
        info "OpenAI-compatible URL: $OPENAI_BASE_URL_VALUE"
    fi
    info "Health check timeout: ${HEALTH_TIMEOUT}s"
    info "Autolaunch UI: $([[ "$AUTO_LAUNCH" -eq 1 ]] && printf yes || printf no)"
}

detect_compose_command() {
    if command_exists docker && docker compose version >/dev/null 2>&1; then
        COMPOSE_CMD=(docker compose)
    elif command_exists docker-compose; then
        COMPOSE_CMD=(docker-compose)
    elif command_exists podman-compose; then
        COMPOSE_CMD=(podman-compose)
    else
        return 1
    fi
}

wait_for_docker_ready() {
    local timeout="${1:-60}"
    local deadline=$((SECONDS + timeout))

    while (( SECONDS < deadline )); do
        if docker info >/dev/null 2>&1; then
            return 0
        fi
        sleep 2
    done

    return 1
}

wait_for_podman_ready() {
    local timeout="${1:-60}"
    local deadline=$((SECONDS + timeout))

    while (( SECONDS < deadline )); do
        if podman info >/dev/null 2>&1; then
            return 0
        fi
        sleep 2
    done

    return 1
}

start_docker_runtime_if_possible() {
    local command_text

    say "Docker is installed but not running"

    if [[ "$HW_OS" == "Darwin" ]] && command_exists open && [[ -d /Applications/Docker.app ]]; then
        command_text="$(command_to_text open -a Docker)"
        if confirm_install_command "Start Docker Desktop now?" "$command_text"; then
            open -a Docker
            wait_for_docker_ready 90
            return
        fi
    fi

    if command_exists systemctl; then
        command_text="$(root_command_to_text systemctl start docker)"
        if confirm_install_command "Start the Docker service now?" "$command_text"; then
            run_root_command systemctl start docker
            wait_for_docker_ready 60
            return
        fi
    fi

    return 1
}

start_podman_runtime_if_possible() {
    local command_text

    say "Podman is installed but not running"

    if [[ "$HW_OS" == "Darwin" ]] && command_exists podman; then
        command_text="$(command_to_text podman machine init) && $(command_to_text podman machine start)"
        if confirm_install_command "Start a local Podman machine now?" "$command_text"; then
            podman machine init >/dev/null 2>&1 || true
            podman machine start
            wait_for_podman_ready 90
            return
        fi
    fi

    if command_exists systemctl; then
        command_text="$(command_to_text systemctl --user start podman.socket)"
        if confirm_install_command "Start the user Podman socket now?" "$command_text"; then
            systemctl --user start podman.socket
            wait_for_podman_ready 30
            return
        fi
    fi

    return 1
}

check_container_runtime_ready() {
    case "${COMPOSE_CMD[0]}" in
        docker|docker-compose)
            if ! docker info >/dev/null 2>&1; then
                start_docker_runtime_if_possible || true
                docker info >/dev/null 2>&1 || die "Docker is installed, but the Docker daemon is not reachable. Start Docker Desktop or Docker Engine and run this installer again."
            fi
            ;;
        podman-compose)
            if ! podman info >/dev/null 2>&1; then
                start_podman_runtime_if_possible || true
                podman info >/dev/null 2>&1 || die "Podman is installed, but the Podman service is not reachable. Start Podman Desktop or the Podman machine and run this installer again."
            fi
            ;;
    esac
}

install_with_brew() {
    local label="$1"
    shift
    local command_text
    local log_file
    command_text="$(command_to_text brew install "$@")"
    log_file="$(installer_log_file "brew-install-${label// /-}")"

    if confirm_install_command "Install $label with Homebrew now?" "$command_text"; then
        run_with_spinner_logged "Installing $label with Homebrew" "$log_file" brew install "$@"
    else
        return 1
    fi
}

install_with_apt() {
    local label="$1"
    shift
    local command_text
    command_text="$(root_command_to_text apt-get update) && $(root_command_to_text apt-get install -y "$@")"

    if confirm_install_command "Install $label with apt now?" "$command_text"; then
        run_root_command apt-get update
        run_root_command apt-get install -y "$@"
    else
        return 1
    fi
}

install_with_dnf() {
    local label="$1"
    shift
    local command_text
    command_text="$(root_command_to_text dnf install -y "$@")"

    if confirm_install_command "Install $label with dnf now?" "$command_text"; then
        run_root_command dnf install -y "$@"
    else
        return 1
    fi
}

install_with_yum() {
    local label="$1"
    shift
    local command_text
    command_text="$(root_command_to_text yum install -y "$@")"

    if confirm_install_command "Install $label with yum now?" "$command_text"; then
        run_root_command yum install -y "$@"
    else
        return 1
    fi
}

install_with_pacman() {
    local label="$1"
    shift
    local command_text
    command_text="$(root_command_to_text pacman -Sy --noconfirm "$@")"

    if confirm_install_command "Install $label with pacman now?" "$command_text"; then
        run_root_command pacman -Sy --noconfirm "$@"
    else
        return 1
    fi
}

install_with_zypper() {
    local label="$1"
    shift
    local command_text
    command_text="$(root_command_to_text zypper install -y "$@")"

    if confirm_install_command "Install $label with zypper now?" "$command_text"; then
        run_root_command zypper install -y "$@"
    else
        return 1
    fi
}

install_python3_prerequisite() {
    if command_exists brew; then
        install_with_brew "Python 3" python
    elif command_exists apt-get; then
        install_with_apt "Python 3" python3 python3-venv python3-pip
    elif command_exists dnf; then
        install_with_dnf "Python 3" python3 python3-pip
    elif command_exists yum; then
        install_with_yum "Python 3" python3 python3-pip
    elif command_exists pacman; then
        install_with_pacman "Python 3" python
    elif command_exists zypper; then
        install_with_zypper "Python 3" python3 python3-pip python3-venv
    else
        warn "No supported package manager was found. Install Python 3 manually, then run this installer again."
        return 1
    fi
}

install_python_venv_prerequisite() {
    if command_exists apt-get; then
        install_with_apt "Python venv support" python3-venv
    elif command_exists zypper; then
        install_with_zypper "Python venv support" python3-venv
    elif command_exists brew || command_exists dnf || command_exists yum || command_exists pacman; then
        info "Python venv support is usually bundled with the Python package on this platform."
        return 1
    else
        warn "Install Python's venv module manually, then run this installer again."
        return 1
    fi
}

install_basic_tool_prerequisite() {
    local tool="$1"

    if command_exists brew; then
        install_with_brew "$tool" "$tool"
    elif command_exists apt-get; then
        install_with_apt "$tool" "$tool"
    elif command_exists dnf; then
        install_with_dnf "$tool" "$tool"
    elif command_exists yum; then
        install_with_yum "$tool" "$tool"
    elif command_exists pacman; then
        install_with_pacman "$tool" "$tool"
    elif command_exists zypper; then
        install_with_zypper "$tool" "$tool"
    else
        warn "No supported package manager was found. Install $tool manually, then run this installer again."
        return 1
    fi
}

install_node_prerequisite() {
    if command_exists brew; then
        install_with_brew "Node.js and npx" node
    elif command_exists apt-get; then
        install_with_apt "Node.js and npx" nodejs npm
    elif command_exists dnf; then
        install_with_dnf "Node.js and npx" nodejs npm
    elif command_exists yum; then
        install_with_yum "Node.js and npx" nodejs npm
    elif command_exists pacman; then
        install_with_pacman "Node.js and npx" nodejs npm
    elif command_exists zypper; then
        install_with_zypper "Node.js and npx" nodejs npm
    else
        warn "No supported package manager was found. Install Node.js/npm manually, then run this installer again."
        return 1
    fi
}

start_podman_machine_if_needed() {
    [[ "$HW_OS" == "Darwin" ]] || return 0
    command_exists podman || return 0

    if podman info >/dev/null 2>&1; then
        return 0
    fi

    if ! confirm_install_command \
        "Start a local Podman machine now?" \
        "$(command_to_text podman machine init) && $(command_to_text podman machine start)"; then
        return 1
    fi

    podman machine init >/dev/null 2>&1 || true
    podman machine start
}

install_compose_prerequisite() {
    if command_exists docker && ! docker compose version >/dev/null 2>&1; then
        if command_exists brew; then
            install_with_brew "Docker Compose" docker-compose
        elif command_exists apt-get; then
            install_with_apt "Docker Compose plugin" docker-compose-plugin
        elif command_exists dnf; then
            install_with_dnf "Docker Compose plugin" docker-compose-plugin
        elif command_exists yum; then
            install_with_yum "Docker Compose plugin" docker-compose-plugin
        elif command_exists pacman; then
            install_with_pacman "Docker Compose" docker-compose
        elif command_exists zypper; then
            install_with_zypper "Docker Compose" docker-compose
        else
            warn "Install Docker Compose manually, then run this installer again."
            return 1
        fi
        return
    fi

    if command_exists podman && ! command_exists podman-compose; then
        if command_exists brew; then
            install_with_brew "podman-compose" podman-compose
        elif command_exists apt-get; then
            install_with_apt "podman-compose" podman-compose
        elif command_exists dnf; then
            install_with_dnf "podman-compose" podman-compose
        elif command_exists yum; then
            install_with_yum "podman-compose" podman-compose
        elif command_exists pacman; then
            install_with_pacman "podman-compose" podman-compose
        elif command_exists zypper; then
            install_with_zypper "podman-compose" podman-compose
        else
            warn "Install podman-compose manually, then run this installer again."
            return 1
        fi
        start_podman_machine_if_needed || true
        return
    fi

    if command_exists brew; then
        info "Docker Desktop also works well. The CLI-friendly fallback is Podman plus podman-compose."
        install_with_brew "Podman and podman-compose" podman podman-compose
        start_podman_machine_if_needed || true
    elif command_exists apt-get; then
        install_with_apt "Podman and podman-compose" podman podman-compose
    elif command_exists dnf; then
        install_with_dnf "Podman and podman-compose" podman podman-compose
    elif command_exists yum; then
        install_with_yum "Podman and podman-compose" podman podman-compose
    elif command_exists pacman; then
        install_with_pacman "Podman and podman-compose" podman podman-compose
    elif command_exists zypper; then
        install_with_zypper "Podman and podman-compose" podman podman-compose
    else
        warn "Install Docker Desktop, Docker Engine with Compose, or Podman with podman-compose, then run this installer again."
        return 1
    fi
}

install_ollama_prerequisite() {
    local command_text

    if command_exists brew; then
        install_with_brew "Ollama" ollama
    elif [[ "$HW_OS" == "Linux" ]] && command_exists curl; then
        command_text="curl -fsSL https://ollama.com/install.sh | sh"
        info "This uses Ollama's official Linux install script."
        if confirm_install_command "Install Ollama now?" "$command_text"; then
            sh -c "$command_text"
        else
            return 1
        fi
    else
        warn "Install Ollama from https://ollama.com/download, then run this installer again."
        return 1
    fi
}

ensure_python3_available() {
    command_exists python3 && return 0

    say "Python 3 is missing"
    install_python3_prerequisite || die "Python 3 is required to run tests and helper CLIs."
    command_exists python3 || die "Python 3 was not found after installation. Open a new terminal or add it to PATH, then run this installer again."
}

ensure_python_venv_available() {
    python3 -m venv --help >/dev/null 2>&1 && return 0

    say "Python venv support is missing"
    install_python_venv_prerequisite || die "Python venv support is required to create the installer environment."
    python3 -m venv --help >/dev/null 2>&1 || die "Python venv support is still unavailable. Open a new terminal or install python3-venv manually."
}

ensure_basic_tool_available() {
    local tool="$1"
    local reason="$2"

    command_exists "$tool" && return 0

    say "$tool is missing"
    info "$reason"
    install_basic_tool_prerequisite "$tool" || die "$tool is required. Install it manually, then run this installer again."
    command_exists "$tool" || die "$tool was not found after installation. Open a new terminal or add it to PATH, then run this installer again."
}

ensure_npx_available() {
    [[ -n "$USE_EXISTING_COMPOSE" ]] && return 0
    command_exists npx && return 0

    say "npx is missing"
    info "npx is required for the existing TrustGraph config generator: npx @trustgraph/config."
    install_node_prerequisite || die "npx is required. Install Node.js/npm manually, then run this installer again."
    command_exists npx || die "npx was not found after installation. Open a new terminal or add it to PATH, then run this installer again."
}

ensure_compose_available() {
    detect_compose_command && return 0

    say "Container compose support is missing"
    info "TrustGraph runs as a compose stack. Docker Compose or podman-compose is required."
    install_compose_prerequisite || die "Docker Compose or podman-compose is required to start TrustGraph."
    detect_compose_command || die "Compose support was not found after installation. Open a new terminal or add it to PATH, then run this installer again."
}

ensure_ollama_available_if_needed() {
    [[ "$LLM_MODE" == "ollama" ]] || return 0
    command_exists ollama && return 0

    say "Ollama is missing"
    info "Ollama was selected for local LLMs, so the Ollama CLI and service are needed before model setup."
    install_ollama_prerequisite || die "Ollama is required for the selected local LLM path. Install it manually, then run this installer again."
    command_exists ollama || die "Ollama was not found after installation. Open a new terminal or add it to PATH, then run this installer again."
}

preflight() {
    say "Checking prerequisites"

    ensure_python3_available
    ensure_python_venv_available
    ensure_basic_tool_available unzip "unzip is required to unpack deploy.zip from the config generator."
    ensure_basic_tool_available curl "curl is required for startup health checks and local service probes."
    ensure_npx_available
    ensure_compose_available
    ensure_ollama_available_if_needed
    check_container_runtime_ready

    info "Compose command: ${COMPOSE_CMD[*]}"
    info "Python: $(python3 --version 2>&1)"
    if command_exists npx; then
        info "npx: $(npx --version 2>/dev/null || printf unknown)"
    fi
}

write_env_file() {
    mkdir -p "$INSTALL_DIR"
    local env_file="$INSTALL_DIR/trustgraph-installer.env"
    local grafana_admin_password="${GF_SECURITY_ADMIN_PASSWORD:-${GRAFANA_ADMIN_PASSWORD:-$AUTH_TOKEN}}"

    umask 077
    {
        printf 'export TRUSTGRAPH_URL=%q\n' "$API_URL"
        printf 'export TRUSTGRAPH_UI_URL=%q\n' "$UI_URL"
        printf 'export TRUSTGRAPH_TOKEN=%q\n' "$AUTH_TOKEN"
        printf 'export TRUSTGRAPH_BOOTSTRAP_TOKEN=%q\n' "$AUTH_TOKEN"
        printf 'export IAM_BOOTSTRAP_TOKEN=%q\n' "$AUTH_TOKEN"
        printf 'export GF_SECURITY_ADMIN_PASSWORD=%q\n' "$grafana_admin_password"
        printf 'export TG_VENV_DIR=%q\n' "$VENV_DIR"
        printf 'export TG_NLTK_DATA_DIR=%q\n' "$NLTK_DATA_DIR"
        printf 'export NLTK_DATA=%q\n' "$NLTK_DATA_DIR${NLTK_DATA:+:$NLTK_DATA}"
        printf 'export TIKTOKEN_CACHE_DIR=%q\n' "$TIKTOKEN_CACHE_DIR_VALUE"
        printf 'export TRUSTGRAPH_LLM_MODE=%q\n' "$LLM_MODE"
        printf 'export OPENAI_BASE_URL=%q\n' "$OPENAI_BASE_URL_VALUE"
        printf 'export OPENAI_TOKEN=%q\n' "$OPENAI_TOKEN_VALUE"
        printf 'export OLLAMA_HOST=%q\n' "$OLLAMA_BASE_URL_VALUE"
        printf 'export OLLAMA_BASE_URL=%q\n' "$OLLAMA_BASE_URL_VALUE"
        printf 'export OLLAMA_MODEL=%q\n' "$OLLAMA_MODEL"
        printf 'export OLLAMA_EMBEDDINGS_MODEL=%q\n' "$OLLAMA_EMBEDDINGS_MODEL"
    } > "$env_file"
    chmod 600 "$env_file"

    info "Saved answers to $env_file"
}

prepare_python_env() {
    say "Preparing Python environment"
    mkdir -p "$INSTALL_DIR"

    if [[ ! -x "$VENV_DIR/bin/python" ]]; then
        info "Creating venv at $VENV_DIR"
        run_with_spinner "Creating Python venv" python3 -m venv "$VENV_DIR"
    else
        info "Using existing venv at $VENV_DIR"
    fi

    PYTHON_BIN="$VENV_DIR/bin/python"
    export PATH="$VENV_DIR/bin:$PATH"
    info "Python venv: $($PYTHON_BIN --version 2>&1)"
}

ensure_version_files() {
    local version="${TRUSTGRAPH_LOCAL_VERSION:-2.5.0}"
    local specs=(
        "trustgraph-base/trustgraph/base_version.py:trustgraph.base_version"
        "trustgraph-flow/trustgraph/flow_version.py:trustgraph.flow_version"
        "trustgraph-vertexai/trustgraph/vertexai_version.py:trustgraph.vertexai_version"
        "trustgraph-bedrock/trustgraph/bedrock_version.py:trustgraph.bedrock_version"
        "trustgraph-embeddings-hf/trustgraph/embeddings_hf_version.py:trustgraph.embeddings_hf_version"
        "trustgraph-cli/trustgraph/cli_version.py:trustgraph.cli_version"
        "trustgraph-ocr/trustgraph/ocr_version.py:trustgraph.ocr_version"
        "trustgraph-unstructured/trustgraph/unstructured_version.py:trustgraph.unstructured_version"
        "trustgraph-mcp/trustgraph/mcp_version.py:trustgraph.mcp_version"
        "trustgraph/trustgraph/trustgraph_version.py:trustgraph.trustgraph_version"
    )

    say "Ensuring local package version files"
    for spec in "${specs[@]}"; do
        local file="${spec%%:*}"
        mkdir -p "$(dirname "$SCRIPT_DIR/$file")"
        printf '__version__ = "%s"\n' "$version" > "$SCRIPT_DIR/$file"
        info "Set $file to $version"
    done
}

local_package_pythonpath() {
    local package_dirs=(
        "$SCRIPT_DIR/trustgraph-flow"
        "$SCRIPT_DIR/trustgraph-embeddings-hf"
        "$SCRIPT_DIR/trustgraph-base"
        "$SCRIPT_DIR/trustgraph-cli"
        "$SCRIPT_DIR/trustgraph-bedrock"
        "$SCRIPT_DIR/trustgraph-ocr"
        "$SCRIPT_DIR/trustgraph-unstructured"
        "$SCRIPT_DIR/trustgraph-mcp"
        "$SCRIPT_DIR/trustgraph-vertexai"
        "$SCRIPT_DIR/trustgraph"
    )
    local joined=""
    local dir

    for dir in "${package_dirs[@]}"; do
        if [[ -d "$dir" ]]; then
            if [[ -n "$joined" ]]; then
                joined="$joined:$dir"
            else
                joined="$dir"
            fi
        fi
    done

    printf '%s\n' "$joined"
}

ensure_python_build_tools() {
    say "Preparing Python build tools"
    local pip_cache_dir="$INSTALL_DIR/pip_cache"
    mkdir -p "$pip_cache_dir"

    if ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
        local ensurepip_log
        ensurepip_log="$(installer_log_file "python-ensurepip")"
        info "Installing pip into the Python venv"
        run_with_spinner_logged \
            "Installing pip" \
            "$ensurepip_log" \
            "$PYTHON_BIN" -m ensurepip --upgrade \
            || die "Could not install pip into the Python venv."
    fi

    if "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import setuptools.build_meta
PY
    then
        info "Python build backend available: setuptools.build_meta"
        return
    fi

    local log_file
    log_file="$(installer_log_file "pip-build-tools")"
    info "Installing setuptools and wheel into the Python venv"
    run_with_spinner_logged \
        "Installing Python build tools" \
        "$log_file" \
        env \
        PIP_CACHE_DIR="$pip_cache_dir" \
        PIP_DISABLE_PIP_VERSION_CHECK=1 \
        "$PYTHON_BIN" -m pip install "setuptools>=61" wheel \
        || die "Could not install setuptools/wheel. Check $log_file, then re-run the installer."
}

install_test_packages() {
    say "Installing local Python packages for tests"
    local pip_cache_dir="$INSTALL_DIR/pip_cache"
    mkdir -p "$pip_cache_dir"
    ensure_python_build_tools

    local package_dirs=(
        trustgraph-base
        trustgraph-cli
        trustgraph-flow
        trustgraph-vertexai
        trustgraph-bedrock
        trustgraph-embeddings-hf
        trustgraph-ocr
        trustgraph-unstructured
        trustgraph-mcp
    )

    for package_dir in "${package_dirs[@]}"; do
        if [[ -d "$SCRIPT_DIR/$package_dir" ]]; then
            local log_file
            log_file="$(installer_log_file "pip-${package_dir}")"
            info "Installing $package_dir"
            run_with_spinner_logged \
                "Installing $package_dir" \
                "$log_file" \
                env \
                PIP_CACHE_DIR="$pip_cache_dir" \
                PIP_DISABLE_PIP_VERSION_CHECK=1 \
                "$PYTHON_BIN" -m pip install --no-build-isolation "$SCRIPT_DIR/$package_dir"
        fi
    done

    if [[ -f "$SCRIPT_DIR/tests/requirements.txt" ]]; then
        local log_file
        log_file="$(installer_log_file "pip-test-requirements")"
        info "Installing test requirements"
        run_with_spinner_logged \
            "Installing test requirements" \
            "$log_file" \
            env \
            PIP_CACHE_DIR="$pip_cache_dir" \
            PIP_DISABLE_PIP_VERSION_CHECK=1 \
            "$PYTHON_BIN" -m pip install -r "$SCRIPT_DIR/tests/requirements.txt"
    fi
}

ensure_tokenizer_cache() {
    say "Preparing tokenizer cache"
    mkdir -p "$TIKTOKEN_CACHE_DIR_VALUE"
    info "tiktoken cache: $TIKTOKEN_CACHE_DIR_VALUE"

    TIKTOKEN_CACHE_DIR="$TIKTOKEN_CACHE_DIR_VALUE" "$PYTHON_BIN" - <<'PY'
import tiktoken

tiktoken.get_encoding("cl100k_base")
print("  Cached tiktoken encoding: cl100k_base")
PY
}

ensure_nltk_data() {
    say "Preparing NLTK tokenizer data"
    mkdir -p "$NLTK_DATA_DIR"
    info "NLTK data: $NLTK_DATA_DIR"

    TG_NLTK_DATA_DIR="$NLTK_DATA_DIR" \
    NLTK_DATA="$NLTK_DATA_DIR${NLTK_DATA:+:$NLTK_DATA}" \
    "$PYTHON_BIN" - <<'PY'
import os
import nltk

target = os.environ["TG_NLTK_DATA_DIR"]
if target not in nltk.data.path:
    nltk.data.path.insert(0, target)

resources = (
    ("punkt", "tokenizers/punkt"),
    ("punkt_tab", "tokenizers/punkt_tab"),
    ("averaged_perceptron_tagger_eng", "taggers/averaged_perceptron_tagger_eng"),
)

for package, resource in resources:
    try:
        nltk.data.find(resource)
    except LookupError:
        print(f"  Downloading NLTK resource: {package}")
        if not nltk.download(package, download_dir=target, quiet=True):
            raise SystemExit(f"Could not download NLTK resource: {package}")
    else:
        print(f"  NLTK resource already available: {package}")
PY
}

run_all_tests() {
    if [[ "$RUN_TESTS" -ne 1 ]]; then
        warn "Skipping tests because --skip-tests was supplied."
        return
    fi

    prepare_python_env
    ensure_version_files
    install_test_packages
    ensure_tokenizer_cache
    ensure_nltk_data

    say "Running all tests"
    info "Command: $PYTHON_BIN -m pytest tests"
    local test_log
    test_log="$(installer_log_file "pytest")"
    if spinner_enabled; then
        info "Test output log: $test_log"
    fi
    (
        cd "$SCRIPT_DIR"
        run_with_spinner_logged \
            "Running pytest tests" \
            "$test_log" \
            env \
            INSTALL_TRUSTGRAPH_SOURCE_ONLY= \
            TG_NO_SPINNER= \
            TG_FORCE_SPINNER= \
            NLTK_DATA="$NLTK_DATA_DIR${NLTK_DATA:+:$NLTK_DATA}" \
            TIKTOKEN_CACHE_DIR="$TIKTOKEN_CACHE_DIR_VALUE" \
            TRUSTGRAPH_CASSANDRA_SKIP_ON_UNREADY=1 \
            "$PYTHON_BIN" -m pytest tests
    )
}

show_config_guidance() {
    say "Before the config wizard starts"
    info "Choose a Docker/Podman compose deployment for local installation."
    info "Keep the Workbench UI enabled; the existing UI default is port 8888."
    info "Use the bundled infrastructure defaults: Cassandra, Qdrant, Garage, and RabbitMQ/Pulsar as offered."
    if [[ -n "$AUTH_TOKEN" ]]; then
        info "For IAM/auth, use token/bootstrap-token mode when offered."
        info "Admin/bootstrap API key to enter if asked: $AUTH_TOKEN"
    else
        info "For IAM/auth, use token/bootstrap-token mode when offered and paste the API key saved by this installer."
    fi
    if [[ "$LLM_MODE" == "ollama" ]]; then
        info "For LLMs, choose Ollama or an OpenAI-compatible endpoint and use $OLLAMA_BASE_URL_VALUE."
    elif [[ "$LLM_MODE" == "openai" ]]; then
        info "For LLMs, choose OpenAI/OpenAI-compatible and use $OPENAI_BASE_URL_VALUE."
    else
        info "You can skip LLM configuration now and add it later in the Workbench."
    fi
}

run_config_generator() {
    if [[ -n "$USE_EXISTING_COMPOSE" ]]; then
        return
    fi

    mkdir -p "$INSTALL_DIR"

    if [[ -f "$INSTALL_DIR/deploy.zip" ]]; then
        if confirm "Existing deploy.zip found in $INSTALL_DIR. Reuse it and skip the config wizard?" 1; then
            info "Using existing deployment archive: $INSTALL_DIR/deploy.zip"
            return
        fi
    fi

    show_config_guidance

    if ! confirm "Start the TrustGraph config wizard now?" 1; then
        die "Config generation cancelled."
    fi

    say "Running TrustGraph config generator"
    (
        cd "$INSTALL_DIR"
        TRUSTGRAPH_TOKEN="$AUTH_TOKEN" \
        TRUSTGRAPH_BOOTSTRAP_TOKEN="$AUTH_TOKEN" \
        OPENAI_TOKEN="$OPENAI_TOKEN_VALUE" \
        OPENAI_BASE_URL="$OPENAI_BASE_URL_VALUE" \
        OLLAMA_HOST="$OLLAMA_BASE_URL_VALUE" \
        OLLAMA_BASE_URL="$OLLAMA_BASE_URL_VALUE" \
        OLLAMA_MODEL="$OLLAMA_MODEL" \
        OLLAMA_EMBEDDINGS_MODEL="$OLLAMA_EMBEDDINGS_MODEL" \
        NLTK_DATA="$NLTK_DATA_DIR${NLTK_DATA:+:$NLTK_DATA}" \
        TIKTOKEN_CACHE_DIR="$TIKTOKEN_CACHE_DIR_VALUE" \
        npx @trustgraph/config
    )
}

find_compose_file() {
    if [[ -n "$USE_EXISTING_COMPOSE" ]]; then
        [[ -f "$USE_EXISTING_COMPOSE" ]] || die "Compose file does not exist: $USE_EXISTING_COMPOSE"
        printf '%s\n' "$USE_EXISTING_COMPOSE"
        return
    fi

    local deploy_zip="$INSTALL_DIR/deploy.zip"
    local unpack_dir="$INSTALL_DIR/deploy"

    [[ -f "$deploy_zip" ]] || die "The config generator did not create $deploy_zip"

    rm -rf "$unpack_dir"
    mkdir -p "$unpack_dir"
    unzip -oq "$deploy_zip" -d "$unpack_dir"

    local compose_file
    compose_file="$(find "$unpack_dir" "$INSTALL_DIR" \
        \( -name 'docker-compose.yaml' -o -name 'docker-compose.yml' -o -name 'compose.yaml' -o -name 'compose.yml' \) \
        -type f | head -n 1)"

    [[ -n "$compose_file" ]] || die "Could not find a compose file in $deploy_zip"
    printf '%s\n' "$compose_file"
}

compose_dir_for() {
    local compose_file="$1"
    (cd "$(dirname "$compose_file")" && pwd -P)
}

compose_env_file_for() {
    local compose_file="$1"
    local compose_dir

    compose_dir="$(compose_dir_for "$compose_file")"
    printf '%s/.env\n' "$compose_dir"
}

write_compose_env_file() {
    local compose_file="$1"
    local compose_env_file
    local grafana_admin_password="${GF_SECURITY_ADMIN_PASSWORD:-${GRAFANA_ADMIN_PASSWORD:-$AUTH_TOKEN}}"

    [[ -n "$AUTH_TOKEN" ]] || die "TrustGraph API key is empty; cannot create compose environment."

    compose_env_file="$(compose_env_file_for "$compose_file")"
    umask 077
    {
        printf 'TRUSTGRAPH_TOKEN=%s\n' "$AUTH_TOKEN"
        printf 'TRUSTGRAPH_BOOTSTRAP_TOKEN=%s\n' "$AUTH_TOKEN"
        printf 'IAM_BOOTSTRAP_TOKEN=%s\n' "$AUTH_TOKEN"
        printf 'GF_SECURITY_ADMIN_PASSWORD=%s\n' "$grafana_admin_password"
        printf 'OLLAMA_HOST=%s\n' "$OLLAMA_BASE_URL_VALUE"
        printf 'OLLAMA_BASE_URL=%s\n' "$OLLAMA_BASE_URL_VALUE"
        printf 'OLLAMA_MODEL=%s\n' "$OLLAMA_MODEL"
        printf 'OLLAMA_EMBEDDINGS_MODEL=%s\n' "$OLLAMA_EMBEDDINGS_MODEL"
    } > "$compose_env_file"
    chmod 600 "$compose_env_file"

    info "Compose environment: $compose_env_file"
}

start_stack() {
    local compose_file="$1"
    local compose_dir
    local compose_name
    local log_file

    say "Starting TrustGraph"
    info "Compose file: $compose_file"
    write_compose_env_file "$compose_file"

    compose_dir="$(compose_dir_for "$compose_file")"
    compose_name="$(basename "$compose_file")"
    log_file="$(installer_log_file "compose-up")"
    case "$log_file" in
        /*) ;;
        *) log_file="$SCRIPT_DIR/$log_file" ;;
    esac

    (
        cd "$compose_dir"
        run_with_spinner_logged \
            "Starting TrustGraph containers" \
            "$log_file" \
            "${COMPOSE_CMD[@]}" -f "$compose_name" up -d
    )
}

http_status() {
    local url="$1"
    curl -sS -o /dev/null -w '%{http_code}' --max-time 5 "$url" 2>/dev/null || true
}

http_status_with_bearer() {
    local url="$1"
    local token="$2"

    curl -sS -o /dev/null -w '%{http_code}' --max-time 5 \
        -H "Authorization: Bearer $token" \
        "$url" 2>/dev/null || true
}

sha256_text() {
    local value="$1"

    printf '%s' "$value" | python3 -c 'import hashlib, sys; print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())'
}

repair_local_iam_api_key() {
    local compose_file="$1"
    local compose_dir
    local compose_name
    local key_hash
    local key_suffix
    local user_id
    local username
    local key_id
    local prefix
    local cql
    local log_file

    [[ -n "$compose_file" && -f "$compose_file" ]] || return 1
    [[ -n "$AUTH_TOKEN" ]] || return 1
    command_exists python3 || return 1
    [[ "${#COMPOSE_CMD[@]}" -gt 0 ]] || return 1

    key_hash="$(sha256_text "$AUTH_TOKEN")"
    key_suffix="${key_hash:0:12}"
    user_id="installer-admin-$key_suffix"
    username="installer-admin-$key_suffix"
    key_id="installer-key-$key_suffix"
    prefix="$(printf '%s' "${AUTH_TOKEN:0:7}" | tr -cd 'a-zA-Z0-9_-')"
    compose_dir="$(compose_dir_for "$compose_file")"
    compose_name="$(basename "$compose_file")"
    log_file="$(installer_log_file "iam-key-repair")"

    cql="
USE iam;
INSERT INTO iam_users (id, workspace, username, name, email, password_hash, roles, enabled, must_change_password, created)
VALUES ('$user_id', 'default', '$username', 'Installer Admin', '', 'installer-repair', {'admin'}, true, false, toTimestamp(now()));
INSERT INTO iam_users_by_username (workspace, username, user_id)
VALUES ('default', '$username', '$user_id');
INSERT INTO iam_api_keys (key_hash, id, user_id, name, prefix, expires, created, last_used)
VALUES ('$key_hash', '$key_id', '$user_id', 'installer-repair', '$prefix', null, toTimestamp(now()), null);
"

    say "Repairing local IAM API key"
    info "Adding the saved installer key to the local installer-managed IAM database."
    mkdir -p "$(dirname "$log_file")"
    if (
        cd "$compose_dir"
        printf '%s\n' "$cql" | "${COMPOSE_CMD[@]}" -f "$compose_name" exec -T cassandra cqlsh
    ) >"$log_file" 2>&1; then
        info "Local IAM API key repair completed."
        return 0
    fi

    warn "Local IAM API key repair failed. Last log lines from $log_file:"
    tail -n 40 "$log_file" >&2 || true
    return 1
}

wait_for_gateway() {
    local deadline=$((SECONDS + HEALTH_TIMEOUT))
    local next_notice=$((SECONDS + 15))
    local status=""

    say "Waiting for API gateway"
    info "Checking $API_URL for up to ${HEALTH_TIMEOUT}s."
    while (( SECONDS < deadline )); do
        status="$(http_status "$API_URL")"
        if [[ "$status" == "200" || "$status" == "401" || "$status" == "404" ]]; then
            info "API gateway is responding with HTTP $status"
            return 0
        fi
        if (( SECONDS >= next_notice )); then
            info "Still waiting; last HTTP status was ${status:-connection failed}."
            next_notice=$((SECONDS + 15))
        fi
        sleep 3
    done

    die "API gateway did not respond at $API_URL within ${HEALTH_TIMEOUT}s"
}

verify_api_key_authentication() {
    local compose_file="${1:-}"
    local deadline=$((SECONDS + AUTH_CHECK_TIMEOUT))
    local metrics_url="${API_URL%/}/api/metrics/query?query=processor_info"
    local status=""

    [[ -n "$AUTH_TOKEN" ]] || return 0

    say "Checking API key authentication"
    info "The API gateway root can return HTTP 404; that is normal. This checks an authenticated endpoint."

    while :; do
        status="$(http_status_with_bearer "$metrics_url" "$AUTH_TOKEN")"
        case "$status" in
            200)
                info "Installer API key authenticated at the API gateway."
                return 0
                ;;
            401|403)
                ;;
            "")
                ;;
            *)
                info "Authentication probe returned HTTP $status; continuing to the full health checks."
                return 0
                ;;
        esac

        (( SECONDS >= deadline )) && break
        sleep 3
    done

    if [[ "$status" == "401" || "$status" == "403" ]]; then
        if [[ -n "$compose_file" ]] && repair_local_iam_api_key "$compose_file"; then
            status="$(http_status_with_bearer "$metrics_url" "$AUTH_TOKEN")"
            if [[ "$status" == "200" ]]; then
                info "Installer API key authenticated after local IAM repair."
                return 0
            fi
        fi
        warn "The API gateway is running, but it rejected the installer API key."
        info "Configured installer API key: $AUTH_TOKEN"
        info "Saved environment: $INSTALL_DIR/trustgraph-installer.env"
        warn "This usually means compose volumes contain IAM data from an earlier install. Run ./install_trustgraph.sh --remove-all to remove the installer-managed deployment and compose volumes, then reinstall; or rerun with the original TRUSTGRAPH_TOKEN if you know it."
        return 1
    fi

    warn "Could not confirm API key authentication yet; continuing to the full health checks."
}

bootstrap_iam_if_available() {
    local bootstrap_output=""
    local log_file="$INSTALL_DIR/iam-bootstrap.log"

    if ! command_exists tg-bootstrap-iam; then
        warn "tg-bootstrap-iam is not on PATH; using the installer API key for health checks."
        return
    fi

    say "Checking IAM bootstrap"
    if bootstrap_output="$(tg-bootstrap-iam --api-url "$API_URL" 2>"$log_file")"; then
        if [[ -n "$bootstrap_output" ]]; then
            AUTH_TOKEN="$bootstrap_output"
            info "Captured the first-run admin API key from IAM bootstrap."
            write_env_file
        fi
    else
        info "IAM bootstrap did not issue a new key; this is normal for token mode or an already-bootstrapped system."
        info "Details: $log_file"
    fi
}

verify_system() {
    local verify_cmd=()

    if command_exists tg-verify-system-status; then
        verify_cmd=(tg-verify-system-status)
    elif "$PYTHON_BIN" -c 'import trustgraph.cli.verify_system_status' >/dev/null 2>&1; then
        verify_cmd=("$PYTHON_BIN" -m trustgraph.cli.verify_system_status)
    else
        say "Verifying TrustGraph health"
        info "API gateway: $API_URL"
        info "Workbench UI: $UI_URL"
        [[ "$(http_status "$API_URL")" =~ ^(200|401|404)$ ]] || die "API gateway health check failed."
        [[ "$(http_status "${UI_URL%/}/index.html")" == "200" ]] || warn "Workbench UI did not return HTTP 200 yet."
        return
    fi

    say "Verifying TrustGraph health"
    verify_cmd+=(
        --api-url "$API_URL"
        --ui-url "$UI_URL"
        --global-timeout "$HEALTH_TIMEOUT"
    )
    if [[ -n "$AUTH_TOKEN" ]]; then
        verify_cmd+=(--token "$AUTH_TOKEN")
    fi

    "${verify_cmd[@]}"
}

launch_ui() {
    if [[ "$AUTO_LAUNCH" -ne 1 ]]; then
        info "Workbench UI autolaunch disabled."
        return
    fi

    say "Opening Workbench UI"
    if command_exists open; then
        open "$UI_URL"
    elif command_exists xdg-open; then
        xdg-open "$UI_URL"
    elif command_exists wslview; then
        wslview "$UI_URL"
    else
        warn "Could not find a browser launcher. Open this URL manually: $UI_URL"
        return
    fi
    info "Workbench UI: $UI_URL"
}

print_ready_summary() {
    local auth_status="${1:-0}"

    if [[ "$auth_status" -eq 0 ]]; then
        say "TrustGraph is ready"
    else
        say "TrustGraph started with an authentication warning"
    fi
    info "Workbench UI: $UI_URL"
    info "API gateway: $API_URL"
    if [[ -n "$AUTH_TOKEN" ]]; then
        info "Admin/bootstrap API key: $AUTH_TOKEN"
    fi
    info "Saved environment: $INSTALL_DIR/trustgraph-installer.env"
}

main() {
    parse_args "$@"
    cd "$SCRIPT_DIR"
    init_colors

    print_banner
    if [[ "$REMOVE_ALL" -eq 1 ]]; then
        say "$APP_NAME guided uninstaller"
        load_saved_answers
        remove_all_installation
        return 0
    fi

    say "$APP_NAME guided installer"
    handle_existing_install
    load_saved_answers
    detect_hardware
    choose_recommendations
    print_hardware_summary

    collect_answers
    print_plan_summary

    if [[ "$DRY_RUN" -eq 1 ]]; then
        say "Dry run complete"
        return 0
    fi

    if ! confirm "Proceed with this install plan?" 1; then
        die "Install cancelled."
    fi

    preflight
    offer_ollama_model_downloads
    write_env_file
    run_all_tests
    run_config_generator

    local compose_file
    compose_file="$(find_compose_file)"
    start_stack "$compose_file"
    wait_for_gateway
    bootstrap_iam_if_available
    local auth_status=0
    local verify_status=0

    verify_api_key_authentication "$compose_file" || auth_status=$?
    if [[ "$auth_status" -eq 0 ]]; then
        verify_system || verify_status=$?
    else
        warn "Skipping authenticated health checks because the configured API key was rejected."
    fi
    launch_ui

    print_ready_summary "$auth_status"

    if [[ "$auth_status" -ne 0 ]]; then
        return "$auth_status"
    fi
    if [[ "$verify_status" -ne 0 ]]; then
        return "$verify_status"
    fi
}

if [[ "${INSTALL_TRUSTGRAPH_SOURCE_ONLY:-0}" != "1" ]]; then
    main "$@"
fi
