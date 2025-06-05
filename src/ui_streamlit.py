import streamlit as st
import os
import json
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
from transcribe import transcribe_audio
from spell_corrector import correct_spelling_groq_words
from translate import translate_words_with_context
from render_subtitles import render_subtitles
from broll_mapper import process_transcript_context, load_broll_knowledge, save_meme_map
from video_editor import MemeVideoProcessor
from export import export_final_video

WORKFLOW_GROUPS = {
    "text_processing": {
        "title": "📝 Text Processing (Fixed Order)",
        "processes": ["transcribe", "spell_correct", "translate"],
        "fixed_order": True
    },
    "video_processing": {
        "title": "🎬 Video Processing (Flexible Order)",
        "processes": ["subtitle_render", "meme_processing"],
        "fixed_order": False
    },
    "final_export": {
        "title": "📤 Final Export (Always Last)",
        "processes": ["export"],
        "fixed_order": True
    }
}

PROCESSES = {
    "transcribe": {"title": "🎙️ Transcription", "group": "text_processing"},
    "spell_correct": {"title": "✏️ Spell Check", "group": "text_processing"},
    "translate": {"title": "🌐 Translation", "group": "text_processing"},
    "subtitle_render": {"title": "💬 Subtitle Render", "group": "video_processing"},
    "meme_processing": {"title": "🎭 Meme Processing", "group": "video_processing"},
    "export": {"title": "📤 Export", "group": "final_export"}
}

st.set_page_config(page_title="Video Editor", page_icon="🎬", layout="wide")

def init_session():
    defaults = {
        'video_order': ['subtitle_render', 'meme_processing'],
        'processing_status': {},
        'file_paths': {},
        'subtitle_language': 'hinglish',
        'export_formats': ['Original'],
        'meme_threshold': 0.8,
        'current_video': None,
        'subtitle_text_color': 'white',
        'subtitle_shadow_color': 'black',
        'subtitle_shadow_opacity': 0.7,
        'subtitle_position': 'bottom',
        'subtitle_size': 'medium',
        'use_custom_style': False,
        'custom_style_content': '',
        'selected_font_path': 'Arial'
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def get_font_size(size_option):
    size_map = {
        "small": 30,
        "medium": 38,
        "large": 50
    }
    return size_map.get(size_option, 38)

def create_dirs():
    dirs = ["data/input_videos", "data/transcripts", "data/subtitles", "data/exports",
            "assets/brolls", "assets/styles", "assets/fonts", "output", "knowledge_base"]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)

def check_dependencies():
    deps = {}
    try:
        import faster_whisper
        deps["whisper"] = True
    except ImportError:
        try:
            import whisper
            deps["whisper"] = True
        except ImportError:
            deps["whisper"] = False
   
    modules = {"moviepy": "moviepy", "groq": "groq", "PIL": "PIL"}
    for name, module in modules.items():
        try:
            __import__(module)
            deps[name] = True
        except ImportError:
            deps[name] = False
   
    return deps

def get_available_fonts():
    fonts = {}
    
    if os.name == 'nt':
        system_fonts = {
            "Arial": "C:/Windows/Fonts/arial.ttf",
            "Arial Bold": "C:/Windows/Fonts/arialbd.ttf",
            "Times New Roman": "C:/Windows/Fonts/times.ttf",
            "Calibri": "C:/Windows/Fonts/calibri.ttf",
            "Comic Sans MS": "C:/Windows/Fonts/comic.ttf",
            "Impact": "C:/Windows/Fonts/impact.ttf",
            "Trebuchet MS": "C:/Windows/Fonts/trebuc.ttf",
            "Verdana": "C:/Windows/Fonts/verdana.ttf"
        }
        fonts.update(system_fonts)
    
    elif os.name == 'posix':
        linux_fonts = {
            "DejaVu Sans": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "Liberation Sans": "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "Ubuntu": "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf"
        }
        fonts.update(linux_fonts)
    
    custom_fonts_dir = Path("assets/fonts")
    if custom_fonts_dir.exists():
        for font_file in custom_fonts_dir.glob("*.ttf"):
            font_name = f"Custom: {font_file.stem}"
            fonts[font_name] = str(font_file)
    
    return fonts

