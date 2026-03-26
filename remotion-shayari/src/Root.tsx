import { Composition, Folder, CalculateMetadataFunction } from 'remotion';
import { ShayariVideo, getDurationInFrames, ShayariVideoProps } from './ShayariVideo';
import { LyricsVideo, getDurationInFrames as getLyricsDuration, LyricsVideoProps } from './LyricsVideo';

const calculateShayariMetadata: CalculateMetadataFunction<ShayariVideoProps> = async ({ props }) => {
  return {
    durationInFrames: getDurationInFrames(props.quote),
  };
};

const calculateLyricsMetadata: CalculateMetadataFunction<LyricsVideoProps> = async ({ props }) => {
  return {
    durationInFrames: getLyricsDuration(props.lyrics),
  };
};

export const RemotionRoot = () => {
  return (
    <>
      <Folder name="Shayari">
        <Composition
          id="ShayariVideo"
          component={ShayariVideo}
          durationInFrames={600} // Placeholder
          fps={30}
          width={1080}
          height={1920}
          defaultProps={{
            quote: "Loading...",
            author: "Unknown",
            backgroundColor: "#0a0a0a",
          }}
          calculateMetadata={calculateShayariMetadata}
        />
      </Folder>

      <Folder name="Songs">
        <Composition
          id="LyricsVideo"
          component={LyricsVideo}
          durationInFrames={600} // Placeholder, calculated from lyrics
          fps={30}
          width={1080}
          height={1920}
          defaultProps={{
            audioUrl: "",
            lyrics: [
              {
                sentence: "Example lyrics line one",
                start: 0,
                end: 2.0,
                words: [
                  { word: "Example", start: 0, end: 0.5 },
                  { word: "lyrics", start: 0.5, end: 1.0 },
                  { word: "line", start: 1.0, end: 1.5 },
                  { word: "one", start: 1.5, end: 2.0 }
                ]
              },
              {
                sentence: "Second line of example lyrics",
                start: 2.0,
                end: 4.5,
                words: [
                  { word: "Second", start: 2.0, end: 2.5 },
                  { word: "line", start: 2.5, end: 3.0 },
                  { word: "of", start: 3.0, end: 3.2 },
                  { word: "example", start: 3.2, end: 3.8 },
                  { word: "lyrics", start: 3.8, end: 4.5 }
                ]
              }
            ],
            title: "Song Title",
            artist: "Artist Name",
            backgroundColor: "#0a0a0a",
          }}
          calculateMetadata={calculateLyricsMetadata}
        />
      </Folder>
    </>
  );
};
