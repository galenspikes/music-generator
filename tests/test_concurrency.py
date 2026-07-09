"""Concurrency and hermeticity tests for the generation seam (Tier 5).

What these pin down:

- **Determinism**: the same seeded spec produces byte-identical MIDI, run
  after run, and is immune to unrelated global-RNG consumption between runs
  (the flat path uses a private ``random.Random``).
- **Isolation**: concurrent ``generate()`` calls from many threads each get
  exactly the result they'd get serially — no cross-request RNG or
  drum-map bleed.
- **Thread-safe caches**: the chord-recipe and drum-map caches survive a
  concurrent cold start.
"""
import random
import threading
from concurrent.futures import ThreadPoolExecutor

import generator_api as api
import mtheory
import percussion


SPECS = [
    {"keys": "C::maj7, A::min9", "seconds": 4, "seed": 11,
     "perc_main": "qb, eg, qc, eg"},
    {"keys": "F::maj7, D::min7, G::13", "seconds": 4, "seed": 22,
     "voicing": "dense"},
    {"keys": "Eb, Bb, Ab", "seconds": 4, "seed": 33,
     "satb_style": "counterpoint"},
    {"random_roots": True, "seconds": 4, "seed": 44,
     "perc_main": "qb, eg", "perc_interrupters": ["qk,er,qs,er"],
     "perc_fill_rate": 0.5},
]


class TestDeterminism:
    def test_same_seed_same_bytes(self):
        for spec in SPECS:
            a = api.generate(spec).midi
            b = api.generate(spec).midi
            assert a == b, f"nondeterministic for {spec}"

    def test_seeded_generation_immune_to_global_rng_noise(self):
        """Consuming the global RNG between runs must not change seeded
        output — the flat path draws from a private Random."""
        spec = SPECS[0]
        a = api.generate(spec).midi
        random.random()  # perturb the global stream
        random.seed(999)
        b = api.generate(spec).midi
        assert a == b

    def test_different_seeds_differ(self):
        base = dict(SPECS[3])
        one = api.generate({**base, "seed": 1}).midi
        two = api.generate({**base, "seed": 2}).midi
        assert one != two


class TestConcurrentGeneration:
    def test_parallel_matches_serial(self):
        """N threads × M specs: every concurrent result equals its serial
        reference — no cross-request interference."""
        serial = {i: api.generate(spec).midi for i, spec in enumerate(SPECS)}

        def run(i: int) -> tuple[int, bytes]:
            return i, api.generate(SPECS[i]).midi

        jobs = [i for i in range(len(SPECS)) for _ in range(4)]
        with ThreadPoolExecutor(max_workers=8) as pool:
            for i, midi in pool.map(run, jobs):
                assert midi == serial[i], f"spec {i} corrupted under concurrency"

    def test_concurrent_validate_and_parse(self):
        """The read-only editor endpoints are safe to hammer in parallel."""
        def work(_):
            assert api.parse_keys("C::maj7, A::min9")["ok"]
            assert api.parse_perc("qb, eg, qc")["ok"]
            assert not api.parse_keys("ZZ")["ok"]
            return True

        with ThreadPoolExecutor(max_workers=8) as pool:
            assert all(pool.map(work, range(32)))


class TestThreadSafeCaches:
    def test_recipe_cache_concurrent_cold_start(self):
        cache = mtheory.RecipeCache(mtheory.CHORD_RECIPES_PATH)
        results = []
        barrier = threading.Barrier(8)

        def load():
            barrier.wait()
            results.append(cache.load())

        threads = [threading.Thread(target=load) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(results) == 8
        first = results[0]
        assert first  # recipes actually loaded
        assert all(r is first for r in results), "one shared load expected"

    def test_drum_map_set_get_race_is_consistent(self):
        """Concurrent set/get never yields a torn or None map."""
        stop = threading.Event()
        errors_seen = []

        def reader():
            while not stop.is_set():
                m = percussion.get_drum_map()
                if not isinstance(m, dict) or "b" not in m:
                    errors_seen.append(m)

        def writer():
            while not stop.is_set():
                percussion.set_active_drum_map(None)

        threads = [threading.Thread(target=reader) for _ in range(4)]
        threads += [threading.Thread(target=writer) for _ in range(2)]
        for t in threads:
            t.start()
        stop_timer = threading.Timer(0.5, stop.set)
        stop_timer.start()
        for t in threads:
            t.join()
        stop_timer.cancel()
        assert not errors_seen