def save_uploaded_font(uploaded_font):
    if uploaded_font:
        font_path = Path("assets/fonts") / uploaded_font.name
        with open(font_path, "wb") as f:
            f.write(uploaded_font.getbuffer())
        return str(font_path)
    return None

def get_sample_style_json():
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

def save_custom_style():
    if st.session_state.custom_style_content:
        try:
            style_data = json.loads(st.session_state.custom_style_content)
            style_path = "assets/styles/custom.json"
            with open(style_path, "w", encoding="utf-8") as f:
                json.dump(style_data, f, indent=2)
            return style_path
        except json.JSONDecodeError:
            st.error("Invalid JSON format in custom style")
            return None
    return None

def get_input_video_for_step(step_name):
    if step_name in ["transcribe", "spell_correct", "translate"]:
        return st.session_state.file_paths.get('input_video')
   
    if st.session_state.video_order[0] == step_name:
        return st.session_state.file_paths.get('input_video')
    else:
        first_step = st.session_state.video_order[0]
        if first_step == 'subtitle_render':
            return "output/with_subtitles.mp4"
        else:
            return "output/with_memes.mp4"

def get_exported_files():
    export_dir = Path("data/exports")
    if not export_dir.exists():
        return []
    
    exported_files = []
    for file_path in export_dir.glob("*.mp4"):
        exported_files.append(str(file_path))
    
    return exported_files

def run_process(process_name):
    try:
        st.session_state.processing_status[process_name] = "🔄"
       
        if process_name == 'transcribe':
            input_video = st.session_state.file_paths['input_video']
            transcribe_audio(input_video, "data/transcripts/output.json")
           
        elif process_name == 'spell_correct':
            correct_spelling_groq_words("data/transcripts/output.json", "data/transcripts/cleaned.json")
           
        elif process_name == 'translate':
            translate_words_with_context("data/transcripts/cleaned.json", "data/subtitles/combined.json")
           
        elif process_name == 'subtitle_render':
            input_video = get_input_video_for_step('subtitle_render')
            if not input_video or not Path(input_video).exists():
                raise Exception("Input video not found")
            
            if st.session_state.use_custom_style:
                style_path = save_custom_style()
                if not style_path:
                    style_path = "assets/styles/default.json"
            else:
                style_path = "assets/styles/quick_style.json"
                quick_style = {
                    "font": st.session_state.get('selected_font_path', 'Arial'),
                    "font_size": get_font_size(st.session_state.subtitle_size),
                    "text_color": st.session_state.subtitle_text_color,
                    "bg_color": st.session_state.subtitle_shadow_color,
                    "bg_opacity": st.session_state.subtitle_shadow_opacity,
                    "padding": 8,
                    "position": st.session_state.subtitle_position,
                    "method": "label"
                }
                with open(style_path, "w", encoding="utf-8") as f:
                    json.dump(quick_style, f, indent=2)
            
            if not Path(style_path).exists():
                default_style = get_sample_style_json()
                with open(style_path, "w", encoding="utf-8") as f:
                    json.dump(default_style, f, indent=2)
            
            render_subtitles(
                video_path=input_video, 
                subtitle_path="data/subtitles/combined.json",
                style_path=style_path, 
                output_path="output/with_subtitles.mp4",
                language=st.session_state.subtitle_language,
                text_color=st.session_state.subtitle_text_color,
                shadow_color=st.session_state.subtitle_shadow_color,
                shadow_opacity=st.session_state.subtitle_shadow_opacity,
                position=st.session_state.subtitle_position,
                size=st.session_state.subtitle_size
            )
           
        elif process_name == 'meme_processing':
            if not Path("data/subtitles/combined.json").exists():
                raise Exception("Need translation first")
           
            knowledge_base_path = Path("knowledge_base/broll_knowledge_base.json")
            if knowledge_base_path.exists():
                knowledge_base = load_broll_knowledge()
                meme_map = process_transcript_context(
                    "data/subtitles/combined.json", 
                    knowledge_base,
                    confidence_threshold=st.session_state.meme_threshold
                )
                save_meme_map(meme_map, "data/subtitles/meme_map.json")
            else:
                raise Exception("Meme knowledge base missing")
           
            input_video = get_input_video_for_step('meme_processing')
            if not input_video or not Path(input_video).exists():
                raise Exception("Input video not found")
           
            processor = MemeVideoProcessor(confidence_threshold=st.session_state.meme_threshold)
            result = processor.process_meme_video(
                main_video_path=input_video,
                meme_map_path="data/subtitles/meme_map.json",
                output_path="output/with_memes.mp4",
                assets_dir="assets/brolls"
            )
           
        elif process_name == 'export':
            video_outputs = []
            for step in st.session_state.video_order:
                if st.session_state.processing_status.get(step) == "✅":
                    if step == 'subtitle_render' and Path("output/with_subtitles.mp4").exists():
                        video_outputs.append("output/with_subtitles.mp4")
                    elif step == 'meme_processing' and Path("output/with_memes.mp4").exists():
                        video_outputs.append("output/with_memes.mp4")
            if video_outputs:
                input_video = video_outputs[-1]
            else:
                input_video = st.session_state.file_paths['input_video']
           
            export_dir = Path("data/exports")
            export_dir.mkdir(parents=True, exist_ok=True)
           
            for fmt in st.session_state.export_formats:
                aspect = {"9:16 (Vertical)": "9:16", "16:9 (Horizontal)": "16:9",
                         "1:1 (Square)": "1:1"}.get(fmt, "original")
                export_final_video(input_video, str(export_dir), aspect)
       
        st.session_state.processing_status[process_name] = "✅"
        st.success(f"✅ {PROCESSES[process_name]['title']} completed!")
       
    except Exception as e:
        st.session_state.processing_status[process_name] = "❌"
        st.error(f"❌ Error in {PROCESSES[process_name]['title']}: {str(e)}")

