"""Performance regression guard (nice-to-have from the 2026-07 code review).

The review's target: <100ms per typical generation. Warm medians sit around
40–60ms on ordinary hardware, so the assertions below use a generous 4x
headroom (400ms median) to stay CI-noise-proof while still catching a real
regression (an accidental O(n^2), a disk read per note, a lost cache).
Medians over several runs, not single timings, keep flakiness down.

Run with ``-s`` to see the measured numbers.
"""
import statistics
import time

import generator_api as api

MEDIAN_BUDGET_S = 0.4  # review target is 0.1s; 4x headroom for slow CI

FLAT_SPEC = {"keys": "C::maj7, A::min9, D::min7, G::13", "seconds": 30,
             "seed": 1, "perc_main": "qb, eg, qc, eg",
             "perc_fill_rate": 0.3}


def _median_seconds(fn, runs: int = 7) -> float:
    fn()  # warm caches (recipes, drum map, parser) outside the measurement
    samples = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - t0)
    return statistics.median(samples)


class TestGenerationPerformance:
    def test_flat_generation_median_within_budget(self):
        med = _median_seconds(lambda: api.generate(FLAT_SPEC))
        print(f"\nflat generate median: {med * 1000:.1f}ms "
              f"(budget {MEDIAN_BUDGET_S * 1000:.0f}ms, target 100ms)")
        assert med < MEDIAN_BUDGET_S, (
            f"flat generation regressed: median {med:.3f}s "
            f"exceeds {MEDIAN_BUDGET_S}s budget")

    def test_validate_is_not_slower_than_generate(self):
        """validate() is generate() minus serialization — it must stay in the
        same league, since the editor calls it on every edit."""
        med = _median_seconds(lambda: api.validate(FLAT_SPEC))
        print(f"\nvalidate median: {med * 1000:.1f}ms")
        assert med < MEDIAN_BUDGET_S

    def test_parameter_schema_is_fast(self):
        """The UI fetches the schema at boot; keep it well under a frame
        budget's worth of work."""
        med = _median_seconds(api.parameter_schema, runs=10)
        print(f"\nparameter_schema median: {med * 1000:.1f}ms")
        assert med < 0.1
