# Shayari Video Generator - Remotion

Generates YouTube Short videos (9:16) from shayari JSON data with typing effect.

## Features

- **Typewriter effect**: Quote appears character by character
- **Timing**: 2 second pause before typing, 5 second pause after
- **Dynamic duration**: Video length adjusts based on quote length
- **Elegant design**: Dark background with gold accents
- **Batch rendering**: Render multiple shayari videos automatically

## Project Structure

```
remotion-shayari/
├── src/
│   ├── index.tsx          # Entry point
│   ├── Root.tsx           # Composition registration
│   └── ShayariVideo.tsx   # Main composition component
├── scripts/
│   └── render-shayari.js  # Batch render script
├── public/                # Static assets (optional)
├── package.json
├── tsconfig.json
└── README.md
```

## Installation

```bash
cd remotion-shayari
npm install
```

## Usage

### Preview in Studio

```bash
npm start
```

This opens Remotion Studio at http://localhost:3000 where you can:
- Preview the composition
- Test with sample quote/author
- Adjust colors and fonts

### Render All 10 Shayari Videos

```bash
npm run build
```

Or run the script directly:

```bash
node scripts/render-shayari.js
```

This will:
1. Read `data/shayari/shayari.json`
2. Take the first 10 entries
3. Render each as a separate MP4 file in `out/` directory

### Render Single Video

```bash
npx remotion render src/index.tsx ShayariVideo output.mp4 --props='{"quote":"Your quote","author":"Author Name"}'
```

## Customization

### Timing

Edit `CONFIG` in `ShayariVideo.tsx`:

```typescript
const CONFIG = {
  fps: 30,
  preWaitFrames: 60,      // 2 seconds before typing (60 frames at 30fps)
  postWaitFrames: 150,    // 5 seconds after typing
  typingSpeed: 4,         // frames per character (lower = faster)
  maxWidth: 1000,
  paddingHorizontal: 80,
};
```

### Colors

Change `backgroundColor` prop and colors in the styles:

- Background: default `#0a0a0a`
- Quote text: `#ffffff`
- Author/accents: `#ffd700` (gold)

### Fonts

Currently uses:
- **Playfair Display**: Quote (italic serif)
- **Inter**: Author (sans-serif)

Change in `ShayariVideo.tsx` by using different Google Fonts via `@remotion/google-fonts`.

## Video Specifications

- **Aspect ratio**: 9:16 (portrait)
- **Resolution**: 1080x1920 (Full HD vertical)
- **Frame rate**: 30 fps
- **Duration**: Variable (typically 12-20 seconds depending on quote length)
- **Output**: MP4 (H.264)

## Remotion Best Practices Used

✅ Dynamic duration with `calculateMetadata`
✅ Google Fonts loading
✅ Typewriter effect using string slicing (not per-character opacity)
✅ Spring/eased animations for smooth transitions
✅ Proper sequencings and timing
✅ Text hierarchy (large quote, smaller author)
✅ 9:16 aspect ratio for YouTube Shorts / Instagram Reels
✅ Component-based architecture for reusability

## Requirements

- Node.js 18+
- npm or yarn
- Chrome Headless (downloaded automatically by Remotion)

## Troubleshooting

### Font loading errors
Make sure `@remotion/google-fonts` is installed:
```bash
npx remotion add @remotion/google-fonts
```

### JSON parse errors
Ensure `data/shayari/shayari.json` exists and is valid JSON.

### Render fails with "Composition not found"
Check that the composition ID in `Root.tsx` matches `ShayariVideo`.

## License

MIT
