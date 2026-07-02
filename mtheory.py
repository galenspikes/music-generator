"""Music-theory primitives: the base layer of the generator.

Note/pitch-class tables, duration and General-MIDI instrument maps, voice
ranges and channel constants, the :class:`ChordDef` value object, key parsing,
register helpers, and the chord-recipe loader. Everything here is
dependency-free with respect to the rest of the project, so every other module
may import from it.
"""
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

# --- project folders (relative to this module, i.e. the repo root) ---
SCRIPT_DIR = Path(__file__).resolve().parent
LIB_DIR = SCRIPT_DIR / "library"
CHORD_RECIPES_PATH = LIB_DIR / "chord_recipes.py"

__all__ = [
    "ChordDef",
    "CHORD_CH",
    "DRUM_CH",
    "BASS_RANGE",
    "TENOR_RANGE",
    "ALTO_RANGE",
    "SOP_RANGE",
    "VOICE_ORDER",
    "VOICE_RANGE_MAP",
    "GM_ALIASES",
    "NOTE_TO_PC",
    "DUR_MAP",
    "parse_key_name",
    "resolve_instrument",
    "clamp_to_range",
    "nearest_in_register",
    "pc",
    "load_chord_recipes",
    "get_chord_recipe",
]


@dataclass(frozen=True)
class ChordDef:
    root_pc: int
    pcs: tuple[int, ...]
    bass_pc: int | None = None
    label: str | None = None


# Channel constants
CHORD_CH = 0
DRUM_CH = 9  # GM percussion = channel 10

BASS_RANGE = (28, 55)  # E1–G3  (keeps foundation deep but not muddy)
TENOR_RANGE = (43, 67)  # G2–G4  (gives strong mid-low movement)
ALTO_RANGE = (50, 76)  # D3–E5  (bridges mid to high)
SOP_RANGE = (60, 91)  # C4–G6  (lets top voice soar and scream)

VOICE_ORDER = ("soprano", "alto", "tenor", "bass")
VOICE_RANGE_MAP = {
    "soprano": SOP_RANGE,
    "alto": ALTO_RANGE,
    "tenor": TENOR_RANGE,
    "bass": BASS_RANGE,
}

GM_ALIASES = {
    # pianos
    "piano": 0,
    "brightpiano": 1,
    "epiano": 4,
    "epiano2": 5,
    # organs
    "organ": 16,
    "rockorgan": 18,
    "churchorgan": 19,
    # guitars
    "guitar": 24,
    "distguitar": 30,
    "jazzguitar": 26,
    "nylongt": 24,
    "clav": 7,
    # basses
    "bass": 32,
    "slapbass": 36,
    "synthbass": 38,
    "pickbass": 34,
    # strings / pads / choir
    "strings": 48,
    "slowstrings": 50,
    "choir": 52,
    "vox": 54,
    "pad": 88,
    # winds / brass
    "flute": 73,
    "clarinet": 71,
    "sax": 66,
    "trumpet": 56,
    "trombone": 57,
    # mallets / percussion
    "marimba": 12,
    "vibes": 11,
    "harpsi": 6,
    # synth leads
    "lead": 80,
    "saw": 81,
    "square": 80,
    "warm": 89,
    "synthbrass": 62,
}

# -------- Key parsing --------
NOTE_TO_PC = {
    "C": 0,
    "B#": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "Fb": 4,
    "F": 5,
    "E#": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11,
    "Cb": 11,
}

DUR_MAP = {"w": 4.0, "h": 2.0, "q": 1.0, "e": 0.5, "s": 0.25, "t": 0.125}


def parse_key_name(kname: str) -> tuple[int, bool]:
    """
    Parse a key token like 'C', 'Eb', 'F#', 'Gm', 'Bbm', 'F#m'.
    Returns (pitch_class, is_minor).
    Raises ValueError on bad input.
    """
    s = kname.strip()
    if not s:
        raise ValueError("Empty key name")
    is_minor = s.endswith("m")
    core = s[:-1] if is_minor else s
    core = core.replace("♭", "b").replace("♯", "#")
    if core not in NOTE_TO_PC:
        raise ValueError(f"Bad key '{kname}'")
    return NOTE_TO_PC[core], is_minor


def resolve_instrument(arg: str) -> int:
    """
    Accepts either a GM program number (0-127) or a friendly alias string.
    Returns the GM program number.
    """
    s = arg.strip()
    if s.isdigit():
        return max(0, min(127, int(s)))
    return GM_ALIASES.get(s.lower(), 0)  # default to Acoustic Grand (0)


def clamp_to_range(n: int, lo: int, hi: int) -> int:
    while n < lo:
        n += 12
    while n > hi:
        n -= 12
    return n


def nearest_in_register(target: int, lo: int, hi: int) -> int:
    c = clamp_to_range(target, lo, hi)
    candidates = [c, c + 12, c - 12]
    return min(candidates,
               key=lambda x: (abs(x - target), 0 if lo <= x <= hi else 1e9))


def pc(name: str) -> int:
    return NOTE_TO_PC[name]


_CHORD_RECIPES_CACHE: dict[str, tuple[int, ...]] | None = None


def load_chord_recipes(
        force_reload: bool = False) -> dict[str, tuple[int, ...]]:
    """Load chord recipes from library/chord_recipes.json (cached)."""

    global _CHORD_RECIPES_CACHE
    if _CHORD_RECIPES_CACHE is not None and not force_reload:
        return _CHORD_RECIPES_CACHE

    if not CHORD_RECIPES_PATH.exists():
        _CHORD_RECIPES_CACHE = {}
        return _CHORD_RECIPES_CACHE

    module_name = "_fs_chord_recipes"
    sys.modules.pop(module_name, None)

    spec = importlib.util.spec_from_file_location(module_name,
                                                  CHORD_RECIPES_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Could not import chord recipes from {CHORD_RECIPES_PATH}")

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # pragma: no cover - developer-facing failure
        raise RuntimeError(f"Failed to load chord_recipes.py: {exc}") from exc

    data = getattr(module, "CHORD_RECIPES", {})
    if not isinstance(data, dict):
        raise RuntimeError("chord_recipes.py must define CHORD_RECIPES = {...}")

    # normalise payload to int lists
    recipes: dict[str, tuple[int, ...]] = {}
    for key, values in data.items():
        if not isinstance(key, str) or not isinstance(values, (list, tuple)):
            continue
        cleaned: list[int] = []
        for val in values:
            try:
                cleaned.append(int(val))
            except Exception:
                continue
        if cleaned:
            immutable = tuple(cleaned)
            recipes[key] = immutable
            lower_key = key.lower()
            if lower_key not in recipes:
                recipes[lower_key] = immutable

    _CHORD_RECIPES_CACHE = recipes
    return recipes


def get_chord_recipe(name: str) -> list[int] | None:
    """Fetch a chord recipe by name (case-insensitive)."""

    if not name:
        return None
    recipes = load_chord_recipes()
    recipe = recipes.get(name) or recipes.get(name.lower())
    if recipe is None:
        return None
    return list(recipe)
