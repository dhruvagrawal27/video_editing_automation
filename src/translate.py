import json
import time
import os
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Helper: detect if a word is in English (Latin letters only)
import string

def is_english_word(word):
    cleaned = word.strip(string.punctuation + "“”‘’\"")  # Remove surrounding punctuation
    return re.fullmatch(r'[a-zA-Z0-9\s\-\']+', cleaned) is not None



def translate_words_with_context(input_file, output_file, context_size=2):
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    translated = []
    all_words = [entry["word"] for entry in data]

    for i, word_entry in enumerate(data):
        hindi_word = word_entry["word"]

        # 🛑 Skip translation for English words
        if is_english_word(hindi_word):
            translated.append({
                "start": word_entry["start"],
                "end": word_entry["end"],
                "hindi": hindi_word,
                "english": hindi_word,
                "hinglish": hindi_word
            })
            print(f"⏩ Skipped English word: {hindi_word}")
            continue

        # Otherwise, translate from Hindi
        start_idx = max(0, i - context_size)
        end_idx = min(len(all_words), i + context_size + 1)
        context_words = all_words[start_idx:end_idx]
        context_phrase = " ".join(context_words)

        eng_prompt = (
            f"Translate the Hindi word '{hindi_word}' in the context of this phrase:\n\"{context_phrase}\"\n"
            "Provide only the English equivalent of the highlighted word without extra explanation."
        )

        hing_prompt = (
            f"Convert this Hindi word into Hinglish (Hindi written in casual English letters, e.g. 'mujhe'):\n\"{hindi_word}\"\n"
            "Reply only with the Hinglish word, no explanation."
        )

        try:
            # English Translation
            eng_response = client.chat.completions.create(
                model="meta-llama/llama-4-maverick-17b-128e-instruct",
                messages=[{"role": "user", "content": eng_prompt}],
                temperature=0.2,
                max_completion_tokens=20,
            )
            english = eng_response.choices[0].message.content.strip()

            # Hinglish Conversion
            hing_response = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{"role": "user", "content": hing_prompt}],
                temperature=0.2,
                max_completion_tokens=20,
            )
            hinglish = hing_response.choices[0].message.content.strip()

            translated.append({
                "start": word_entry["start"],
                "end": word_entry["end"],
                "hindi": hindi_word,
                "english": english,
                "hinglish": hinglish
            })

            print(f"[{word_entry['start']:.2f} - {word_entry['end']:.2f}] {hindi_word} -> {english} / {hinglish}")
            time.sleep(0.3)

        except Exception as e:
            print(f"❌ Error translating word '{hindi_word}' at {word_entry['start']}: {e}")
            translated.append({
                "start": word_entry.get("start", 0),
                "end": word_entry.get("end", 0),
                "hindi": hindi_word,
                "english": "[Error]",
                "hinglish": "[Error]"
            })

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(translated, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    translate_words_with_context(
        input_file="data/transcripts/cleaned.json",
        output_file="data/subtitles/combined.json"
    )
