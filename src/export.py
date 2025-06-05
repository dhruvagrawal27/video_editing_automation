import os
from moviepy import VideoFileClip
from moviepy.video.fx import Resize
from datetime import datetime

def export_final_video(input_path, output_dir="data/exports", aspect_ratio="original", filename_prefix="final"):
    """
    Export video in the specified aspect ratio or keep original format.
    
    Args:
        input_path (str): Path to the input video file
        output_dir (str): Directory to save the exported video
        aspect_ratio (str): "original", "9:16", "16:9", or "1:1"
        filename_prefix (str): Prefix for the output filename
    
    Returns:
        str: Path to the exported video file
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"🚀 Loading video: {input_path}")
    video = VideoFileClip(input_path)
    original_width, original_height = video.size
    
    print(f"📐 Original resolution: {original_width}x{original_height}")
    
    # Handle original format (no resizing)
    if aspect_ratio == "original":
        output_filename = f"{filename_prefix}_original.mp4"
        output_path = os.path.join(output_dir, output_filename)
        
        print(f"💾 Exporting in original format...")
        video.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac",
            preset="medium",
            bitrate="3000k"
        )
        
        video.close()
        print(f"✅ Exported: {output_path}")
        return output_path
    
    # Handle specific aspect ratios
    aspect_configs = {
        "9:16": (1080, 1920),  # Vertical (TikTok, Reels, Shorts)
        "16:9": (1920, 1080),  # Horizontal (YouTube, standard video)
        "1:1": (1080, 1080)    # Square (Instagram feed)
    }
    
    if aspect_ratio not in aspect_configs:
        video.close()
        raise ValueError(f"Unsupported aspect ratio: {aspect_ratio}. Use: {list(aspect_configs.keys())} or 'original'")
    
    target_width, target_height = aspect_configs[aspect_ratio]
    print(f"🎯 Target resolution: {target_width}x{target_height} ({aspect_ratio})")
    
    # Resize video to target aspect ratio
    resized_video = resize_to_aspect_ratio(video, target_width, target_height)
    
    # Generate output filename
    output_filename = f"{filename_prefix}_{aspect_ratio.replace(':', 'x')}.mp4"
    output_path = os.path.join(output_dir, output_filename)
    
    print(f"💾 Exporting resized video...")
    resized_video.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        bitrate="3000k"
    )
    
    # Clean up
    video.close()
    resized_video.close()
    
    print(f"✅ Exported: {output_path}")
    return output_path


def resize_to_aspect_ratio(video, target_width, target_height):
    """
    Resize video to target aspect ratio using smart cropping/padding.
    
    Args:
        video: MoviePy VideoClip object
        target_width (int): Target width in pixels
        target_height (int): Target height in pixels
    
    Returns:
        VideoClip: Resized video clip
    """
    original_width, original_height = video.size
    original_ratio = original_width / original_height
    target_ratio = target_width / target_height
    
    print(f"🔄 Resizing from {original_width}x{original_height} to {target_width}x{target_height}")
    
    if abs(original_ratio - target_ratio) < 0.01:
        # Already close to target ratio, just resize
        return video.Resize((target_width, target_height))
    
    elif original_ratio > target_ratio:
        # Original is wider - fit by height, then crop width
        scaled = video.Resize(height=target_height)
        x_center = scaled.w // 2
        x_start = max(0, x_center - target_width // 2)
        x_end = min(scaled.w, x_start + target_width)
        return scaled.crop(x1=x_start, x2=x_end)
    
    else:
        # Original is taller - fit by width, then crop height
        scaled = video.Resize(width=target_width)
        y_center = scaled.h // 2
        y_start = max(0, y_center - target_height // 2)
        y_end = min(scaled.h, y_start + target_height)
        return scaled.crop(y1=y_start, y2=y_end)


def export_with_timestamp(input_path, output_dir="data/exports", aspect_ratio="original"):
    """
    Export video with timestamp in filename for unique identification.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename_prefix = f"final_{timestamp}"
    
    return export_final_video(
        input_path=input_path,
        output_dir=output_dir,
        aspect_ratio=aspect_ratio,
        filename_prefix=filename_prefix
    )


# Example usage and testing
if __name__ == "__main__":
    # Test with different scenarios
    input_video = "output/sample3_professional_final.mp4"  # Replace with your video path
    
    # Export in original format (default)
    try:
        result = export_final_video(input_video, aspect_ratio="original")
        print(f"Original export successful: {result}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Export in 9:16 for vertical platforms
    # try:
    #     result = export_final_video(input_video, aspect_ratio="9:16")
    #     print(f"Vertical export successful: {result}")
    # except Exception as e:
    #     print(f"Error: {e}")
    
    # Export with timestamp
    # try:
    #     result = export_with_timestamp(input_video, aspect_ratio="16:9")
    #     print(f"Timestamped export successful: {result}")
    # except Exception as e:
    #     print(f"Error: {e}")