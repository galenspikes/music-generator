"""Chord recipe catalogue for the FluidSynth music generator.

Each entry maps a short recipe name to semitone offsets relative to the chord
root. The lists stay minimal so voicing logic can choose inversions, drop
notes, or extend as needed. Categories are grouped with comments for quick
reference and editing.
"""

CHORD_RECIPES: dict[str, list[int]] = {
    # =========================
    # Common-practice harmony
    # =========================

    # Triads
    "maj": [0, 4, 7],  # Major triad
    "min": [0, 3, 7],  # Minor triad
    "dim": [0, 3, 6],  # Diminished triad
    "aug": [0, 4, 8],  # Augmented triad

    # Sevenths
    "7": [0, 4, 7, 10],  # Dominant 7
    "maj7": [0, 4, 7, 11],  # Major 7
    "min7": [0, 3, 7, 10],  # Minor 7
    "mmaj7": [0, 3, 7, 11],  # Minor-major 7
    "hdim7": [0, 3, 6, 10],  # Half-diminished 7 (ø7)
    "m7b5": [0, 3, 6, 10],  # Alias: half-diminished 7
    "wdim7": [0, 3, 6, 9],  # Fully diminished 7 (°7)
    "dim7": [0, 3, 6, 9],  # Alias: fully diminished 7

    # Suspended chords
    "sus2": [0, 2, 7],  # sus2 triad
    "sus4": [0, 5, 7],  # sus4 triad
    "sus2add7": [0, 2, 7, 10],  # sus2 with b7
    "sus4add7": [0, 5, 7, 10],  # sus4 with b7

    # Add chords (major quality)
    "majadd6": [0, 4, 7, 9],  # add6 / add13
    "majadd9": [0, 4, 7, 14],  # add9
    "majaddb9": [0, 4, 7, 13],  # add♭9
    "majadd#9": [0, 4, 7, 15],  # add♯9
    "majadd11": [0, 4, 7, 17],  # add11
    "majadd#11": [0, 4, 7, 18],  # add♯11
    "majaddb13": [0, 4, 7, 20],  # add♭13
    "majadd13": [0, 4, 7, 21],  # add13
    "maj7add9": [0, 4, 7, 11, 14],  # maj7 with added 9 (alias of maj9)

    # Add chords (minor quality)
    "minadd6": [0, 3, 7, 9],  # m(add6)
    "minadd9": [0, 3, 7, 14],  # m(add9)
    "minadd11": [0, 3, 7, 17],  # m(add11)

    # Extended chords (dominant/major/minor)
    "9": [0, 4, 7, 10, 14],  # Dominant 9
    "maj9": [0, 4, 7, 11, 14],  # Major 9
    "min9": [0, 3, 7, 10, 14],  # Minor 9
    "11": [0, 4, 7, 10, 14, 17],  # Dominant 11
    "13": [0, 4, 7, 10, 14, 21],  # Dominant 13
    "min11": [0, 3, 7, 10, 14, 17],  # Minor 11
    "min13": [0, 3, 7, 10, 14, 21],  # Minor 13

    # Altered dominant palette
    "7b5": [0, 4, 6, 10],  # 7♭5
    "7#5": [0, 4, 8, 10],  # 7♯5
    "7b9": [0, 4, 7, 10, 13],  # 7♭9
    "7#9": [0, 4, 7, 10, 15],  # 7♯9
    "7b11": [0, 4, 7, 10, 16],  # 7♭11 (a.k.a. 7♯4)
    "7#11": [0, 4, 7, 10, 18],  # 7♯11
    "7b13": [0, 4, 7, 10, 20],  # 7♭13
    "7#13": [0, 4, 7, 10, 22],  # 7♯13
    "7alt": [0, 4, 6, 8, 10, 13, 15],  # Altered collection (♭5,♯5,♭9,♯9)

    # Split-third sonorities
    "split3": [0, 3, 4, 7],  # Major/minor blend
    "maj7split3": [0, 3, 4, 7, 11],  # Maj7 with split 3rd
    "7split3": [0, 3, 4, 7, 10],  # Dom7 with split 3rd

    # Power chords
    "5": [0, 7],  # Power chord (root + fifth)
    "5add8": [0, 7, 12],  # Power chord with octave
    "5add9": [0, 7, 14],  # Power chord with added 9

    # Special functional harmony (Classical)
    "it6": [0, 4, 10],  # Italian augmented sixth
    "fr6": [0, 4, 6, 10],  # French augmented sixth
    "ger6": [0, 3, 4, 10],  # German augmented sixth
    "n6": [0, 4, 8],  # Neapolitan (as first-inversion triad on ♭II)

    # =========================
    # Jazz / Modern voicings
    # =========================
    "quartal": [0, 5, 10],  # Stacked fourths
    "quartal7": [0, 5, 10, 15],  # Four stacked fourths
    "quintal": [0, 7, 14],  # Stacked fifths
    "so_what": [0, 5, 10, 15, 20],  # "So What" quartal voicing
    "lydian_stack": [0, 4, 6, 11],  # Lydian-flavoured maj7(#11)

    # =========================
    # Famous / Iconic sonorities
    # =========================
    "tristan": [0, 6, 10, 15],  # Wagner Tristan chord (enharmonic set)
    "mystic": [0, 2, 4, 6, 9, 10],  # Scriabin mystical hexachord
    "whole_tone": [0, 2, 4, 6, 8, 10],  # Whole-tone scale segment
    "petrushka": [0, 1, 4, 7],  # Stravinsky bitonal crunch
    "augurs": [0, 1, 7, 8],  # Stravinsky "Augurs of Spring" clash

    # Messiaen-inspired sets
    "messiaen_resonance": [0, 4, 7, 10, 14, 18,
                           21],  # Resonance chord (prior to mod-12)
    "messiaen_resonance_pc": [0, 4, 7, 10, 2, 6, 9],  # Resonance reduced mod 12
    "messiaen_dom": [0, 2, 4, 6, 9, 10],  # Symmetric dominant colour

    # =========================
    # Clusters & symmetry
    # =========================
    "tone_cluster_3": [0, 1, 2],  # Three-note chromatic cluster
    "tone_cluster_4": [0, 1, 2, 3],  # Four-note chromatic cluster
    "tone_cluster_5": [0, 1, 2, 3, 4],  # Five-note chromatic cluster
    "chromatic_cluster": [0, 1, 2, 3, 4],  # Alias: five-note cluster
    "diatonic_cluster": [0, 2, 4, 5, 7],  # Pentachord inside diatonic set
    "bartok": [0, 3, 6, 9],  # Symmetric diminished tetrachord
    "octatonic_tet": [0, 3, 6, 9],  # Alias for diminished tetrachord
    "wholetone_tet": [0, 2, 4, 6],  # Four-note whole-tone subset

    # =========================
    # Extra colours / utilities
    # =========================
    "add4": [0, 4, 5, 7],  # Maj triad with added 4th (pop colour)
    "sus2add6": [0, 2, 7, 9],  # Airy guitar voicing
    "maj7#11": [0, 4, 7, 11, 18],  # Fusion/film maj7(♯11)
    "min7#11": [0, 3, 7, 10, 18],  # Modal minor (Dorian) colour
    "min7add9": [0, 3, 7, 10, 14],  # Minor7(add9)

    # Keep prior special mode name for compatibility
    "lyd-dom": [0, 4, 6, 10],  # Compact lydian dominant flavour
}
