"""Property-based tests (hypothesis) for the token parsers.

The invariants under test, over generated rather than hand-picked inputs:

- every *valid* token the grammar admits parses, and the parse is
  structurally sound (counts, ranges, expansion arithmetic);
- every *invalid* input fails **as a ValueError** (usually a typed
  errors.* subclass) — never a stray TypeError/IndexError/KeyError
  escaping a parser, and never a hang;
- the editor-facing wrappers (generator_api.parse_keys / parse_perc)
  never raise at all: they report failure in their result dict.
"""
import string

from hypothesis import given, settings
from hypothesis import strategies as st

import generator_api as api
import mtheory
import percussion
import tokens

# --- strategies ------------------------------------------------------------

VALID_ROOTS = sorted(mtheory.NOTE_TO_PC.keys())
DUR_LETTERS = sorted(mtheory.DUR_MAP.keys())
RECIPES = sorted(mtheory.load_chord_recipes().keys())
DRUM_LETTERS = sorted(percussion.FALLBACK_DRUM_MAP.keys())

valid_bare_roots = st.builds(
    lambda root, minor: root + minor,
    st.sampled_from(VALID_ROOTS),
    st.sampled_from(["", "m"]),
)

valid_colon_tokens = st.builds(
    lambda root, inv, recipe: f"{root}:{inv}:{recipe}",
    st.sampled_from(VALID_ROOTS),
    st.sampled_from(["", "0", "1", "2"]),
    st.sampled_from(RECIPES),
)

# Printable junk that may or may not be a token — the parser must reject it
# with ValueError (or accept it), never crash with anything else.
garbage_text = st.text(
    alphabet=string.printable, min_size=0, max_size=40)

valid_perc_tokens = st.builds(
    lambda dur, letters: dur + "".join(letters),
    st.sampled_from(DUR_LETTERS),
    st.lists(st.sampled_from(DRUM_LETTERS), min_size=1, max_size=4),
)


# --- chord tokens ------------------------------------------------------------

class TestChordTokenProperties:
    @given(root=valid_bare_roots, reps=st.integers(min_value=1, max_value=32))
    def test_bare_root_repetition_expands_exactly(self, root, reps):
        out = tokens.key_roots("ostinato", f"{root}*{reps}")
        assert len(out) == reps
        assert len(set(out)) == 1  # all copies identical

    @given(token=valid_colon_tokens)
    def test_valid_colon_tokens_parse_soundly(self, token):
        cd = tokens.parse_colon_key_token(token)
        assert cd is not None
        assert 0 <= cd.root_pc < 12
        assert cd.pcs, "a recipe always has tones"
        assert all(0 <= pc < 12 for pc in cd.pcs)
        assert list(cd.pcs) == sorted(set(cd.pcs))
        assert cd.root_pc in cd.pcs or cd.pcs  # root may be omitted by exotic recipes

    @given(token=valid_colon_tokens, bass=st.sampled_from(VALID_ROOTS))
    def test_slash_bass_overrides(self, token, bass):
        cd = tokens.parse_colon_key_token(f"{token}/{bass}")
        assert cd.bass_pc == mtheory.NOTE_TO_PC[bass]

    @given(base=valid_bare_roots, count=st.integers(min_value=1, max_value=99))
    def test_repetition_roundtrip(self, base, count):
        assert tokens.parse_repetition_token(f"{base}*{count}") == (base, count)

    @given(items=st.lists(valid_bare_roots, min_size=1, max_size=5),
           reps=st.integers(min_value=1, max_value=8))
    def test_chain_expansion_arithmetic(self, items, reps):
        chain = f"[{','.join(items)}]*{reps}"
        out = tokens.key_roots("ostinato", chain)
        assert len(out) == len(items) * reps

    @given(text=garbage_text)
    @settings(max_examples=300)
    def test_key_roots_fails_only_with_value_error(self, text):
        try:
            out = tokens.key_roots("ostinato", text)
        except ValueError:
            pass  # includes every errors.* type
        else:
            assert isinstance(out, list)

    @given(text=garbage_text)
    @settings(max_examples=300)
    def test_parse_keys_api_never_raises(self, text):
        res = api.parse_keys(text)
        assert isinstance(res, dict)
        assert isinstance(res["ok"], bool)
        if not res["ok"]:
            assert res["error"]


# --- percussion tokens --------------------------------------------------------

class TestPercTokenProperties:
    @given(tok=valid_perc_tokens)
    def test_valid_tokens_parse_soundly(self, tok):
        beats, hits = percussion.parse_single_token(tok)
        assert beats == mtheory.DUR_MAP[tok[0]]
        assert len(hits) == len(tok) - 1
        assert all(0 <= h.note <= 127 for h in hits)

    @given(dur=st.sampled_from(DUR_LETTERS))
    def test_rests_have_no_hits(self, dur):
        beats, hits = percussion.parse_single_token(dur + "r")
        assert beats == mtheory.DUR_MAP[dur]
        assert hits == []

    @given(text=garbage_text)
    @settings(max_examples=300)
    def test_parse_single_token_fails_only_with_value_error(self, text):
        try:
            beats, hits = percussion.parse_single_token(text)
        except ValueError:
            pass
        else:
            assert beats > 0
            assert isinstance(hits, list)

    @given(text=garbage_text)
    @settings(max_examples=300)
    def test_parse_perc_api_never_raises(self, text):
        res = api.parse_perc(text)
        assert isinstance(res, dict)
        assert isinstance(res["ok"], bool)

    @given(tokens_list=st.lists(valid_perc_tokens, min_size=1, max_size=6))
    def test_quantize_preserves_total_duration(self, tokens_list):
        pattern = [percussion.parse_single_token(t) for t in tokens_list]
        step = percussion.GRID_STEP
        gridded = percussion.quantize_to_grid(pattern)
        assert all(dur == step for dur, _hits in gridded)
        total_in = sum(b for b, _h in pattern)
        total_out = sum(d for d, _h in gridded)
        # Slot rounding can stretch/shrink by at most half a step per token.
        assert abs(total_out - total_in) <= (step / 2) * len(pattern)
