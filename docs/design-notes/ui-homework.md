# UI homework — control surface decisions

*Fill this in however you want — sentences, fragments, examples, stream of consciousness.
The goal is to capture your instincts so the design reflects you, not defaults.*

---

## 1. The home

> The home is the instrument's idle tone — what you hear when you've touched nothing.
> Right now the candidate is: **Cmaj7, epiano, 120bpm, 8th-note pulse, everything else off.**

**1a.** Is that right? What does the home *feel* like to you — is it a pad, a pulse, a drone?
Something that could play for 20 minutes without becoming annoying?

i was saying 8th note pulse just to draw a line in the sand, but from the perspective of a new user, i would want something more dynamic. i agree, something that could play for 20 minutes without becoming annoying. that will need to be a parameter set that i am happy with, which requires me to experiment for some time before crystalizing anything. we should have a placeholder until a point that i decide on a preset/recipe that will stand as the opening number.

**1b.** Does the home have bass? (Root bass under Cmaj7 is warm and grounding. No bass is
purer but also thinner.) Where does your gut land?

i don't know, this experience should have a placeholder, but it is something that should exist.

**1c.** Does the home have dynamics — does the velocity shape at all, or is it flat (uniform)?

this would be dertermined by the preset.. see 1a

**1d.** Is BPM a home property or a deviation? (Is 120 the "neutral" and changing it a
deviation, or is tempo just a setting you pick before you start?)

irrelevant right now

---

## 2. The deviations (the antennae)

> Everything in this section should boot at zero / off and represent a dimension you
> *push away from the home.*

**2a.** List every dimension you can imagine deviating from the home. Don't filter yet —
throw them all down. (Examples: percussion, bass motion, chord quality, voicing spread,
fills, melody, register, harmonic tension, rhythm density, dynamics shape…)

this isnt how i think about it. "home" is an arbitrary position. its something that you establish. i think you are taking this far too literally. this is a music generator. from the perspective of this generator, music is sound plus time, and for the purposes of being used by a machine, this uses midi and the western 12 tone scale. it can be functional, it can be nonfunctional, it can be modal, chromatic, serial, atonal, etc.

**2b.** Now order them: which feels most *structural* (bottom of the music) to most
*textural* (surface decoration)? This will be the physical top-to-bottom on the panel.

i refuse to do this, its against the spirit

**2c.** Are there deviations you'd never use together? Deviations that imply each other?
(E.g. does a melody deviation require a certain bass deviation to make sense?)

i dont care

**2d.** Is there a deviation that *is the point* — the one you reach for most? Where does
it sit in your order?

"order" in art is stupid. you can order it of course, but it still futile at the end of the day, but not in a fatalistic way. its just a truism? how do you create order out of a subjective piece of expression or whatever? i dont know, ask an egghead.

---

## 3. Control types

> For each major antenna, what kind of control feels right?
>
> - **Toggle** — off/on, binary (e.g. bass: none/follow)
> - **Knob** — continuous 0→max (e.g. fill rate)
> - **Selector** — choose a named mode (e.g. percussion style: off / hi-hat / full kit)
> - **Combo** — a selector with a knob modifier (e.g. bass style + bass density)

**3a.** Go through your deviation list from 2a. For each one, what control type fits it?

**3b.** Are there controls that feel like they should be *hidden by default* and only appear
when you flip a "more" switch? Or should everything be visible at once?

too deep in the weeds to define now. i prefer everythign but the kitchen sink

**3c.** Is there a single "how far from home am I" macro you'd want — one knob that pulls
everything up from zero at once?

---

## 4. Groups

> The question: is it two panels (Home / Deviations), or does the deviation space have
> natural sub-groups?

**4a.** Looking at your list from 2a, do you see clusters? (Rhythm cluster? Harmonic cluster?
Melodic cluster?) Or does it feel like one flat list of antennae?

**4b.** If there are sub-groups, what are they called? Use whatever language feels natural —
not engine names (Harmony, Drums) but player names.

**4c.** Is there anything that doesn't fit in either Home or Deviations — a third kind of
thing? (Session settings? Utility controls? Something else?)

---

## 5. The opening moment

**5a.** When you open the instrument and press play — before you've touched anything — what
do you want to experience? (The home? A demo? A blank canvas?)

the home, or a user defined home preset

**5b.** The "Kiss On My List" demo idea: a recallable state that visibly *moves the controls
away from home and back.* Does that still feel right? Or is that better as a preset you
load, not the opening?

we'll talk about this later when the app actually works properly

**5c.** Should there be presets / scenes at all? Or is the instrument always just "you
building from the home"?

presets are a must, the more the better. i can't wait to get it working so i can start building them myself

---

## 6. What the surface should NOT show

> The controllability audit flagged baggage: `mode`, process/fugue controls, CLI render
> plumbing (`out`, `sf2`, `poly`, etc.). We agreed those go away.

**6a.** Anything else you never want to see on the surface?

**6b.** Is there anything in the current UI that you find yourself reaching for constantly
that should be more prominent?

---

## 7. The feel

**7a.** One or two instruments or interfaces (hardware or software) whose *control layout*
you admire. Not the sound — the layout, the logic of the surface.

u-he bazille, dm-1 drum machine

**7b.** When you imagine using this instrument for 30 minutes straight — what are your hands
doing? What are you adjusting, in what order, how often?

we arent there yet