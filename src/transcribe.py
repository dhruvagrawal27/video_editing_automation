from faster_whisper import WhisperModel
import json
import os

def transcribe_audio(input_path, output_json):
    # Load model
    model = WhisperModel("small", compute_type="int8")

    # Step 1: Detect language (first 30 seconds are enough)
    print("🌐 Detecting language...")
    segments, info = model.transcribe(
        input_path,
        vad_filter=True,
        word_timestamps=False,  # Don't need them for detection
        language=None           # 🔍 Let model detect language
    )

    detected_lang = info.language
    print(f"🔤 Detected Language: {detected_lang}")

    # Step 2: Decide final language
    final_language = "en" if detected_lang == "en" else "hi"
    print(f"🗣️ Using Language: {'English' if final_language == 'en' else 'Hindi'}")

    # Step 3: Transcribe again with word-level timestamps
    segments, _ = model.transcribe(
        input_path,
        language=final_language,
        vad_filter=True,
        initial_prompt="कृपया देवनागरी लिपि में ट्रांसक्राइब करें।" if final_language == "hi" else None,
        word_timestamps=True
    )

    full_transcript = []
    for segment in segments:
        for word in segment.words:
            full_transcript.append({
                "start": round(word.start, 2),
                "end": round(word.end, 2),
                "word": word.word.strip()
            })

    # Save transcript
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(full_transcript, f, ensure_ascii=False, indent=2)

    print(f"✅ Transcription saved to {output_json}")

if __name__ == "__main__":
    transcribe_audio(
        r"C:\Users\lenovo\Downloads\videoplayback.mp4",
        "data/transcripts/sample3_words.json"
    )
