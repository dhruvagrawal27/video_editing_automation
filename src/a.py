import os
import json
import shutil

def create_broll_mappings():
    """Map existing b-roll files to required ones in JSON"""
    
    # Your existing files
    existing_files = [
        "bhag_milkha_bhag.mp4",
        "girl_workout.mp4", 
        "glass_pouring.mp4",
        "hera_pheri.mp4",
        "pushup_workout.mp4",
        "three_idiots.mp4",
        "walking_style.mp4",
        "workout.mp4"
    ]
    
    # Required files from your JSON (with logical mappings)
    file_mappings = {
        "nuclear_facility_aerial.mp4": "glass_pouring.mp4",  # Generic footage
        "girl_workout.mp4": "girl_workout.mp4",  # Exact match
        "world_map_conflict.mp4": "walking_style.mp4",  # Movement/tension
        "international_pressure.mp4": "hera_pheri.mp4",  # Drama/tension
        "three_idiots.mp4": "three_idiots.mp4",  # Exact match
        "global_news_coverage.mp4": "bhag_milkha_bhag.mp4",  # Action/urgency
        "clock_countdown.mp4": "workout.mp4",  # Timing/rhythm
        "market_street.mp4": "walking_style.mp4",  # Movement
        "peace_demonstration.mp4": "pushup_workout.mp4",  # Group activity
        "airport_departure.mp4": "bhag_milkha_bhag.mp4",  # Travel/movement
        "media_briefing_india.mp4": "hera_pheri.mp4",  # Dialogue scene
        "diplomatic_meeting.mp4": "three_idiots.mp4"  # Meeting scene
    }
    
    assets_dir = "assets/brolls"
    os.makedirs(assets_dir, exist_ok=True)
    
    print("🎬 Creating B-Roll File Mappings...")
    
    for required_file, source_file in file_mappings.items():
        source_path = os.path.join(assets_dir, source_file)
        target_path = os.path.join(assets_dir, required_file)
        
        if os.path.exists(source_path) and not os.path.exists(target_path):
            try:
                shutil.copy2(source_path, target_path)
                print(f"✅ Mapped: {source_file} → {required_file}")
            except Exception as e:
                print(f"❌ Failed to map {source_file}: {e}")
        elif os.path.exists(target_path):
            print(f"⚡ Already exists: {required_file}")
        else:
            print(f"⚠️  Source missing: {source_file}")
    
    print(f"\n📁 B-Roll files now available in: {assets_dir}")
    
    # List all files in the directory
    if os.path.exists(assets_dir):
        files = os.listdir(assets_dir)
        print(f"📋 Total files: {len(files)}")
        for file in sorted(files):
            print(f"   • {file}")

if __name__ == "__main__":
    create_broll_mappings()