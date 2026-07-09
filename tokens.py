"""Chord token DSL: colon chords, repetition, and key expansion.

Parses the chord mini-language — ``root[:inv][:recipe][/bass]`` colon tokens,
``*N`` repetition, ``[a,b,...]*N`` chain repetition — and expands a
comma-separated key string into a flat list of normalized key tokens via
:func:`key_roots`. Depends only on :mod:`mtheory`. See ``docs/token-grammar.md``.
"""
import re

from errors import (
    EmptyTokenError,
    InvalidBassError,
    InvalidKeyError,
    InvalidRecipeError,
    InvalidRepetitionError,
    TokenSyntaxError,
)
from mtheory import ChordDef, NOTE_TO_PC, get_chord_recipe, parse_key_name

__all__ = [
    "parse_colon_key_token",
    "parse_repetition_token",
    "parse_chain_repetition",
    "key_roots",
]


def parse_colon_key_token(token: str) -> ChordDef | None:
    """Parse root[:inv][:recipe][/bass] tokens into a chord definition.

    The optional ``/bass`` suffix sets an explicit bass pitch class (a slash
    chord / pedal), e.g. ``G::maj/C`` is a G major triad voiced over C. The
    bass note need not be a chord tone, so pedals like ``E/A`` are supported.
    An explicit ``/bass`` overrides any inversion-derived bass.
    """

    if ":" not in token:
        return None

    raw = token.strip()
    if not raw:
        raise EmptyTokenError("Empty colon chord token")

    # Optional slash-bass suffix.
    slash_bass_pc: int | None = None
    if "/" in raw:
        raw, bass_part = raw.rsplit("/", 1)
        raw = raw.strip()
        bass_part = bass_part.strip()
        if not bass_part:
            raise InvalidBassError(f"Missing bass note after '/' in token '{token}'")
        try:
            slash_bass_pc, _ = parse_key_name(bass_part)
        except Exception as exc:
            raise InvalidBassError(
                f"Bad slash bass '{bass_part}' in token '{token}'") from exc

    parts = raw.split(":")
    if len(parts) > 3:
        raise TokenSyntaxError(f"Too many ':' sections in '{token}'")

    # pad to [root, inversion?, recipe?]
    while len(parts) < 3:
        parts.append("")

    root_part, inv_part, recipe_part = (p.strip() for p in parts[:3])
    if not root_part:
        raise TokenSyntaxError(f"Missing root in colon token '{token}'")

    root_pc, is_minor = parse_key_name(root_part)

    inversion: int | None = None
    if inv_part:
        try:
            inversion = int(inv_part)
        except ValueError as exc:
            raise TokenSyntaxError(
                f"Bad inversion '{inv_part}' in colon token '{token}'") from exc

    recipe_name = recipe_part or ("min" if is_minor else "maj")
    recipe = get_chord_recipe(recipe_name)
    if recipe is None:
        raise InvalidRecipeError(
            f"Unknown chord recipe '{recipe_name}' in token '{token}'")

    if not recipe:
        raise InvalidRecipeError(f"Chord recipe '{recipe_name}' has no tones")

    pcs = tuple(sorted({(root_pc + off) % 12 for off in recipe}))
    bass_pc = None
    if inversion is not None:
        idx = inversion % len(recipe)
        bass_pc = (root_pc + recipe[idx]) % 12
    if slash_bass_pc is not None:
        bass_pc = slash_bass_pc  # explicit slash bass overrides inversion

    return ChordDef(root_pc=root_pc, pcs=pcs, bass_pc=bass_pc, label=token.strip())


def parse_repetition_token(token: str) -> tuple[str, int]:
    """Parse token with optional repetition operator *N. Returns (base_token, count)."""
    if "*" not in token:
        return token, 1

    parts = token.split("*")
    if len(parts) != 2:
        raise InvalidRepetitionError(f"Bad repetition syntax in '{token}' (use *N format)")

    base_token = parts[0].strip()
    count_str = parts[1].strip()

    if not base_token:
        raise EmptyTokenError(f"Empty base token in '{token}'")

    try:
        count = int(count_str)
    except ValueError as exc:
        raise InvalidRepetitionError(
            f"Bad repetition count '{count_str}' in '{token}'") from exc
    if count < 1:
        raise InvalidRepetitionError(f"Repetition count must be >= 1, got {count}")

    return base_token, count


