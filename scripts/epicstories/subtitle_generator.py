"""
Subtitle Generator for Epic Stories
Creates word-synced subtitles for dynamic display
"""
import os
import subprocess
import config

try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except:
    FFMPEG_EXE = "ffmpeg"


class SubtitleGenerator:
    def __init__(self):
        self.font_size = config.SUBTITLE_FONT_SIZE
        self.font_color = config.SUBTITLE_COLOR
        self.bg_color = config.SUBTITLE_BG_COLOR
        self.position_y = config.SUBTITLE_POSITION_Y
    
    def format_time_srt(self, seconds):
        """Format time for SRT (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def create_word_synced_srt(self, word_timings, output_path):
        """
        Create SRT file where each entry shows 5 words at a time
        
        Args:
            word_timings: List of dicts with 'word', 'start', 'end'
            output_path: Path to save SRT file
        """
        srt_content = ""
        words_per_subtitle = 5
        
        # Group words into chunks of 5
        for i in range(0, len(word_timings), words_per_subtitle):
            chunk = word_timings[i:i + words_per_subtitle]
            
            # Get timing from first and last word in chunk
            start = self.format_time_srt(chunk[0]['start'])
            end = self.format_time_srt(chunk[-1]['end'])
            
            # Combine words in chunk
            words = ' '.join([timing['word'] for timing in chunk])
            
            subtitle_index = (i // words_per_subtitle) + 1
            srt_content += f"{subtitle_index}\n{start} --> {end}\n{words}\n\n"
            
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        return output_path

    def burn_subtitles_srt(self, video_path, srt_path, output_path):
        """
        Burn subtitles from SRT into video using FFmpeg subtitles filter
        """
        try:
            # Shift the position using the subtitles filter arguments
            # Note: FFmpeg subtitles filter uses libass. 
            # It's harder to position vertically via filter string compared to drawtext.
            # We use force_style to set alignment and margins.
            # Alignment 2 is bottom center. MarginV shifts it up.
            
            # libass alignment codes: 1=LB, 2=CB, 3=RB, 5=LM, 6=CM, 7=RM, 9=LT, 10=CT, 11=RT
            # Alignment 2 is bottom center. MarginV shifts it up.
            margin_v = config.HEIGHT - config.SUBTITLE_POSITION_Y - 50
            
            # Using the font name configured in config.py
            font_name = config.SUBTITLE_FONT
            
            style = (
                f"FontName={font_name},FontSize={self.font_size*0.75}," # libass fontsize is different
                f"PrimaryColour={config.SUBTITLE_COLOR},Outline=1,Shadow=1,"
                f"BackColour=&H99000000,BorderStyle=4," # BorderStyle 4 is background box
                f"Alignment=2,MarginV={margin_v}"
            )
            
            # Need to escape path for FFmpeg subtitles filter (especially on Windows)
            escaped_srt = srt_path.replace('\\', '/').replace(':', '\\:')
            escaped_fontsdir = config.FONTS_DIR.replace('\\', '/').replace(':', '\\:')
            
            # filter string: subtitles=filename.srt:force_style='...':fontsdir='...'
            sub_filter = f"subtitles='{escaped_srt}':force_style='{style}':fontsdir='{escaped_fontsdir}'"
            
            cmd = [
                FFMPEG_EXE, "-y",
                "-threads", "2",
                "-i", video_path,
                "-vf", sub_filter,
                "-c:a", "copy",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return output_path
            else:
                print(f"FFmpeg subtitles error: {result.stderr}")
                return video_path
                
        except Exception as e:
            print(f"Error burning SRT subtitles: {e}")
            return video_path

    def create_subtitle_file(self, text, duration, output_path):
        # Legacy method for full scene subtitle if needed
        def format_time(seconds):
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            millis = int((seconds % 1) * 1000)
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
        
        srt_content = f"1\n{format_time(0)} --> {format_time(duration)}\n{text}\n"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        return output_path


def test_subtitles():
    """Test subtitle generator with word synced SRT"""
    generator = SubtitleGenerator()
    timings = [
        {'word': 'Discipline', 'start': 0.0, 'end': 1.0},
        {'word': 'is', 'start': 1.0, 'end': 1.5},
        {'word': 'Freedom', 'start': 1.5, 'end': 3.0},
    ]
    test_output = os.path.join(config.TEMP_DIR, "test_word_sync.srt")
    srt_path = generator.create_word_synced_srt(timings, test_output)
    print(f"Created Word-Synced SRT: {srt_path}")


if __name__ == "__main__":
    print("Testing Subtitle Generator Word-Sync...")
    test_subtitles()