def render_header():
    st.title("🎬 Video Editing Automation")
    st.markdown("Transform videos into professionally edited content")

def render_workflow():
    st.header("🔧 Workflow Configuration")
   
    col1, col2 = st.columns(2)
   
    with col1:
        st.subheader("Workflow Structure")
        st.markdown("**📝 Text Processing (Fixed Order)**")
        for i, process in enumerate(["transcribe", "spell_correct", "translate"]):
            st.write(f"{i+1}. {PROCESSES[process]['title']}")
       
        st.markdown("---")
        st.markdown("**🎬 Video Processing (You can reorder)**")
        for i, process in enumerate(st.session_state.video_order):
            col_a, col_b, col_c = st.columns([0.1, 0.7, 0.2])
            with col_a:
                st.write(f"{i+1}.")
            with col_b:
                st.write(PROCESSES[process]['title'])
            with col_c:
                if len(st.session_state.video_order) > 1:
                    if st.button("🔄", key=f"swap_{i}"):
                        order = st.session_state.video_order
                        order[0], order[1] = order[1], order[0]
                        st.rerun()
       
        st.markdown("---")
        st.markdown("**📤 Final Export (Always Last)**")
        st.write("1. 📤 Export")
   
    with col2:
        st.subheader("General Configuration")
        st.multiselect("Export Formats",
                      ["9:16 (Vertical)", "16:9 (Horizontal)", "1:1 (Square)", "Original"],
                      default=["Original"], key="export_formats")
        st.slider("Meme Confidence Threshold", 0.5, 1.0, 0.8, key="meme_threshold")

