# Set up for development

*How to get a working dev environment, run the tests, and lint before you commit.*

## 1. Create the environment

```bash
make install
```

This creates a virtualenv at `./venv` and installs both the runtime
(`requirements.txt`) and dev (`requirements-dev.txt`) dependencies. Equivalent
to doing it by hand:

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt -r requirements-dev.txt
```

Audio rendering additionally needs FluidSynth and ffmpeg (`brew install
fluidsynth ffmpeg` on macOS). They aren't required for generating MIDI or
running the tests.

## 2. The dev loop

```bash
make test      # pytest — the safety net for every render mode + the token DSL
make lint      # ruff check (config lives in pyproject.toml)
make format    # apply ruff's safe autofixes
make check     # lint + test together — run this before committing
```

Run `make help` to list every target.

## 3. Conventions worth knowing

- **Parser changes require test verification.** Never change a parser without running the
  token tests (`tests/test_tokens.py`), and update
  [../reference/token-grammar.md](../reference/token-grammar.md) if the grammar
  changes.
- **Keep the layering intact.** The engine is split into dependency-ordered
  modules (`mtheory` → `percussion`/`tokens`/`voicing`/`midiout` → `composition` →
  `music_generator`); a module imports only layers above it, and satellites
  (`arrangement`, `fugue`, `process`, `melody`, `generator_api`) import the core,
  never the reverse. See [../explanation/architecture.md](../explanation/architecture.md).
- **Tests are the contract.** `tests/test_integration.py` renders every mode
  end-to-end; keep it green through refactors.
- **Commit hygiene.** One logical change per commit; commit/push only when asked.

## 4. Linting notes

Ruff is configured for high-signal rules (pyflakes + the pycodestyle error
classes) in `pyproject.toml`. Line length (`E501`) is intentionally not enforced.
`music_generator.py` re-exports the engine via star imports on purpose, so `F403`
is ignored there — that's the documented backward-compat seam, not an oversight.