def parse_chain_repetition(token: str) -> tuple[list[str], int]:
    """Parse chain repetition token like [A:1:maj*2,B:0:min*2]*3. Returns (chain_tokens, count)."""
    if not token.startswith("["):
        raise InvalidRepetitionError(f"Chain repetition must start with bracket: '{token}'")

    # Find the last *N pattern by looking for * followed by digits at the end
    match = re.search(r'\*(\d+)$', token)
    if not match:
        raise InvalidRepetitionError(
            f"Chain repetition must have *N count at the end: '{token}'")

    count_str = match.group(1)
    chain_part = token[:match.start()].strip()

    # Remove the opening bracket from chain_part
    if chain_part.startswith("["):
        chain_part = chain_part[1:]
    else:
        raise InvalidRepetitionError(f"Chain repetition must start with bracket: '{token}'")

    # Remove the closing bracket if it exists
    if chain_part.endswith("]"):
        chain_part = chain_part[:-1]

    if not chain_part:
        raise EmptyTokenError(f"Empty chain in '{token}'")

    try:
        count = int(count_str)
        if count < 1:
            raise InvalidRepetitionError(f"Chain repetition count must be >= 1, got {count}")
    except InvalidRepetitionError:
        raise
    except ValueError as exc:
        raise InvalidRepetitionError(
            f"Bad chain repetition count '{count_str}' in '{token}'") from exc

    # Parse the chain tokens (comma-separated)
    chain_tokens = [t.strip() for t in chain_part.split(",") if t.strip()]
    if not chain_tokens:
        raise EmptyTokenError(f"Empty chain in '{token}'")

    return chain_tokens, count


_KEY_SHARP_TO_FLAT = {"C#": "Db", "D#": "Eb", "F#": "Gb", "G#": "Ab", "A#": "Bb"}


def _normalize_key_token(base_token: str) -> str:
    """Validate one key token and return its canonical form.

    Colon tokens (e.g. ``C::maj7``) are validated and returned as-is. Bare roots
    are unicode-normalized, have minor markers stripped, and sharps folded to the
    project's flat spelling. Raises ValueError on an unknown key.
    """
    if ":" in base_token:
        parse_colon_key_token(base_token)  # validate early; keep original token
        return base_token
    t = base_token.replace("♭", "b").replace("♯", "#")
    low = t.lower()
    if low.endswith("min"):
        t = t[:-3]
    elif low.endswith("m"):
        t = t[:-1]
    # Lowercase the accidental too, so "GBm"/"F#M" normalize the same as
    # "Gbm"/"F#m" instead of failing NOTE_TO_PC lookup on a stray uppercase B.
    t = (t[0].upper() + t[1:].lower()) if t else t
    t = _KEY_SHARP_TO_FLAT.get(t, t)
    if t not in NOTE_TO_PC:
        raise InvalidKeyError(f"Bad key '{base_token}'")
    return t


def _emit_key_token(tok: str, out: list[str]) -> None:
    """Expand one comma token (with optional ``*N``) into normalized keys."""
    base_token, count = parse_repetition_token(tok)
    out.extend([_normalize_key_token(base_token)] * count)


def _emit_key_chain(chain_token: str, out: list[str]) -> None:
    """Expand a ``[a,b,...]*N`` chain into normalized keys."""
    chain_tokens, chain_count = parse_chain_repetition(chain_token)
    for _ in range(chain_count):
        for chain_tok in chain_tokens:
            _emit_key_token(chain_tok, out)


def key_roots(mode: str, keys_csv: str | None) -> list[str]:
    if mode == "ostinato" and keys_csv:
        # Pull [..]*N chains out to placeholders so the comma-split won't break
        # them, then expand each token through a single shared code path.
        placeholder_map: dict[str, str] = {}
        processed = keys_csv
        for i, chain in enumerate(re.findall(r'\[[^\]]+\]\*\d+', keys_csv)):
            ph = f"__CHAIN_{i}__"
            placeholder_map[ph] = chain
            processed = processed.replace(chain, ph)

        out: list[str] = []
        for tok in (t.strip() for t in processed.split(",") if t.strip()):
            chain = placeholder_map.get(tok) or (tok if tok.startswith("[") else None)
            if chain is not None:
                try:
                    _emit_key_chain(chain, out)
                except ValueError as e:
                    # Re-raise as the same type so the classification the
                    # inner parser chose (bad key, bad count, …) survives
                    # the added context.
                    raise type(e)(f"Invalid chain repetition '{chain}': {e}") from e
            else:
                _emit_key_token(tok, out)
        return out
    # default: stroll through a circle-ish order for 'mixed'/'complete'
    return ["C", "G", "D", "A", "E", "B", "Gb", "Db", "Ab", "Eb", "Bb", "F"]
