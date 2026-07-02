# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""Curated capability presets for the music generator.

Each recipe is a ready-to-run set of ``music_generator.py`` arguments that shows
off one strength of the engine — dense/exotic harmony, counterpoint, fugue,
process music, the melody primitive, evolving percussion, or a finished style.
The args are pure generator args (no ``--sf2``/``--fx``), so the same recipe can
be rendered to MIDI (``music_generator.py --no-play``) *or* to audio (via
``play_music``). ``cook_song.py`` looks these up and bakes the command line;
``make gallery`` renders the ``demo``-tagged ones to committable MIDI.

Arrangements (multi-section *songs*) live in ``songs/*.yml`` and are handled by
``arrangement.py`` — these recipes are for the things a song file can't express
(fugue, process music, dense voicing, melody transforms).
"""

from __future__ import annotations

from typing import Dict, Iterable, Tuple


def _slugify(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


SONG_COOKBOOK: Dict[str, Dict[str, object]] = {
    # =====================================================================
    # Capability showcases — the things arrangements can't express.
    # =====================================================================
    "dense_colors": {
        "title": "Dense Colours",
        "description": (
            "The token DSL as a colour organ. Extended and exotic chord recipes"
            " (maj7#11, mystic, messiaen, quartal, 7alt) sounded complete across"
            " the whole register with --voicing dense — every chord tone, no"
            " voice-leading reduction."
        ),
        "args": [
            "--mode", "ostinato",
            "--keys",
            "C::maj9, A::min11, F::maj7#11, G::13, "
            "E::mystic, Ab::messiaen_resonance, Db::quartal, G::7alt, C::maj9",
            "--voicing", "dense",
            "--instrument", "slowstrings",
            "--chord-length", "w",
            "--bpm", "64",
            "--perc-main", "wr",
            "--perc-fill-rate", "0.0",
            "--velocity-mode-chords", "human",
            "--seconds", "60",
        ],
        "aliases": ["dense", "colors", "colours"],
        "tags": ["demo", "harmony", "dsl", "ambient"],
    },
    "counterpoint": {
        "title": "Counterpoint Study",
        "description": (
            "Four independent SATB lines over a ii-V cycle, with suspensions and"
            " anticipations woven in. Shows --satb-style counterpoint and the"
            " suspension/anticipation probabilities."
        ),
        "args": [
            "--mode", "ostinato",
            "--keys",
            "C::maj7, A::min7, D::min7, G::7, "
            "E::min7, A::min7, D::min7, G::7",
            "--satb-style", "counterpoint",
            "--counterpoint-step", "0.25",
            "--counterpoint-suspension-prob", "0.35",
            "--counterpoint-anticipation-prob", "0.30",
            "--instrument", "choir",
            "--chord-length", "w",
            "--bpm", "88",
            "--perc-main", "wr",
            "--perc-fill-rate", "0.0",
            "--velocity-mode-chords", "human",
            "--seconds", "70",
        ],
        "aliases": ["counter", "voice_leading"],
        "tags": ["demo", "counterpoint", "classical"],
    },
    "fugue": {
        "title": "Fugue Exposition",
        "description": (
            "A fugal exposition in D minor from a scale-degree subject: voices"
            " enter with subject then answer (up a fifth), the prior voice"
            " continues with the inverted countersubject, and a V-I cadence"
            " closes it. Organ, four voice-channels."
        ),
        "args": [
            "--fugue", "q1 e3 e5 q3 e5 e4 e3 e2 h1",
            "--melody-key", "D",
            "--melody-mode", "minor",
            "--instrument", "organ",
            "--bpm", "96",
        ],
        "aliases": ["fugal", "bach_fugue"],
        "tags": ["demo", "counterpoint", "classical", "generative"],
    },
    "process_additive": {
        "title": "Additive Process (after Glass)",
        "description": (
            "Minimalist process music: a melodic cell grows a note at a time,"
            " then contracts — watch the phrase lengthen and fold back. An arching"
            " two-register cell on vibraphone. ~2 min."
        ),
        "args": [
            "--process", "additive",
            "--process-cell", "e1 e2 e3 e5 e6 e1' e6 e5 e3 e2",
            "--process-reps", "5",
            "--melody-key", "C",
            "--melody-mode", "major",
            "--instrument", "vibes",
            "--bpm", "120",
        ],
        "aliases": ["additive", "glass"],
        "tags": ["demo", "process", "minimalism", "generative"],
    },
    "process_additive_long": {
        "title": "Additive Process — Long Form (~8 min)",
        "description": (
            "The additive process taken to full length on a complex, two-octave"
            " arching cell: fourteen notes grow one at a time and contract, an"
            " ~8-minute slow unfolding on vibraphone."
        ),
        "args": [
            "--process", "additive",
            "--process-cell",
            "e1 e2 e3 e5 e6 e1' e2' e3' e2' e1' e6 e5 e3 e2",
            "--process-reps", "11",
            "--melody-key", "C",
            "--melody-mode", "major",
            "--instrument", "vibes",
            "--bpm", "132",
        ],
        "aliases": ["additive_long", "glass_long"],
        "tags": ["process", "minimalism", "generative", "longform"],
    },
    "process_phase": {
        "title": "Phase Process (after Reich)",
        "description": (
            "Two voices loop the same cell; the follower advances one note per"
            " stage, sweeping every rhythmic alignment before snapping back to"
            " unison. Marimba, brisk pulse. ~30 s."
        ),
        "args": [
            "--process", "phase",
            "--process-cell", "s1 s2 s3 s5 s6 s5 s3 s2",
            "--process-reps", "4",
            "--melody-key", "E",
            "--melody-mode", "minor",
            "--instrument", "marimba",
            "--bpm", "160",
        ],
        "aliases": ["phase", "reich"],
        "tags": ["demo", "process", "minimalism", "generative"],
    },
    "process_phase_5min": {
        "title": "Phase Process — 5 Minutes",
        "description": (
            "The full Reich phasing sweep at ~5 minutes: each alignment held long"
            " enough to settle before the follower advances. Marimba."
        ),
        "args": [
            "--process", "phase",
            "--process-cell", "s1 s2 s3 s5 s6 s5 s3 s2",
            "--process-reps", "45",
            "--melody-key", "E",
            "--melody-mode", "minor",
            "--instrument", "marimba",
            "--bpm", "160",
        ],
        "aliases": ["phase_5", "phase_5min"],
        "tags": ["process", "minimalism", "generative", "longform"],
    },
    "process_phase_20min": {
        "title": "Phase Process — 20 Minutes",
        "description": (
            "The phasing process at full 20-minute length — every rhythmic"
            " alignment of the cell dwelt on at length, on vibraphone. A whole"
            " side of a record from eight notes."
        ),
        "args": [
            "--process", "phase",
            "--process-cell", "s1 s2 s3 s5 s6 s5 s3 s2",
            "--process-reps", "178",
            "--melody-key", "E",
            "--melody-mode", "minor",
            "--instrument", "vibes",
            "--bpm", "160",
        ],
        "aliases": ["phase_20", "phase_20min"],
        "tags": ["process", "minimalism", "generative", "longform"],
    },
    "melody_transforms": {
        "title": "Melody + Transform",
        "description": (
            "The scale-degree melody primitive riding over changes with"
            " --melody-relative chord (the motif re-fits each chord), then"
            " inverted via --melody-transform. Swap invert for retrograde or"
            " augment to hear the other fugal operations."
        ),
        "args": [
            "--mode", "ostinato",
            "--keys", "C::maj7, A::min7, F::maj7, G::7",
            "--melody", "q1 e2 e3 q5 q3 e2 q1 qr",
            "--melody-relative", "chord",
            "--melody-transform", "invert",
            "--satb-style", "block",
            "--instrument", "epiano",
            "--voice-instrument", "soprano=saw",
            "--bpm", "108",
            "--perc-main", "qb,qc,qb,qc",
            "--perc-fill-rate", "0.10",
            "--seconds", "48",
        ],
        "aliases": ["melody", "transform", "lead"],
        "tags": ["demo", "melody", "generative"],
    },
    "perc_evolution": {
        "title": "Percussion Evolution",
        "description": (
            "A drum kit built up in four obvious stages over a held vamp: kick +"
            " hats, then a backbeat snare, then busy off-beat open hats, then a"
            " full 16th-note kit with fills — and the fill rate ramps 0 -> 0.6"
            " across the piece so the groove keeps opening up."
        ),
        "args": [
            "--mode", "ostinato",
            "--keys", "A::min9, A::min9, F::maj9, G::13",
            "--instrument", "pad",
            "--chord-length", "w",
            "--perc-stages",
            "48:eb,eg,er,eg,eb,eg,er,eg",
            "48:eb,eg,ec,eg,eb,eg,ec,eg",
            "48:eb,eig,ec,eg,eb,eg,ec,eig|sb,sc,sb,sc,eg,eg",
            "48:sb,sg,sc,sg,sb,sg,sc,sg|sb,sb,sc,sc,st,st,su,sj|ec,ec,ec,ec,qj",
            "--perc-fill-curve", "0.0:0.6",
            "--velocity-mode-drums", "human",
            "--bpm", "104",
            "--seconds", "110",
        ],
        "aliases": ["percussion", "drums", "groove_evolution"],
        "tags": ["demo", "percussion", "groove"],
    },

    # =====================================================================
    # Finished-style presets — quick "press demo" grooves.
    # =====================================================================
    "salsa": {
        "title": "Salsa Brava",
        "description": (
            "Bright salsa progression with brass lead, clave-driven percussion,"
            " and lively counterpoint lines."
        ),
        "args": [
            "--mode", "mixed",
            "--keys", "C,F,G,Bb",
            "--bpm", "188",
            "--instrument", "trumpet",
            "--chords", "extended-chords", "ninths",
            "--chords-order", "roundrobin",
            "--satb-style", "counterpoint",
            "--counterpoint-step", "0.25",
            "--counterpoint-suspension-prob", "0.45",
            "--counterpoint-anticipation-prob", "0.30",
            "--perc-lib", "library/percussion_library.json",
            "--perc-main-key", "salsa:4/4:clave-3-2",
            "--perc-fill-rate", "0.35",
            "--velocity-mode-drums", "human",
            "--seconds", "90",
        ],
        "aliases": ["latin", "salsa_brava"],
        "tags": ["demo", "latin", "dance", "bright"],
    },
    "rock": {
        "title": "Arena Rock Pulse",
        "description": (
            "Driving rock anthem with distorted guitar, high-energy drums,"
            " and round-robin chord movement."
        ),
        "args": [
            "--mode", "mixed",
            "--keys", "E,A,D",
            "--bpm", "144",
            "--instrument", "distguitar",
            "--chords", "triads", "sevenths",
            "--chords-order", "roundrobin",
            "--satb-style", "block",
            "--velocity-mode-drums", "human",
            "--perc-lib", "library/percussion_library.json",
            "--perc-main-key", "rock:4/4:fast",
            "--perc-interrupter-keys", "rock:4/4:halftime",
            "--perc-fill-rate", "0.28",
            "--seconds", "75",
        ],
        "aliases": ["arena", "rock_fast"],
        "tags": ["demo", "rock", "electric", "energetic"],
    },
    "rnb": {
        "title": "Midnight R&B",
        "description": (
            "Smooth R&B vibe with electric piano, extended chords,"
            " humanized dynamics, and soulful counterpoint."
        ),
        "args": [
            "--mode", "mixed",
            "--keys", "Eb,Gb,Bb",
            "--bpm", "92",
            "--instrument", "epiano",
            "--chords", "extended-chords", "ninths", "sus",
            "--chords-order", "roundrobin",
            "--satb-style", "counterpoint",
            "--counterpoint-step", "0.50",
            "--counterpoint-suspension-prob", "0.35",
            "--counterpoint-anticipation-prob", "0.40",
            "--velocity-mode-chords", "human",
            "--velocity-mode-drums", "human",
            "--perc-lib", "library/percussion_library.json",
            "--perc-main-key", "funk:4/4:med",
            "--perc-fill-rate", "0.22",
            "--seconds", "80",
        ],
        "aliases": ["soul", "r&b"],
        "tags": ["rnb", "groove", "smooth"],
    },
    "bach_prelude": {
        "title": "Prelude in C Style",
        "description": (
            "A flowing homage to Bach's Well-Tempered Clavier Prelude in C,"
            " with steady arpeggiated motion and gentle harmonic shifts."
        ),
        "args": [
            "--mode", "complete",
            "--keys",
            "C::maj, D:3:min7, G:1:7, C::maj, A:1:min, D:3:7, G:1:maj, "
            "C:3:maj7, A::min7, D::7, G::maj, G::dim7, D:1:min, F::dim7, "
            "C:1:maj, F:3:maj7, D::min7, G::7, C::7, F::maj7, F#::dim7, "
            "G#::dim7, G::7, C:2:maj, G::9, G::7, G::7b9, C:2:maj, G::9, "
            "G::7, C::7, F:2:maj, G::7b9, C::maj",
            "--bpm", "80",
            "--instrument", "piano",
            "--chords", "triads", "sevenths", "add6",
            "--chords-order", "roundrobin",
            "--chord-length", "w",
            "--satb-style", "arpeggio",
            "--counterpoint-step", "0.25",
            "--velocity-mode-chords", "human",
            "--perc-main", "qr,qr,qr,qr",
            "--perc-fill-rate", "0.0",
            "--seconds", "150",
        ],
        "aliases": ["bach", "prelude", "baroque"],
        "tags": ["classical", "baroque", "counterpoint"],
    },
    "bach_counterpoint": {
        "title": "Prelude Counterpoint Study",
        "description": (
            "A contrapuntal exploration of the Prelude in C harmony,"
            " voiced with independent SATB motion and subtle suspensions."
        ),
        "args": [
            "--mode", "complete",
            "--keys",
            "C::maj, D:3:min7, G:1:7, C::maj, A:1:min, D:3:7, G:1:maj, "
            "C:3:maj7, A::min7, D::7, G::maj, G::dim7, D:1:min, F::dim7, "
            "C:1:maj, F:3:maj7, D::min7, G::7, C::7, F::maj7, F#::dim7, "
            "G#::dim7, G::7, C:2:maj, G::9, G::7, G::7b9, C:2:maj, G::9, "
            "G::7, C::7, F:2:maj, G::7b9, C::maj",
            "--bpm", "80",
            "--instrument", "harpsi",
            "--chords", "triads", "sevenths", "add6",
            "--chords-order", "roundrobin",
            "--chord-length", "w",
            "--satb-style", "counterpoint",
            "--counterpoint-step", "0.08",
            "--counterpoint-suspension-prob", "0.10",
            "--counterpoint-anticipation-prob", "0.25",
            "--velocity-mode-chords", "human",
            "--perc-main", "qr,qr,qr,qr",
            "--perc-fill-rate", "0.0",
            "--seconds", "150",
        ],
        "aliases": ["bach_counter", "prelude_counterpoint"],
        "tags": ["classical", "baroque", "counterpoint"],
    },
}


def recipe_keys() -> Iterable[str]:
    return SONG_COOKBOOK.keys()


def resolve_recipe(name: str) -> Tuple[str, Dict[str, object]]:
    slug = _slugify(name)
    if slug in SONG_COOKBOOK:
        return slug, SONG_COOKBOOK[slug]
    for key, payload in SONG_COOKBOOK.items():
        for alias in payload.get("aliases", []):
            if _slugify(alias) == slug:
                return key, payload
    raise KeyError(f"Unknown recipe '{name}'.")


def format_command(args: Iterable[str]) -> str:
    import shlex

    return " ".join(shlex.quote(part) for part in args)
