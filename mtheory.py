"""Music-theory primitives: the base layer of the generator.

Note/pitch-class tables, duration and General-MIDI instrument maps, voice
ranges and channel constants, the :class:`ChordDef` value object, key parsing,
register helpers, and the chord-recipe loader. Everything here depends only on
:mod:`errors` (the import-free exception base layer), so every other module
may import from it.
"""
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

from errors import EmptyTokenError, InvalidKeyError

# --- project folders (relative to this module, i.e. the repo root) ---
SCRIPT_DIR = Path(__file__).resolve().parent
LIB_DIR = SCRIPT_DIR / "library"
CHORD_RECIPES_PATH = LIB_DIR / "chord_recipes.py"

__all__ = [
    "ChordDef",
    "CHORD_CH",
    "DRUM_CH",
    "LEAD_CH",
    "BASS_RANGE",
    "TENOR_RANGE",
    "ALTO_RANGE",
    "SOP_RANGE",
    "VOICE_ORDER",
    "VOICE_RANGE_MAP",
    "GM_ALIASES",
    "GM_CATALOG",
    "GM_FAMILIES",
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
LEAD_CH = 4  # optional lead/hook voice (SATB stems occupy 0-3)

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

# The full General MIDI Level 1 sound set (programs 0-127), for browsing the
# whole palette. GM_ALIASES above stays the primary CLI/song vocabulary (short,
# memorable names); this catalog is additive — it's what lets a picker UI group
# and search all 128 instruments instead of the ~40 hand-picked aliases.
GM_PROGRAM_NAMES = [
    "Acoustic Grand Piano", "Bright Acoustic Piano", "Electric Grand Piano",
    "Honky-tonk Piano", "Electric Piano 1", "Electric Piano 2", "Harpsichord",
    "Clavinet",
    "Celesta", "Glockenspiel", "Music Box", "Vibraphone", "Marimba",
    "Xylophone", "Tubular Bells", "Dulcimer",
    "Drawbar Organ", "Percussive Organ", "Rock Organ", "Church Organ",
    "Reed Organ", "Accordion", "Harmonica", "Tango Accordion",
    "Acoustic Guitar (nylon)", "Acoustic Guitar (steel)",
    "Electric Guitar (jazz)", "Electric Guitar (clean)",
    "Electric Guitar (muted)", "Overdriven Guitar", "Distortion Guitar",
    "Guitar Harmonics",
    "Acoustic Bass", "Electric Bass (finger)", "Electric Bass (pick)",
    "Fretless Bass", "Slap Bass 1", "Slap Bass 2", "Synth Bass 1",
    "Synth Bass 2",
    "Violin", "Viola", "Cello", "Contrabass", "Tremolo Strings",
    "Pizzicato Strings", "Orchestral Harp", "Timpani",
    "String Ensemble 1", "String Ensemble 2", "Synth Strings 1",
    "Synth Strings 2", "Choir Aahs", "Voice Oohs", "Synth Voice",
    "Orchestra Hit",
    "Trumpet", "Trombone", "Tuba", "Muted Trumpet", "French Horn",
    "Brass Section", "Synth Brass 1", "Synth Brass 2",
    "Soprano Sax", "Alto Sax", "Tenor Sax", "Baritone Sax", "Oboe",
    "English Horn", "Bassoon", "Clarinet",
    "Piccolo", "Flute", "Recorder", "Pan Flute", "Blown Bottle",
    "Shakuhachi", "Whistle", "Ocarina",
    "Lead 1 (square)", "Lead 2 (sawtooth)", "Lead 3 (calliope)",
    "Lead 4 (chiff)", "Lead 5 (charang)", "Lead 6 (voice)",
    "Lead 7 (fifths)", "Lead 8 (bass + lead)",
    "Pad 1 (new age)", "Pad 2 (warm)", "Pad 3 (polysynth)", "Pad 4 (choir)",
    "Pad 5 (bowed)", "Pad 6 (metallic)", "Pad 7 (halo)", "Pad 8 (sweep)",
    "FX 1 (rain)", "FX 2 (soundtrack)", "FX 3 (crystal)",
    "FX 4 (atmosphere)", "FX 5 (brightness)", "FX 6 (goblins)",
    "FX 7 (echoes)", "FX 8 (sci-fi)",
    "Sitar", "Banjo", "Shamisen", "Koto", "Kalimba", "Bag pipe", "Fiddle",
    "Shanai",
    "Tinkle Bell", "Agogo", "Steel Drums", "Woodblock", "Taiko Drum",
    "Melodic Tom", "Synth Drum", "Reverse Cymbal",
    "Guitar Fret Noise", "Breath Noise", "Seashore", "Bird Tweet",
    "Telephone Ring", "Helicopter", "Applause", "Gunshot",
]

# (family name, first program, last program + 1) — the 16 standard GM families.
GM_FAMILIES = [
    ("Piano", 0, 8), ("Chromatic Percussion", 8, 16), ("Organ", 16, 24),
    ("Guitar", 24, 32), ("Bass", 32, 40), ("Strings", 40, 48),
    ("Ensemble", 48, 56), ("Brass", 56, 64), ("Reed", 64, 72),
    ("Pipe", 72, 80), ("Synth Lead", 80, 88), ("Synth Pad", 88, 96),
    ("Synth Effects", 96, 104), ("Ethnic", 104, 112),
    ("Percussive", 112, 120), ("Sound Effects", 120, 128),
]


def _gm_family(program: int) -> str:
    for name, lo, hi in GM_FAMILIES:
        if lo <= program < hi:
            return name
    return "Other"


# The full browsable catalog: [{"program": int, "name": str, "family": str}, ...]
GM_CATALOG: tuple[dict, ...] = tuple(
    {"program": i, "name": name, "family": _gm_family(i)}
    for i, name in enumerate(GM_PROGRAM_NAMES)
)

_GM_NAME_TO_PROGRAM = {entry["name"].lower(): entry["program"] for entry in GM_CATALOG}

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
        raise EmptyTokenError("Empty key name")
    is_minor = s.endswith("m")
    core = s[:-1] if is_minor else s
    core = core.replace("♭", "b").replace("♯", "#")
    if core not in NOTE_TO_PC:
        raise InvalidKeyError(f"Bad key '{kname}'")
    return NOTE_TO_PC[core], is_minor


def resolve_instrument(arg: str) -> int:
    """
    Accepts a GM program number (0-127), a friendly short alias (GM_ALIASES,
    e.g. "epiano"), or a full General MIDI instrument name (GM_CATALOG, e.g.
    "Electric Piano 1"). Returns the GM program number.
    """
    s = arg.strip()
    if s.isdigit():
        return max(0, min(127, int(s)))
    low = s.lower()
    if low in GM_ALIASES:
        return GM_ALIASES[low]
    return _GM_NAME_TO_PROGRAM.get(low, 0)  # default to Acoustic Grand (0)


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
