import { AbsoluteFill, useCurrentFrame, Audio } from 'remotion';
import { loadFont } from '@remotion/google-fonts/Inter';
import { loadFont as loadPlayfairDisplay } from '@remotion/google-fonts/PlayfairDisplay';
import React from 'react';

// Load fonts
const { fontFamily: interFont } = loadFont('normal', {
  subsets: ['latin'],
  weights: ['400', '700'],
});
const { fontFamily: playfairFont } = loadPlayfairDisplay('normal', {
  subsets: ['latin'],
  weights: ['400', '700'],
});

export interface LyricWord {
  word: string;
  start: number;
  end: number;
}

export interface LyricSentence {
  sentence: string;
  start: number;
  end: number;
  words?: LyricWord[];  // optional, kept for compatibility
}

export interface LyricsVideoProps {
  audioUrl: string;
  lyrics: LyricSentence[];
  title: string;
  artist: string;
  backgroundColor?: string;
}

// Configuration
const CONFIG = {
  fps: 30,
  maxWidth: 900,
  paddingHorizontal: 80,
  lineHeight: 1.6,
  sentenceGap: 30,
};

const frameToSeconds = (frame: number, fps: number): number => {
  return frame / fps;
};

export const LyricsVideo: React.FC<LyricsVideoProps> = ({
  audioUrl,
  lyrics,
  title,
  artist,
  backgroundColor = '#0a0a0a',
}) => {
  const frame = useCurrentFrame();
  const currentTime = frameToSeconds(frame, CONFIG.fps);

  const sentences = lyrics;

  // Handle case with no lyrics extracted
  if (lyrics.length === 0) {
    return (
      <AbsoluteFill
        style={{
          backgroundColor,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          position: 'relative',
        }}
      >
        <AbsoluteFill
          style={{
            background: `radial-gradient(ellipse at 50% 40%, rgba(255, 215, 0, 0.08) 0%, transparent 60%)`,
            zIndex: 0,
          }}
        />
        <AbsoluteFill
          style={{
            background: `linear-gradient(180deg, ${backgroundColor} 0%, #0f0f1a 100%)`,
            opacity: 0.5,
            zIndex: 0,
          }}
        />

        {audioUrl && <Audio src={audioUrl} volume={1.0} />}

        <div style={{ textAlign: 'center', zIndex: 1 }}>
          <div style={{ fontFamily: interFont, fontSize: 36, fontWeight: 700, color: '#ffd700', marginBottom: 20 }}>
            {title || 'Unknown Title'}
          </div>
          <div style={{ fontFamily: interFont, fontSize: 24, color: 'rgba(255,255,255,0.6)', marginBottom: 40 }}>
            {artist || 'Unknown Artist'}
          </div>
          <div style={{ fontFamily: playfairFont, fontSize: 28, color: 'rgba(255,255,255,0.8)', fontStyle: 'italic' }}>
            Instrumental / No Lyrics Detected
          </div>
        </div>

        <div style={{ position: 'absolute', bottom: 40, right: 40, fontFamily: interFont, fontSize: 18, color: 'rgba(255, 255, 255, 0.2)' }}>
          Epic Stories
        </div>
      </AbsoluteFill>
    );
  }

  const firstSentenceStart = sentences[0]?.start || 0;
  const lastSentenceEnd = sentences[sentences.length - 1]?.end || 0;

  // Waiting for first sentence
  if (currentTime < firstSentenceStart) {
    return (
      <AbsoluteFill
        style={{
          backgroundColor,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          position: 'relative',
        }}
      >
        <AbsoluteFill
          style={{
            background: `radial-gradient(ellipse at 50% 40%, rgba(255, 215, 0, 0.08) 0%, transparent 60%)`,
            zIndex: 0,
          }}
        />
        <AbsoluteFill
          style={{
            background: `linear-gradient(180deg, ${backgroundColor} 0%, #0f0f1a 100%)`,
            opacity: 0.5,
            zIndex: 0,
          }}
        />

        {/* Title and Artist only while waiting */}
        <div
          style={{
            position: 'absolute',
            top: 120,
            textAlign: 'center',
            zIndex: 1,
          }}
        >
          <div
            style={{
              fontFamily: interFont,
              fontSize: 28,
              fontWeight: 700,
              color: 'rgba(255, 215, 0, 0.7)',
              letterSpacing: 3,
              textTransform: 'uppercase',
              marginBottom: 8,
            }}
          >
            {title}
          </div>
          <div
            style={{
              fontFamily: interFont,
              fontSize: 20,
              fontWeight: 400,
              color: 'rgba(255, 255, 255, 0.5)',
            }}
          >
            {artist}
          </div>
        </div>

        {/* Waiting message */}
        <div
          style={{
            fontFamily: interFont,
            fontSize: 24,
            color: 'rgba(255, 255, 255, 0.4)',
            fontStyle: 'italic',
          }}
        >
          Starting soon...
        </div>

        <Audio src={audioUrl} volume={1.0} />
      </AbsoluteFill>
    );
  }

  // After all sentences
  const isAfterLastSentence = currentTime > lastSentenceEnd + 2;
  if (isAfterLastSentence) {
    return (
      <AbsoluteFill
        style={{
          backgroundColor,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          padding: `${CONFIG.paddingHorizontal}px 80px`,
          position: 'relative',
        }}
      >
        <AbsoluteFill
          style={{
            background: `radial-gradient(ellipse at 50% 40%, rgba(255, 215, 0, 0.08) 0%, transparent 60%)`,
            zIndex: 0,
          }}
        />
        <AbsoluteFill
          style={{
            background: `linear-gradient(180deg, ${backgroundColor} 0%, #0f0f1a 100%)`,
            opacity: 0.5,
            zIndex: 0,
          }}
        />

        <div style={{ position: 'absolute', top: 100, textAlign: 'center', zIndex: 1 }}>
          <div style={{ fontFamily: interFont, fontSize: 24, fontWeight: 700, color: 'rgba(255, 215, 0, 0.7)', letterSpacing: 2, marginBottom: 6 }}>
            {title}
          </div>
          <div style={{ fontFamily: interFont, fontSize: 16, color: 'rgba(255, 255, 255, 0.5)' }}>
            {artist}
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: `${CONFIG.sentenceGap}px`, maxWidth: CONFIG.maxWidth }}>
          {sentences.map((sent, sIdx) => (
            <div
              key={sIdx}
              style={{
                fontFamily: playfairFont,
                fontSize: 44,
                fontWeight: 400,
                color: '#ffffff',
                opacity: 0.5,
                textAlign: 'center',
                lineHeight: CONFIG.lineHeight,
              }}
            >
              {sent.sentence}
            </div>
          ))}
        </div>

        <div style={{ position: 'absolute', bottom: 40, right: 40, fontFamily: interFont, fontSize: 18, color: 'rgba(255, 255, 255, 0.2)' }}>
          Epic Stories
        </div>
        <Audio src={audioUrl} volume={1.0} />
      </AbsoluteFill>
    );
  }

  // Find current sentence
  let currentSentenceIndex = -1;
  for (let i = 0; i < sentences.length; i++) {
    const sent = sentences[i];
    const nextSent = sentences[i + 1];
    const sentenceEnd = nextSent ? nextSent.start : sent.end;

    if (currentTime >= sent.start && currentTime < sentenceEnd) {
      currentSentenceIndex = i;
      break;
    }
  }

  // Fallback: if not found, use last sentence that has started
  if (currentSentenceIndex === -1) {
    for (let i = sentences.length - 1; i >= 0; i--) {
      if (currentTime >= sentences[i].start) {
        currentSentenceIndex = i;
        break;
      }
    }
  }

  const currentSentence = sentences[currentSentenceIndex];

  // Main rendering - show current sentence full-block
  return (
    <AbsoluteFill
      style={{
        backgroundColor,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        padding: `${CONFIG.paddingHorizontal}px 80px`,
        position: 'relative',
      }}
    >
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 40%, rgba(255, 215, 0, 0.08) 0%, transparent 60%)`,
          zIndex: 0,
        }}
      />
      <AbsoluteFill
        style={{
          background: `linear-gradient(180deg, ${backgroundColor} 0%, #0f0f1a 100%)`,
          opacity: 0.5,
          zIndex: 0,
        }}
      />

      <Audio src={audioUrl} volume={1.0} />

      {/* Title and Artist */}
      <div
        style={{
          position: 'absolute',
          top: 100,
          textAlign: 'center',
          zIndex: 1,
        }}
      >
        <div
          style={{
            fontFamily: interFont,
            fontSize: 24,
            fontWeight: 700,
            color: 'rgba(255, 215, 0, 0.7)',
            letterSpacing: 2,
            textTransform: 'uppercase',
            marginBottom: 6,
          }}
        >
          {title}
        </div>
        <div
          style={{
            fontFamily: interFont,
            fontSize: 16,
            fontWeight: 400,
            color: 'rgba(255, 255, 255, 0.5)',
          }}
        >
          {artist}
        </div>
      </div>

      {/* Current sentence - displayed as a whole block */}
      {currentSentence && (
        <div
          style={{
            zIndex: 1,
            marginTop: 60,
            textAlign: 'center',
          }}
        >
          <div
            style={{
              fontFamily: playfairFont,
              fontSize: 52,
              fontWeight: 700,
              color: '#ffd700',
              lineHeight: CONFIG.lineHeight,
              textShadow: '0 0 20px rgba(255, 215, 0, 0.5), 0 4px 12px rgba(0,0,0,0.5)',
              whiteSpace: 'pre-wrap',
            }}
          >
            {currentSentence.sentence}
          </div>
        </div>
      )}

      {/* Progress bar - sentence level */}
      <div
        style={{
          position: 'absolute',
          bottom: 80,
          display: 'flex',
          gap: '6px',
          zIndex: 1,
        }}
      >
        {sentences.map((sent, idx) => {
          const isCompleted = idx < currentSentenceIndex;
          const isCurrent = idx === currentSentenceIndex;
          const sentenceProgress = isCurrent
            ? ((currentTime - sent.start) / Math.max(0.001, sent.end - sent.start)) * 100
            : isCompleted
            ? 100
            : 0;

          return (
            <div
              key={idx}
              style={{
                width: 5,
                height: 50,
                backgroundColor: isCurrent
                  ? 'rgba(255, 215, 0, 0.6)'
                  : isCompleted
                  ? 'rgba(255, 255, 255, 0.3)'
                  : 'rgba(255, 255, 255, 0.1)',
                borderRadius: 2,
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              {isCurrent && (
                <div
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    height: `${Math.min(100, Math.max(0, sentenceProgress))}%`,
                    backgroundColor: 'rgba(255, 215, 0, 1)',
                    transition: 'height 0.1s linear',
                  }}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Watermark */}
      <div
        style={{
          position: 'absolute',
          bottom: 40,
          right: 40,
          fontFamily: interFont,
          fontSize: 18,
          color: 'rgba(255, 255, 255, 0.2)',
        }}
      >
        Epic Stories
      </div>
    </AbsoluteFill>
  );
};

export const getDurationInFrames = (lyrics: LyricSentence[], fps: number = 30): number => {
  if (lyrics.length === 0) return 0;
  const lastSentence = lyrics[lyrics.length - 1];
  const duration = lastSentence.end + 5;
  return Math.ceil(duration * fps);
};
