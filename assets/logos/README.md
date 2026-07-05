# music-generator Logo Assets

Instagram branding identity for music-generator content creation.

## Files

- **`staff-notes-color.svg`** — Primary logo with indigo accent (#6366F1 light, #818CF8 dark). Responds to system theme preference.
- **`staff-notes-monochrome.svg`** — Black monochrome variant for single-color applications (embroidery, stickers, grayscale contexts).

## Design

The mark combines musical staves with notes in depth, conveying the compositional and generative nature of the tool. Three staff lines frame three notes at different positions, creating visual rhythm and hierarchy.

- **Responsive**: Indigo accent automatically adapts to light/dark theme via CSS media queries
- **Scalable**: Pure SVG, works at any size from 24px (profile picture) to 4000px (print)
- **Simple**: Minimal linework, reads clearly at thumbnail sizes

## Usage

### Instagram Profile
- **Profile Picture**: 24×24 px minimum (use `staff-notes-color.svg`, scales infinitely)
- **Profile Header**: 150×150 px
- **Stories/Reels**: 400×400 px or larger

### Export to PNG
For PNG versions at specific sizes:
1. Open the SVG in a modern browser and screenshot at desired size
2. Use Figma: Import SVG, export as PNG at 2x/3x for different resolutions
3. Use online converter: [Convertio](https://convertio.co/svg-png/), [CloudConvert](https://cloudconvert.com/)
4. Command line (ImageMagick): `convert -density 300 -resize 400x400 staff-notes-color.svg output.png`

### Color Variants
- **Color (Primary)**: Use on light/dark backgrounds; automatically adapts via `prefers-color-scheme`
- **Monochrome**: Use for single-color requirements (embroidery, one-color print, grayscale)
- **Custom Color**: Edit the `#6366F1` (light) and `#818CF8` (dark) values in `staff-notes-color.svg` class definitions

## Brand Guidelines
- Minimum size: 24×24 px
- Clear space: 8px padding recommended
- Primary accent color: `#6366F1` (light theme), `#818CF8` (dark theme)
- Works on any background color; use monochrome version if contrast is an issue
- Never distort or rotate the mark

## Integration
To use these logos on the web:

```html
<img src="assets/logos/staff-notes-color.svg" alt="music-generator" width="64" height="64">
```

For better dark-mode support, the color version includes CSS media queries that respond to the system preference automatically.
