# Control-surface companion

*Explanation — where this project's **control / interaction** ideas come from: the
honest counterpart to the [music-theory companion](music-theory-companion.md). The
project has two intellectual halves — the musical one (that doc) and the one that says
how a player *controls* the music (this one). As there, **nothing here is novel**; the
value is in the synthesis — applying these ideas to a *generative* engine whose neutral
is a literal musical home.*

The framing used in this project's controllability work — a control surface is good
when it is **complete** (every dimension reaches its full range, including *off*) and
**faithful** (the output is exactly the controls, nothing unbidden), and its neutral
rest-state is the **home** — is a recombination of four older ideas. Each is older
than software; the honest claim is the combination, not the parts.

## "Control surface" — the term

Borrowed straight from **audio engineering**: a *control surface* is the panel of
faders and knobs that drives a mixer or DAW — and before that, the aircraft control
surfaces (aileron, rudder, elevator) that are the pilot's inputs. A synthesizer front
panel is a control surface. We mean the same thing: the set of controls that maps onto
the engine, [auto-derived here from the engine's parameters](https://github.com/galenspikes/music-generator/blob/main/generator_api.py).

## Completeness ← control theory's *controllability*

The precise ancestor of "every dimension can reach any state, including off" is
**controllability** in control theory — **Rudolf Kálmán (1960), "On the general theory
of control systems."** A system is *controllable* if its inputs can drive it from any
state to any other. A dimension with no "off" — percussion that cannot be silenced — is
formally an *uncontrollable* state: unreachable by the inputs. Kálmán's paired notion,
*observability* (can you infer the state from the outputs), is the listening side of
the same coin.

## Faithfulness ← least astonishment, natural mapping, pure functions

"Output = the controls, nothing unbidden" is several well-worn principles in one coat:

- **The principle of least astonishment** (software/UX folklore) — the system behaves
  as the user expects; surprises are defects. An engine that adds a drum groove you
  did not ask for violates it.
- **Don Norman, *The Design of Everyday Things*** — *natural mapping* (control→effect
  is obvious) and the *gulf of execution* (can the controls even express the intent).
- **Referential transparency / pure functions** (functional programming) — same
  inputs, same output, no hidden side effects. The engine's seedable determinism
  already lives here.
- **Ben Shneiderman, "Direct Manipulation" (1983, IEEE Computer)** — continuous
  representation, immediate feedback, reversible actions: the interaction-design form
  of the same demand.

## The neutral rest-state ← unity gain, the init patch, the identity element

"Everything at neutral = the home" has three exact precedents:

- **Unity gain** (audio): a fader at 0 dB passes the signal *unchanged* — the faithful
  pass-through, the "do nothing" position. The home is the unity-gain state of the
  whole instrument.
- **The init / default patch** (synthesizers): the neutral program you start from — one
  oscillator, no modulation — before you *do* anything. That is the home, exactly.
- **The identity element** (algebra): the operation that changes nothing. We met it
  from the *musical* side in [stasis and function](stasis-and-function.md); this is the
  same idea from the *control* side.

**Modular synthesis** (Moog and after) is the purest case of all three at once: nothing
sounds that you did not patch — maximal faithfulness, with silence as the honest
default.

## The stance — a controllable instrument, not generative art

There is a long tradition where the machine is *meant* to surprise you — **Brian Eno's
generative music**, and the wider algorithmic-composition field (surveyed in Nierhaus;
see the [music companion](music-theory-companion.md)). Choosing **controllable +
faithful + deterministic** places this project deliberately at the *instrument* pole,
not the *autonomous-generator* pole. That is a stance, not a discovery — and the honest
corollary is that the engine's *generative* parts (the chord-family pickers, the
voice-leading that re-voices a held chord) are exactly what currently pull it toward the
other pole, against the instrument we want.

## How to read this — the synthesis claim

None of these is new. The only thing the project adds is the **combination**: applying
*controllability* (reach every state), *least-astonishment faithfulness* (output =
input), and a *unity/identity neutral* to a **generative music engine** — so the
rest-state is not silence or an init patch but a literal, musical **home** you then
deviate from. This companion turned into a punch-list is the
[controllability audit](../design-notes/controllability-audit.md) (gaps I1–I4 of the
[gap analysis](../design-notes/gap-analysis.md)).

## See also

[Music-theory companion](music-theory-companion.md) ·
[Stasis and function](stasis-and-function.md) ·
[Controllability audit](../design-notes/controllability-audit.md) ·
[Gap analysis](../design-notes/gap-analysis.md)
