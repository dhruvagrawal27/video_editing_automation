import json
import os
import textwrap
from moviepy import VideoFileClip, TextClip, CompositeVideoClip
from PIL import ImageFont
from dotenv import load_dotenv

load_dotenv()

def wrap_text_properly(text, max_chars_per_line=25):
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        if len(current_line + " " + word) <= max_chars_per_line:
            if current_line:
                current_line += " " + word
            else:
                current_line = word
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)
    
    # Add extra line to prevent text cutting
    lines.append("")
    return "\n".join(lines)


def load_style(style_path):
    with open(style_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_font_size(size_option):
    """Convert size option to font size"""
    size_map = {
        "small": 30,
        "medium": 38,
        "large": 50
    }
    return size_map.get(size_option, 28)


def get_position_coords(video_size, text_size, position, padding=60):
    """Calculate position coordinates based on position option"""
    video_width, video_height = video_size
    text_width, text_height = text_size
    
    # Horizontal positioning (always center for now)
    x_pos = 'center'
    
    # Vertical positioning
    if position == "top":
        y_pos = padding
    elif position == "center":
        y_pos = (video_height - text_height) // 2
    else:  # bottom (default)
        y_pos = video_height - text_height - padding
    
    return (x_pos, y_pos)


def create_default_style():
    """Create default style configuration"""
    return {
        "font": "C:/Windows/Fonts/Arial.ttf",
        "font_size": 36,
        "text_color": "white",
        "bg_color": "black",
        "bg_opacity": 0.7,
        "padding": 8,
        "position": "bottom",
        "method": "label"
    }


def render_subtitles(video_path, subtitle_path, style_path, output_path, language="hinglish", 
                    text_color="white", shadow_color="black", shadow_opacity=0.7, 
                    position="bottom", size="medium"):
    """
    Render subtitles with customization options
    
    Args:
        video_path: Path to input video
        subtitle_path: Path to subtitle JSON file
        style_path: Path to style JSON file
        output_path: Path for output video
        language: Language key in subtitle JSON
        text_color: Color of subtitle text (default: white)
        shadow_color: Color of shadow (default: black)
        shadow_opacity: Opacity of shadow (0.0-1.0, default: 0.7)
        position: Position of subtitles ("top", "center", "bottom", default: "bottom")
        size: Size of subtitles ("small", "medium", "large", default: "medium")
    """
    
    # Load or create style
    if os.path.exists(style_path):
        style = load_style(style_path)
    else:
        style = create_default_style()
    
    # Override style with provided parameters
    style["text_color"] = text_color
    style["bg_color"] = shadow_color
    style["bg_opacity"] = shadow_opacity
    style["position"] = position
    style["font_size"] = get_font_size(size)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    video = VideoFileClip(video_path)
    clips = [video]

    with open(subtitle_path, "r", encoding="utf-8") as f:
        subtitles = json.load(f)

    for segment in subtitles:
        start = segment.get("start", 0)
        end = segment.get("end", 0)
        text = segment.get(language, "").strip()

        if not text or start == end:
            continue

        try:
            duration = end - start
            wrapped_text = wrap_text_properly(text, max_chars_per_line=25)

            # Create shadow clip with opacity
            shadow_clip = TextClip(
                text=wrapped_text,
                font_size=style.get("font_size", 36),
                color=style.get("bg_color", "black"),
                font=style.get("font", "Arial"),
                method="label"
            ).with_opacity(style.get("bg_opacity", 0.7))

            # Main text clip (no background)
            txt_clip = TextClip(
                text=wrapped_text,
                font_size=style.get("font_size", 36),
                color=style.get("text_color", "white"),
                font=style.get("font", "Arial"),
                method="label"
            )

            # Calculate position based on user preference
            shadow_pos = get_position_coords(
                video.size, 
                shadow_clip.size, 
                style.get("position", "bottom"),
                padding=80  # Increased padding to prevent cutting
            )
            
            text_pos = get_position_coords(
                video.size, 
                txt_clip.size, 
                style.get("position", "bottom"),
                padding=80
            )

            # Offset shadow slightly for better visibility
            if isinstance(shadow_pos[1], int):
                shadow_y = shadow_pos[1] + 2
                shadow_pos = (shadow_pos[0], shadow_y)

            # Apply positioning and timing
            shadow_clip = shadow_clip.with_position(shadow_pos).with_start(start).with_duration(duration)
            txt_clip = txt_clip.with_position(text_pos).with_start(start).with_duration(duration)

            clips.append(shadow_clip)
            clips.append(txt_clip)

        except Exception as e:
            print(f"Error rendering subtitle '{text}' from {start} to {end}: {e}")
            continue

    final = CompositeVideoClip(clips)
    final.write_videofile(output_path, fps=video.fps, codec="libx264", bitrate="6000k")

if __name__ == "__main__":
    # Example usage with custom parameters
    render_subtitles(
        video_path=r"C:\Users\lenovo\Downloads\videoplayback.mp4",
        subtitle_path="data/subtitles/sample3_words_translated.json",
        style_path="assets/styles/default.json",
        output_path="output/sample3_with_eng_subs.mp4",
        language="english",
        text_color="white",      # Customizable text color
        shadow_color="black",    # Customizable shadow color
        shadow_opacity=0.7,      # Customizable shadow opacity
        position="bottom",       # "top", "center", "bottom"
        size="medium"           # "small", "medium", "large"
    )
    