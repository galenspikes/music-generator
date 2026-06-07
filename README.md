# Fluidsynth Music Generator

A sophisticated Python-based music generation system that creates MIDI files with advanced harmony, percussion, and SATB (Soprano, Alto, Tenor, Bass) voicing capabilities.

## 🎵 Features

### **Harmony Generation**
- **Multiple chord families**: Triads, sevenths, ninths, extended chords, chromatic mediants, quartal harmony, sus chords, lydian dominant
- **SATB voicing styles**: Block chords, counterpoint lines, arpeggiated patterns
- **Advanced voice leading**: Suspensions, anticipations, intelligent part writing
- **Custom chord recipes**: Colon notation (e.g., `C:maj7:1` for C major 7th in 1st inversion)
- **Slash / pedal bass**: append `/bass` to a colon token (e.g., `G::maj/C` for G major over a C bass); the bass can be any note, enabling pedals like `E/A`

### **Percussion System**
- **Pattern-based drums**: Complex percussion patterns with fills and interrupters
- **Staged evolution**: Percussion that evolves over time with fill rate curves
- **Humanized timing**: Velocity and timing variations for realistic performance
- **Library system**: Pre-configured patterns for different musical styles

### **Musical Styles**
- **Classical**: Counterpoint with suspensions and anticipations
- **Jazz**: Extended chords, chromatic mediants, complex progressions
- **Rock/Metal**: Driving rhythms with blast beats and fills
- **Funk**: Pocket grooves with syncopated patterns
- **Latin**: Salsa, bossa nova with clave patterns
- **Ambient**: Arpeggiated patterns with reverb

## 🚀 Quick Start

### **1. Setup Environment**
```bash
# Activate virtual environment
source activate

# Or manually activate
source venv/bin/activate
```

### **2. Generate Music**
```bash
# Simple generation
python music_generator.py --seconds 30 --out my_song

# With percussion
python music_generator.py --seconds 60 --out rock_song \
  --perc-lib library/percussion_library.json \
  --perc-main-key rock:4/4:fast

# Counterpoint style
python music_generator.py --seconds 120 --out classical \
  --satb-style counterpoint --counterpoint-step 0.25
```

### **3. Use Recipe System**
```bash
# List available recipes
python cook_song.py list

# Show recipe details
python cook_song.py show rock

# Generate a pre-configured song
python cook_song.py make rock
```

## 📁 Project Structure

```
fluidsynth/
├── output/                    # Generated content
│   ├── audio/                # WAV files (after FluidSynth rendering)
│   ├── metadata/             # JSON metadata files
│   └── midi/                 # MIDI files
├── library/                  # Library files
│   ├── percussion_library.json  # Drum patterns and mappings
│   ├── chord_recipes.py      # Custom chord definitions
│   ├── keys_presets.json     # Key progression presets
│   └── song_cookbook.py      # Pre-configured song recipes
├── SoundFonts/               # SoundFont files
│   ├── arachno.sf2
│   └── Timbres_of_Heaven.sf2
├── music_generator.py         # Main generation engine
├── cook_song.py              # Recipe system
├── play_music                # Audio rendering wrapper
├── activate                  # Environment activation script
└── config.json              # Default settings
```

## 🎼 Usage Examples

### **Basic Generation**
```bash
# 2-minute jazz piece with counterpoint
python music_generator.py \
  --mode complete \
  --chords sevenths \
  --satb-style counterpoint \
  --seconds 120 \
  --instrument jazzguitar \
  --out jazz_counterpoint
```

### **Advanced Percussion**
```bash
# Rock with staged percussion evolution
python music_generator.py \
  --seconds 180 \
  --perc-lib library/percussion_library.json \
  --perc-stages "32:rock:4/4:fast" "32:rock:4/4:halftime" \
  --perc-fill-curve "0.1:0.4" \
  --out progressive_rock
```

### **Custom Chord Progressions**
```bash
# Custom key sequence with specific chords
python music_generator.py \
  --keys "C:maj7:1,G:min7:2,Am:7:0,F:maj9:1" \
  --mode ostinato \
  --seconds 90 \
  --out custom_progression
```

## 🎚 Configuration

### **Instruments**
```bash
# Piano
--instrument piano

# Strings
--instrument strings

# Jazz guitar
--instrument jazzguitar

# Custom GM program (0-127)
--instrument 73  # Flute
```

### **Velocity Modes**
```bash
# Humanized performance
--velocity-mode-chords human --velocity-mode-drums human

# Random dynamics
--velocity-mode-chords random

# Uniform (default)
--velocity-mode-chords uniform
```

