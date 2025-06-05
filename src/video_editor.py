import os
import json
import random
import time
from moviepy import VideoFileClip, CompositeVideoClip, concatenate_videoclips
from moviepy.video.fx import Resize, FadeIn, FadeOut

class MemeVideoProcessor:
    def __init__(self, confidence_threshold=0.6):
        self.confidence_threshold = confidence_threshold
        self.used_memes = set()
        self.meme_usage_times = {}
        self.MIN_MEME_INTERVAL = 25
        
    def detect_aspect_ratio(self, width, height):
        ratio = width / height
        if abs(ratio - 16/9) <= 0.1: return "16:9"
        if abs(ratio - 9/16) <= 0.1: return "9:16"
        if abs(ratio - 1.0) <= 0.1: return "1:1"
        return "custom"
    
    def should_skip_meme(self, meme_info, start_time, meme_id):
        print(f"🔍 Checking meme: {meme_id}")
        
        confidence = meme_info.get('confidence', 0.0)
        
        if confidence < self.confidence_threshold:
            print(f"⏭️ Skip - Low confidence: {confidence:.3f}")
            return True
        
        if meme_id in self.used_memes:
            print(f"⏭️ Skip - Already used: {meme_id}")
            return True
        
        for used_time in self.meme_usage_times.values():
            if abs(start_time - used_time) < self.MIN_MEME_INTERVAL:
                print(f"⏭️ Skip - Too close to previous meme: {abs(start_time - used_time):.1f}s")
                return True
        
        return False
    
    def resize_meme_fullscreen(self, meme_clip, main_clip):
        print("📐 Resizing meme to fullscreen...")
        main_w, main_h = main_clip.w, main_clip.h
        meme_w, meme_h = meme_clip.w, meme_clip.h
        
        main_ratio = main_w / main_h
        meme_ratio = meme_w / meme_h
        
        if meme_ratio > main_ratio:
            scale = main_h / meme_h
            new_w = int(meme_w * scale)
            new_h = main_h
            resized = meme_clip.with_effects([Resize((new_w, new_h))])
            x_offset = (new_w - main_w) // 2
            if x_offset > 0:
                resized = resized.cropped(x1=x_offset, x2=x_offset + main_w)
        else:
            scale = main_w / meme_w
            new_w = main_w
            new_h = int(meme_h * scale)
            resized = meme_clip.with_effects([Resize((new_w, new_h))])
            y_offset = (new_h - main_h) // 2
            if y_offset > 0:
                resized = resized.cropped(y1=y_offset, y2=y_offset + main_h)
        
        print(f"📐 Resized from {meme_w}x{meme_h} to {resized.w}x{resized.h}")
        return resized
    
    def process_meme_overlay(self, meme_clip, main_clip, start_time, end_time, confidence):
        print(f"🎭 Processing meme overlay...")
        segment_duration = end_time - start_time
        max_meme_duration = min(5.0, segment_duration)
        
        print(f"⏰ Segment: {segment_duration:.1f}s, Max meme: {max_meme_duration:.1f}s")
        
        if meme_clip.duration > max_meme_duration:
            meme_trimmed = meme_clip.subclipped(0, max_meme_duration)
            print(f"✂️ Trimmed meme from {meme_clip.duration:.1f}s to {max_meme_duration:.1f}s")
        else:
            meme_trimmed = meme_clip
        
        meme_resized = self.resize_meme_fullscreen(meme_trimmed, main_clip)
        
        opacity = self.calculate_meme_opacity(confidence)
        print(f"👻 Applying opacity: {opacity:.2f}")
        
        try:
            meme_with_opacity = meme_resized.with_opacity(opacity)
        except:
            meme_with_opacity = meme_resized
        
        fade_duration = min(0.5, meme_trimmed.duration * 0.2)
        meme_final = meme_with_opacity.with_effects([
            FadeIn(fade_duration),
            FadeOut(fade_duration)
        ])
        
        meme_final = meme_final.with_start(start_time).with_end(start_time + meme_trimmed.duration)
        meme_final = meme_final.with_position('center')
        
        print(f"✅ Meme processed: {meme_trimmed.duration:.1f}s duration")
        return meme_final
    
    def calculate_meme_opacity(self, confidence):
        if confidence >= 0.9:
            return random.uniform(0.75, 0.85)
        elif confidence >= 0.8:
            return random.uniform(0.65, 0.75)
        elif confidence >= 0.7:
            return random.uniform(0.55, 0.65)
        else:
            return random.uniform(0.45, 0.55)
    
    def safe_close_clip(self, clip):
        try:
            if hasattr(clip, 'close') and clip is not None:
                clip.close()
        except:
            pass
    
    def process_meme_video(self, main_video_path, meme_map_path, output_path, assets_dir="assets/brolls"):
        print(f"🎬 Loading main video: {main_video_path}")
        base_clip = VideoFileClip(main_video_path)
        
        main_aspect = self.detect_aspect_ratio(base_clip.w, base_clip.h)
        print(f"📹 Main video: {base_clip.w}x{base_clip.h}, {base_clip.duration:.1f}s, {main_aspect}")
        print(f"🎯 Confidence threshold: {self.confidence_threshold}")
        
        print(f"📋 Loading meme mappings: {meme_map_path}")
        with open(meme_map_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            mappings = data.get('broll_mappings', data) if isinstance(data, dict) else data
        
        final_clips = [base_clip]
        processed_count = 0
        skipped_count = 0
        meme_clips_to_close = []
        
        print(f"🎭 Processing {len(mappings)} meme mappings...")
        
        for i, mapping in enumerate(mappings):
            meme_clip = None
            try:
                print(f"\n🎯 Processing meme {i+1}/{len(mappings)}")
                
                meme_info = mapping.get("broll", {})
                meme_type = meme_info.get("type", "unknown")
                
                if meme_type != "meme":
                    print(f"⏭️ Skip - Not a meme: {meme_type}")
                    skipped_count += 1
                    continue
                
                start_time = mapping.get("start", 0)
                if start_time < 10:
                    print(f"⏭️ Skip - Meme in first 10 seconds: {start_time:.1f}s")
                    skipped_count += 1
                    continue
                end_time = mapping.get("end", 5)
                meme_id = meme_info.get("id")
                confidence = meme_info.get("confidence", 0)
                
                print(f"📝 Meme: {meme_id}, Confidence: {confidence:.3f}")
                print(f"⏰ Time: {start_time:.1f}s-{end_time:.1f}s")
                
                if start_time >= base_clip.duration or end_time > base_clip.duration:
                    print(f"⏭️ Skip - Invalid timing")
                    skipped_count += 1
                    continue
                
                if self.should_skip_meme(meme_info, start_time, meme_id):
                    skipped_count += 1
                    continue
                
                meme_path = os.path.join(assets_dir, f"{meme_id}.mp4")
                if not os.path.exists(meme_path):
                    print(f"❌ Missing meme file: {meme_path}")
                    skipped_count += 1
                    continue
                
                print(f"📂 Loading meme: {meme_path}")
                meme_clip = VideoFileClip(meme_path)
                meme_clips_to_close.append(meme_clip)
                
                processed_clip = self.process_meme_overlay(
                    meme_clip, base_clip, start_time, end_time, confidence
                )
                
                final_clips.append(processed_clip)
                
                self.used_memes.add(meme_id)
                self.meme_usage_times[meme_id] = start_time
                
                processed_count += 1
                print(f"✅ Meme added successfully")
                
            except Exception as e:
                print(f"❌ Error processing meme {i+1}: {e}")
                skipped_count += 1
                if meme_clip:
                    self.safe_close_clip(meme_clip)
                continue
        
        print(f"\n📊 Processing Summary:")
        print(f"✅ Processed: {processed_count} memes")
        print(f"⏭️ Skipped: {skipped_count}")
        print(f"🎭 Used memes: {len(self.used_memes)}")
        
        print("\n🔄 Creating final composite...")
        final_video = CompositeVideoClip(final_clips)
        final_video = final_video.with_duration(base_clip.duration)
        
        print(f"💾 Exporting to: {output_path}")
        try:
            final_video.write_videofile(
                output_path,
                fps=base_clip.fps,
                codec='libx264',
                bitrate='8000k',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                logger=None
            )
            print("✅ Export successful!")
            
        except Exception as e:
            print(f"⚠️ Export with audio failed: {e}")
            print("🔄 Trying without audio...")
            
            try:
                final_video_no_audio = final_video.without_audio()
                final_video_no_audio.write_videofile(
                    output_path,
                    fps=base_clip.fps,
                    codec='libx264',
                    bitrate='8000k',
                    logger=None
                )
                print("✅ Export without audio successful!")
                self.safe_close_clip(final_video_no_audio)
                
            except Exception as e2:
                print(f"❌ Export failed: {e2}")
                raise e2
        
        print("🧹 Cleaning up...")
        try:
            self.safe_close_clip(base_clip)
            self.safe_close_clip(final_video)
            for clip in meme_clips_to_close:
                self.safe_close_clip(clip)
            for clip in final_clips[1:]:
                self.safe_close_clip(clip)
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
        
        print(f"🏆 Meme video processing complete!")
        return {
            'processed': processed_count,
            'skipped': skipped_count,
            'used_memes': len(self.used_memes),
            'output_path': output_path
        }

def main():
    print("🚀 Starting Meme Video Processor...")
    
    config = {
        'main_video_path': "output/sample3_with_eng_subs.mp4",
        'meme_map_path': "data/subtitles/sample3_words_broll_map.json",
        'output_path': "output/sample3_meme_final.mp4",
        'assets_dir': "assets/brolls",
        'confidence_threshold': 0.6
    }
    
    print("📁 Creating output directory...")
    os.makedirs(os.path.dirname(config['output_path']), exist_ok=True)
    
    processor = MemeVideoProcessor(confidence_threshold=config['confidence_threshold'])
    
    print("🎬 Starting processing...")
    result = processor.process_meme_video(
        main_video_path=config['main_video_path'],
        meme_map_path=config['meme_map_path'],
        output_path=config['output_path'],
        assets_dir=config['assets_dir']
    )
    
    print(f"\n🎉 Final Result: {result}")
    print("🎭 Used memes:", list(processor.used_memes))

if __name__ == "__main__":
    main()