def render_subtitle_customization():
    st.subheader("🎨 Subtitle Customization")
    
    style_method = st.radio(
        "Style Configuration Method",
        ["Quick Options", "Custom JSON Style"],
        key="style_method"
    )
    
    if style_method == "Quick Options":
        st.session_state.use_custom_style = False
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.selectbox("Text Color", 
                        ["white", "black", "red", "blue", "green", "yellow", "cyan", "magenta"],
                        key="subtitle_text_color")
            st.selectbox("Shadow Color", 
                        ["black", "white", "red", "blue", "green", "yellow", "cyan", "magenta"],
                        key="subtitle_shadow_color")
            st.slider("Shadow Opacity", 0.0, 1.0, 0.7, step=0.1, key="subtitle_shadow_opacity")
        
        with col2:
            st.selectbox("Position", ["top", "center", "bottom"], 
                        index=2, key="subtitle_position")
            st.selectbox("Size", ["small", "medium", "large"], 
                        index=1, key="subtitle_size")
            
            available_fonts = get_available_fonts()
            if available_fonts:
                font_names = list(available_fonts.keys())
                selected_font = st.selectbox("Font", font_names, key="selected_font")
                st.session_state.selected_font_path = available_fonts[selected_font]
            else:
                st.session_state.selected_font_path = "Arial"
        
        st.markdown("---")
        st.subheader("📁 Upload Custom Font")
        uploaded_font = st.file_uploader(
            "Upload TTF font file", 
            type=['ttf'],
            help="Upload your custom .ttf font file to use in subtitles"
        )
        
        if uploaded_font:
            font_path = save_uploaded_font(uploaded_font)
            if font_path:
                st.success(f"✅ Font uploaded: {uploaded_font.name}")
                st.info("🔄 Refresh the page to see the new font in the dropdown")
    
    else:
        st.session_state.use_custom_style = True
        
        st.subheader("📁 Upload Custom Font (Optional)")
        uploaded_font = st.file_uploader(
            "Upload TTF font file", 
            type=['ttf'],
            help="Upload your custom .ttf font file and use its path in JSON below",
            key="json_font_upload"
        )
        
        if uploaded_font:
            font_path = save_uploaded_font(uploaded_font)
            if font_path:
                st.success(f"✅ Font uploaded to: `{font_path}`")
                st.info("Copy the path above and use it in your JSON configuration")
        
        st.markdown("---")
        st.markdown("**Sample Style JSON:**")
        sample_style = get_sample_style_json()
        st.code(json.dumps(sample_style, indent=2), language="json")
        
        available_fonts = get_available_fonts()
        if available_fonts:
            st.markdown("**Available Font Paths:**")
            font_info = ""
            for name, path in available_fonts.items():
                font_info += f"- **{name}**: `{path}`\n"
            st.markdown(font_info)
        
        st.markdown("**Your Custom Style:**")
        st.text_area(
            "Enter your custom style JSON:",
            value=st.session_state.get('custom_style_content', json.dumps(sample_style, indent=2)),
            height=200,
            key="custom_style_content",
            help="Customize font, colors, positioning, and other style parameters"
        )
        
        if st.session_state.custom_style_content:
            try:
                json.loads(st.session_state.custom_style_content)
                st.success("✅ Valid JSON format")
            except json.JSONDecodeError as e:
                st.error(f"❌ Invalid JSON: {e}")