### **SATB Styles**
```bash
# Block chords (default)
--satb-style block

# Counterpoint lines
--satb-style counterpoint --counterpoint-step 0.25

# Arpeggiated patterns
--satb-style arpeggio --counterpoint-step 0.125
```

## 🥘 Recipe System

The project includes a recipe system with pre-configured musical styles:

### **Available Recipes**
```bash
python cook_song.py list
```

### **Popular Styles**
- **`rock`**: Arena rock with driving percussion
- **`jazz`**: Bebop with swing rhythms
- **`classical`**: Counterpoint with suspensions
- **`funk`**: Pocket grooves with syncopation
- **`ambient`**: Arpeggiated pads with reverb
- **`metal`**: Blast beats and complex fills

### **Custom Recipes**
Add your own styles to `library/song_cookbook.py`:
```python
"my_style": {
    "title": "My Custom Style",
    "description": "A unique musical approach",
    "args": ["--chords", "extended-chords", "--satb-style", "counterpoint"]
}
```

## 🔧 Advanced Features

### **Percussion Patterns**
```bash
# Custom drum patterns
--perc-main "qk,eh,esh,eh" --perc-interrupters "qk,er,qs,er"

# Staged evolution
--perc-stages "16:rock:4/4:fast" "16:rock:4/4:halftime"

# Fill rate curves
--perc-fill-curve "0.1:0.5"
```

### **Chord Interrupters**
```bash
# Add rhythmic variety to harmony
--chord-interrupters "ec,er,sc" "er,ec,er,sc"
--chord-fill-rate 0.2
```

### **Counterpoint Parameters**
```bash
# Suspension probability
--counterpoint-suspension-prob 0.3

# Anticipation probability  
--counterpoint-anticipation-prob 0.25

# Step size
--counterpoint-step 0.25
```

## 🎵 Audio Rendering

### **With FluidSynth**
```bash
# Install FluidSynth (macOS)
brew install fluidsynth

# Generate and play
python music_generator.py --seconds 60 --out my_song --sf2 SoundFonts/arachno.sf2
```

### **MIDI Only**
```bash
# Generate MIDI without audio
python music_generator.py --seconds 60 --out my_song --no-play
```

## 📚 Library Files

### **Percussion Library** (`library/percussion_library.json`)
- Drum pattern definitions
- GM percussion mappings
- Style-specific patterns (rock, jazz, funk, etc.)

### **Chord Recipes** (`library/chord_recipes.py`)
- Custom chord definitions
- Extended harmony options
- Inversion support

### **Key Presets** (`library/keys_presets.json`)
- Pre-configured key progressions
- Circle of fifths sequences
- Modal progressions

## 🧪 Testing

```bash
pip install -r requirements-dev.txt
python -m pytest          # runs tests/ (token-grammar golden tests)
```

The token DSL (chord + percussion tokens) is the core of the engine; see the
full **[token grammar reference](docs/token-grammar.md)**. Its behavior is
pinned by `tests/test_tokens.py` — run the tests before/after editing any parser.

## 🛠 Development

### **Adding New Patterns**
1. Edit `library/percussion_library.json`
2. Add new style definitions
3. Test with `--perc-main-key your_style:4/4:tempo`

### **Custom Chord Types**
1. Edit `library/chord_recipes.py`
2. Add new chord definitions
3. Use with colon notation: `C:your_chord:inversion`

### **New Recipes**
1. Edit `library/song_cookbook.py`
2. Add new recipe definitions
3. Test with `python cook_song.py make your_recipe`

## 🎯 Tips

### **For Best Results**
- Use `--velocity-mode-chords human` for realistic dynamics
- Combine `--satb-style counterpoint` with `--counterpoint-step 0.25` for classical feel
- Use `--perc-fill-rate 0.2` to add rhythmic variety
- Experiment with different chord families: `--chords sevenths ninths`

### **Performance**
- Longer pieces work well with `--mode complete`
- Use `--mode ostinato` for repetitive patterns
- Combine multiple chord families: `--chords triads sevenths ninths`

### **Audio Quality**
- Use high-quality SoundFonts for better audio
- Adjust `--gain` parameter for volume control
- Enable `--reverb 1 --chorus 1` for richer sound

## 📄 License

This project is for educational and creative use. The generated music is yours to use as you see fit.

## 🤝 Contributing

Feel free to add new recipes, patterns, or chord types to the library files. The system is designed to be easily extensible.

---

**Happy music making!** 🎵


