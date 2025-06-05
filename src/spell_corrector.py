import json
import time
import os
from groq import Groq
from dotenv import load_dotenv
import re

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Check if the text contains any Hindi characters (Devanagari Unicode block)
def contains_hindi(text):
    return re.search(r'[\u0900-\u097F]', text) is not None

def correct_spelling_groq_words(transcript_file, corrected_output, chunk_size=10):
    with open(transcript_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    corrected = []
    i = 0

    while i < len(data):
        chunk = data[i:i + chunk_size]
        raw_text = " ".join([word["word"] for word in chunk])

        # Skip if text is entirely in English or non-Hindi
        if not contains_hindi(raw_text):
            corrected.extend(chunk)
            print(f"⏩ Skipping English chunk {i}-{i+chunk_size}: {raw_text}")
            i += chunk_size
            continue

        # Hindi correction prompt
        prompt = (
            f"इनपुट किए गए शब्द का आउटपुट दें, कोई अतिरिक्त शब्द नहीं, केवल सही वर्तनी वाला वही शब्द। "
            f"यदि आपको लगता है कि कुछ शब्द गलत हैं तो उन्हें सुधारें "
            f"[जैसे एक शब्द 'पलदार' को 'पलटवार' के रूप में सही किया जाना चाहिए], "
            f"और कोई अतिरिक्त शब्द, वाक्य, प्रतीक नहीं जोड़ा जाएगा, बस आउटपुट दें:\n\"{raw_text}\""
        )

        try:
            response = client.chat.completions.create(
                model="mistral-saba-24b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_completion_tokens=1024,
                top_p=1,
                stream=False
            )

            corrected_text = response.choices[0].message.content.strip()
            corrected_words = corrected_text.split()

            for j, word in enumerate(chunk):
                corrected.append({
                    "start": word["start"],
                    "end": word["end"],
                    "word": corrected_words[j] if j < len(corrected_words) else word["word"]
                })

            print(f"✅ Corrected Hindi chunk {i}-{i+chunk_size}: {corrected_text}")
            time.sleep(1)

        except Exception as e:
            print(f"❌ Error on chunk {i}-{i+chunk_size}: {e}")
            corrected.extend(chunk)

        i += chunk_size

    with open(corrected_output, "w", encoding="utf-8") as f:
        json.dump(corrected, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    correct_spelling_groq_words(
        "data/transcripts/output.json",
        "data/transcripts/cleaned.json"
    )