def render_upload():
    st.header("📁 File Upload")
   
    uploaded_file = st.file_uploader("Choose Hindi video", type=['mp4', 'avi', 'mov', 'mkv'])
   
    if uploaded_file:
        input_path = Path("data/input_videos") / uploaded_file.name
        input_path.parent.mkdir(parents=True, exist_ok=True)
       
        with open(input_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
       
        st.session_state.file_paths['input_video'] = str(input_path)
        st.success(f"✅ Video saved: {uploaded_file.name}")
        st.video(str(input_path))

def render_processing():
    st.header("🚀 Processing")
   
    if 'input_video' not in st.session_state.file_paths:
        st.warning("⚠️ Upload video first")
        return
   
    col1, col2 = st.columns([2, 1])
   
    with col1:
        if st.button("🎬 Start Full Pipeline", type="primary", use_container_width=True):
            text_steps = ["transcribe", "spell_correct", "translate"]
            video_steps = st.session_state.video_order
            final_steps = ["export"]
           
            all_steps = text_steps + video_steps + final_steps
           
            for step in all_steps:
                st.write(f"Running {PROCESSES[step]['title']}...")
                run_process(step)
                if st.session_state.processing_status[step] == "❌":
                    st.error("Pipeline stopped due to error")
                    break
       
        st.subheader("Individual Controls")
       
        st.markdown("**📝 Text Processing**")
        for process in ["transcribe", "spell_correct", "translate"]:
            col_a, col_b = st.columns([3, 1])
            with col_a:
                if st.button(f"Run {PROCESSES[process]['title']}", key=f"run_{process}"):
                    run_process(process)
            with col_b:
                status = st.session_state.processing_status.get(process, "⏳")
                st.write(status)
       
        st.markdown("**🎬 Video Processing**")
        for process in st.session_state.video_order:
            col_a, col_b = st.columns([3, 1])
            with col_a:
                if st.button(f"Run {PROCESSES[process]['title']}", key=f"run_{process}"):
                    run_process(process)
            with col_b:
                status = st.session_state.processing_status.get(process, "⏳")
                st.write(status)
       
        st.markdown("**📤 Export**")
        col_a, col_b = st.columns([3, 1])
        with col_a:
            if st.button("Run 📤 Export", key="run_export"):
                run_process("export")
        with col_b:
            status = st.session_state.processing_status.get("export", "⏳")
            st.write(status)
   
    with col2:
        st.subheader("Progress")
        all_processes = ["transcribe", "spell_correct", "translate"] + st.session_state.video_order + ["export"]
        total = len(all_processes)
        completed = sum(1 for p in all_processes
                       if st.session_state.processing_status.get(p) == "✅")
        st.progress(completed / total if total > 0 else 0)
        st.write(f"{completed}/{total} completed")

def render_results():
    st.header("📥 Final Results")
   
    export_status = st.session_state.processing_status.get("export", "⏳")
    
    if export_status == "✅":
        exported_files = get_exported_files()
        
        if exported_files:
            st.success("🎉 Export completed successfully!")
            
            for video_path in exported_files:
                video_file = Path(video_path)
                st.subheader(f"🎬 {video_file.name}")
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.video(video_path, format="video/mp4", start_time=0)
                
                with col2:
                    size = video_file.stat().st_size / (1024*1024)
                    st.write(f"**Size:** {size:.1f} MB")
                    
                    with open(video_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Download Video",
                            data=f.read(),
                            file_name=video_file.name,
                            mime="video/mp4",
                            key=f"download_{video_file.stem}"
                        )
                
                st.markdown("---")
        else:
            st.info("No exported files found. Please run the export process.")
    
    elif export_status == "🔄":
        st.info("🔄 Export in progress...")
    
    elif export_status == "❌":
        st.error("❌ Export failed. Please check the logs and try again.")
    
    else:
        st.info("💡 Complete the processing pipeline to see final results here.")
        
        if any(status in ["🔄", "✅"] for status in st.session_state.processing_status.values()):
            st.subheader("📊 Current Progress")
            
            all_processes = ["transcribe", "spell_correct", "translate"] + st.session_state.video_order + ["export"]
            
            for process in all_processes:
                status = st.session_state.processing_status.get(process, "⏳")
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"{PROCESSES[process]['title']}")
                with col2:
                    if status == "✅":
                        st.success("✅")
                    elif status == "🔄":
                        st.info("🔄")
                    elif status == "❌":
                        st.error("❌")
                    else:
                        st.write("⏳")

def render_sidebar():
    with st.sidebar:
        st.header("🛠️ Status")
       
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            st.success("✅ Groq API Key loaded")
        else:
            st.error("❌ Groq API Key missing")
            st.caption("Add GROQ_API_KEY to .env file")
       
        st.markdown("---")
       
        st.subheader("Dependencies")
        deps = check_dependencies()
        for package, status in deps.items():
            if status:
                st.success(f"✅ {package}")
            else:
                st.error(f"❌ {package}")

def main():
    init_session()
    create_dirs()
   
    render_header()
    render_sidebar()
   
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔧 Workflow", "🎨 Subtitles", "📁 Upload", "🚀 Process", "📥 Results"])
   
    with tab1:
        render_workflow()
    with tab2:
        render_subtitle_customization()
    with tab3:
        render_upload()
    with tab4:
        render_processing()
    with tab5:
        render_results()

if __name__ == "__main__":
    main()