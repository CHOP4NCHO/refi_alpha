# AGENTS.md

## What This Project Is

REFI ALPHA is a Python prototype that evaluates software requirement fidelity against a codebase using LangChain agents with RAG (Retrieval-Augmented Generation). It extracts requirements from PDFs, maps codebases, and runs AI-powered evaluations.

## Running The App

```bash
# PyQt6 GUI
python -m ui_pyqt

# CLI test menu
python ux_test.py

# Requirements extractor test
python test_extractor.py
```

Install dependencies with `pip install -r requirements.txt`.

## Key Dependencies

- `langchain`, `langchain-ollama`, `langchain-core` - AI agent framework
- `docling` (IBM) - PDF processing with visual language models
- `ttkbootstrap` - Tkinter UI theming (cosmo theme)
- `PyQt6` - Alternative UI (optional)
- `pydantic` - Data models
- `python-dotenv` - Environment loading from `.env`

## Architecture

```
run_app.py               # Entry point used by PyInstaller
scripts/
  build.sh               # Linux PyInstaller build
  package_linux.sh       # Linux .deb/.rpm packaging
  build_windows.py       # Windows NSIS installer build (from Linux)
  refi-alpha.nsi         # Windows NSIS installer script
  launcher.bat.template  # Windows launcher for installed app
core/
  refi_service.py        # Orchestration layer (all UI calls this)
  model_provider.py      # LLM/VLM/Embedding provider (Ollama local or cloud)
  model_factory.py       # Creates LangChain objects from ModelConfig
  model_catalogs.py      # Model discovery per provider
  enums.py               # LlmProvider, EvaluationMode, RealEvaluation
  codebase_reader/       # Scans and indexes source files
  evaluator_agent/       # LangChain agent with RAG + tools
  requirements_extractor/# PDF -> structured requirements
  result_manager.py      # Review persistence
ui_pyqt/                 # PyQt6 UI (uses RefiService)
```

## Packaging

### Linux (PyInstaller)

```bash
./build.sh
./scripts/package_linux.sh [deb|rpm|all]
```

### Windows (NSIS installer from Linux)

Requires `nsis` installed on Linux:

```bash
# Debian/Ubuntu
sudo apt-get install nsis

# Fedora
sudo dnf install mingw64-nsis
```

The build script automatically handles Fedora's stub naming (`zlib-amd64-unicode` instead of `zlib-x86-unicode`).

Download the cached Windows dependencies into `vendor/`:

- `python-3.12.x-embed-amd64.zip` from https://www.python.org/downloads/windows/
- `get-pip.py` from https://bootstrap.pypa.io/get-pip.py

Then run:

```bash
python scripts/build_windows.py
```

Output: `dist/refi-alpha-windows-setup.exe`

The installer copies the embedded Python runtime and application source into the user's local app directory. The first run installs pip and Python dependencies directly into the embedded Python runtime.

## Non-Obvious Conventions

1. **Language split**: All source code (variables, methods, comments) is in English. All user-facing strings, prompts, and reports are in Spanish.

2. **Ollama auto-detection**: `ModelProvider` checks `localhost:11434` on init. If reachable, uses local models (`gemma4:12b`, `qwen3-embedding`). If not, falls back to cloud (Google GenAI by default).

3. **Memory management is critical**: Always call `evaluator.clear_vector_store()` in `finally` blocks after evaluation. The vector store holds the entire codebase in RAM. See `core/evaluator_agent/evaluation_runner.py:92-99`.

4. **Agent recursion limit**: Set to 25 in `evaluator.py:234`. Do not lower this without understanding the impact on complex evaluation loops.

5. **Two evaluation modes**:
   - `AGENT_AI` - Full agentic loop with RAG and tools (requires LLM + embeddings)
   - `LLM_PIPELINE` - Simpler prompt-response (requires LLM only)

6. **Accepted file extensions**: `.py`, `.kt`, `.ts`, `.tsx`, `.js`, `.jsx`, `.java`, `.go`, `.rb`, `.php`, `.c`, `.cpp`, `.h`, `.html` (defined in `core/codebase_reader/constants.py`).

7. **Default ignores**: `node_modules`, `.opencode`, `venv`, `__pycache__`, `dist`, `build`, `vendor`, all dotfiles.

8. **Environment**: `.env` file at project root. Required keys depend on provider (e.g., `GOOGLE_API_KEY`, `OPENAI_API_KEY`).

## Gotchas

- No linting, typechecking, or test framework is configured. Verify changes manually.
- `test_extractor.py` and `ux_test.py` are manual tests, not automated.
- Results are saved to `stats/performed_reviews/results.txt`.
- The `ui_pyqt/` module is autonomous from `ui/` but shares `RefiService`.
- Ollama IP is hardcoded in test scripts (not from `.env`).
