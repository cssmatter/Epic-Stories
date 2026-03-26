import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
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

export interface ShayariVideoProps {
  quote: string;
  author: string;
  backgroundColor?: string;
  [key: string]: unknown;
}

// Configuration
const CONFIG = {
  fps: 30,
  preWaitFrames: 60, // 2 seconds before typing
  postWaitFrames: 150, // 5 seconds after typing
  typingSpeed: 4, // frames per character (adjust for faster/slower typing)
  maxWidth: 1000,
  paddingHorizontal: 80,
};

// Format quote with line breaks after commas and periods (Devanagari danda included)
const formatQuote = (text: string): string => {
  return text
    .replace(/([,.।])\s*/g, '$1\n')
    .trim();
};

export const ShayariVideo: React.FC<ShayariVideoProps> = ({
  quote,
  author,
  backgroundColor = '#0a0a0a',
}) => {
  const frame = useCurrentFrame();

  // Format the quote with line breaks
  const formattedQuote = formatQuote(quote);
  const formattedQuoteLength = formattedQuote.length;

  // Calculate timing based on formatted quote length
  const typingFrames = formattedQuoteLength * CONFIG.typingSpeed;

  // Typing progress: which character to show
  const charsToShow = Math.max(
    0,
    Math.min(formattedQuoteLength, Math.floor((frame - CONFIG.preWaitFrames) / CONFIG.typingSpeed))
  );

  // Current visible text
  const visibleQuote = formattedQuote.slice(0, charsToShow);

  // Cursor blink effect (after typing starts)
  const cursorOpacity = frame >= CONFIG.preWaitFrames && frame < CONFIG.preWaitFrames + typingFrames
    ? Math.sin(frame * 0.3) > 0 ? 1 : 0
    : 0;

  // Author fade in after quote typing completes
  const authorStartFrame = CONFIG.preWaitFrames + typingFrames;
  const authorOpacity = interpolate(
    frame,
    [authorStartFrame, authorStartFrame + 30],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  // Quote fade in after pre-wait
  const quoteOpacity = interpolate(
    frame,
    [CONFIG.preWaitFrames, CONFIG.preWaitFrames + 30],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

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
      {/* Background gradient overlay */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at 50% 40%, rgba(255, 215, 0, 0.08) 0%, transparent 60%)`,
          zIndex: 0,
        }}
      />

      {/* Quote text with typewriter effect */}
      <div
        style={{
          fontFamily: playfairFont,
          fontSize: 64,
          fontWeight: 400,
          color: '#ffffff',
          lineHeight: 1.8,
          textAlign: 'center',
          opacity: quoteOpacity,
          maxWidth: CONFIG.maxWidth,
          whiteSpace: 'pre-wrap',
          wordWrap: 'break-word',
          textShadow: '0 2px 20px rgba(0, 0, 0, 0.8)',
          zIndex: 1,
        }}
      >
        {visibleQuote}
        <span
          style={{
            color: '#ffd700',
            opacity: cursorOpacity,
            fontWeight: 'bold',
          }}
        >
          |
        </span>
      </div>

      {/* Author */}
      <div
        style={{
          fontFamily: interFont,
          fontSize: 42,
          fontWeight: 700,
          color: '#ffd700',
          textAlign: 'center',
          marginTop: 60,
          opacity: authorOpacity,
          letterSpacing: 2,
          textTransform: 'uppercase',
          zIndex: 1,
        }}
      >
        — {author}
      </div>

      {/* Bottom accent line */}
      <div
        style={{
          position: 'absolute',
          bottom: 80,
          width: 200,
          height: 3,
          backgroundColor: 'rgba(255, 215, 0, 0.5)',
          borderRadius: 2,
          opacity: authorOpacity,
        }}
      />

      {/* Watermark/logo area (optional) */}
      <div
        style={{
          position: 'absolute',
          bottom: 40,
          right: 40,
          fontFamily: interFont,
          fontSize: 24,
          color: 'rgba(255, 255, 255, 0.3)',
        }}
      >
        Epic Stories
      </div>
    </AbsoluteFill>
  );
};

// Helper function to get duration for a given quote
export const getDurationInFrames = (quote: string): number => {
  const formatted = formatQuote(quote);
  return CONFIG.preWaitFrames + (formatted.length * CONFIG.typingSpeed) + CONFIG.postWaitFrames;
};
