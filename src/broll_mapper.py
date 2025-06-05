import json
import os
import time
import random
import requests
from pathlib import Path
from dotenv import load_dotenv
import re

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

TRANSCRIPT_PATH_DEFAULT = Path("data/subtitles/sample3_words_translated.json")
KNOWLEDGE_BASE_PATH = Path("knowledge_base/broll_knowledge_base.json")
OUTPUT_PATH_DEFAULT = Path("data/subtitles/sample3_words_broll_map.json")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

def extract_inner_json(content):
    code_block_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
    if code_block_match:
        json_str = code_block_match.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None
    
    match = re.search(r'\{.*?\}', content, re.DOTALL)
    if match:
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None
    return None

def load_broll_knowledge():
    with open(KNOWLEDGE_BASE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def analyze_emotional_context(chunk):
    combined_text = f"{chunk.get('hindi', '')} {chunk.get('english', '')} {chunk.get('hinglish', '')}".lower()
    
    context = {
        'emotion': 'neutral',
        'situation': 'general',
        'intensity': 'low',
        'themes': []
    }
    
    if any(word in combined_text for word in ['khush', 'happy', 'celebrate', 'success', 'good', 'achha', 'badhiya']):
        context['emotion'] = 'joy'
        context['intensity'] = 'high'
    elif any(word in combined_text for word in ['problem', 'issue', 'tension', 'pareshani', 'dikkat', 'mushkil']):
        context['emotion'] = 'stress'
        context['intensity'] = 'medium'
    elif any(word in combined_text for word in ['confusion', 'samjh', 'understand', 'kya', 'doubt']):
        context['emotion'] = 'confused'
        context['intensity'] = 'medium'
    elif any(word in combined_text for word in ['money', 'paisa', 'business', 'profit', 'earning']):
        context['situation'] = 'money'
        context['intensity'] = 'high'
    elif any(word in combined_text for word in ['risk', 'danger', 'safe', 'careful', 'bach']):
        context['situation'] = 'caution'
        context['intensity'] = 'high'
    elif any(word in combined_text for word in ['style', 'confidence', 'attitude', 'cool']):
        context['situation'] = 'swagger'
        context['intensity'] = 'medium'
    elif any(word in combined_text for word in ['angry', 'gussa', 'frustrate', 'irritate']):
        context['emotion'] = 'anger'
        context['intensity'] = 'high'
    elif any(word in combined_text for word in ['run', 'bhag', 'fast', 'speed', 'jaldi']):
        context['situation'] = 'urgency'
        context['intensity'] = 'high'
    
    return context

def build_context_prompt(chunk, knowledge_base):
    hindi_text = chunk.get('hindi', '')
    english_text = chunk.get('english', '')
    hinglish_text = chunk.get('hinglish', '')
    
    context = analyze_emotional_context(chunk)
    
    meme_items = [item for item in knowledge_base if item.get('type') == 'meme']
    random.shuffle(meme_items)
    
    meme_summary = "\n".join([
        f"- {item['id']}: {item['description'][:70]}... (context: {', '.join(item.get('context_keywords', [])[:3])})"
        for item in meme_items[:10]
    ])

    return f"""
Analyze video content for perfect meme match. Focus on DEEP CONTEXTUAL understanding.

DETECTED CONTEXT:
- Emotion: {context['emotion']}
- Situation: {context['situation']}  
- Intensity: {context['intensity']}

MATCHING RULES:
- HIGHLY RELATABLE (confidence >0.7): Perfect emotional/situational match
- MODERATELY RELATABLE (0.4-0.7): Good contextual connection
- WEAK MATCH (<0.4): Skip with "none"

Think like human - what meme would perfectly represent this moment?

RESPOND ONLY JSON:
{{
  "id": "meme_id_or_none",
  "confidence": 0.0_to_1.0,
  "reason": "Why this meme perfectly matches the context"
}}

AVAILABLE MEMES:
{meme_summary}

CONTENT:
Hindi: "{hindi_text}"
English: "{english_text}"
Hinglish: "{hinglish_text}"

Match by MEANING and EMOTION, not keywords!
"""

def query_groq_context(prompt):
    body = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "messages": [
            {
                "role": "system",
                "content": "You are a meme selection AI. Choose memes based on deep contextual understanding. Be selective - only pick highly relatable memes. Respond only with valid JSON."
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.4,
        "max_tokens": 250,
        "top_p": 0.8
    }

    try:
        print("🤖 Querying AI for meme selection...")
        response = requests.post(GROQ_API_URL, headers=HEADERS, json=body, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ AI Error: {response.status_code}")
            return None

        raw_content = response.json()["choices"][0]["message"]["content"].strip()
        print(f"🔍 AI Response: {raw_content[:80]}...")
        
        result = extract_inner_json(raw_content)
        
        if result and isinstance(result, dict):
            if all(field in result for field in ['id', 'confidence', 'reason']):
                return result
        
        return None
        
    except Exception as e:
        print(f"❌ AI Query Error: {e}")
        return None

def calculate_contextual_score(segment, meme_item):
    hindi_text = segment.get('hindi', '').lower()
    english_text = segment.get('english', '').lower() 
    hinglish_text = segment.get('hinglish', '').lower()
    combined_text = f"{hindi_text} {english_text} {hinglish_text}"
    
    meme_keywords = [kw.lower() for kw in meme_item.get('context_keywords', [])]
    meme_tags = [tag.lower() for tag in meme_item.get('tags', [])]
    
    exact_matches = sum(1 for kw in meme_keywords if kw in combined_text)
    tag_matches = sum(1 for tag in meme_tags if tag in combined_text)
    
    keyword_score = (exact_matches / max(1, len(meme_keywords))) * 0.6
    tag_score = (tag_matches / max(1, len(meme_tags))) * 0.4
    
    base_score = keyword_score + tag_score
    
    context_boost = 0
    context = analyze_emotional_context(segment)
    
    if context['emotion'] == 'joy' and any(tag in meme_tags for tag in ['happiness', 'celebration', 'success']):
        context_boost += 0.25
    elif context['emotion'] == 'stress' and any(tag in meme_tags for tag in ['problem', 'trouble', 'caution']):
        context_boost += 0.25
    elif context['situation'] == 'money' and 'money' in meme_tags:
        context_boost += 0.3
    elif context['situation'] == 'swagger' and any(tag in meme_tags for tag in ['confidence', 'style', 'cool']):
        context_boost += 0.2
    
    final_score = min(1.0, base_score + context_boost)
    return round(final_score, 3)

def chunk_words(words, chunk_size=12, overlap=4):
    chunks = []
    step = max(1, chunk_size - overlap)
    
    for i in range(0, len(words), step):
        chunk = words[i:i + chunk_size]
        if len(chunk) >= 6:
            chunks.append(chunk)
    
    return chunks

def should_skip_meme(meme_result, confidence_threshold=0.6):
    if not meme_result or not isinstance(meme_result, dict):
        return True
    
    confidence = float(meme_result.get('confidence', 0.0))
    meme_id = meme_result.get('id', '')
    
    if meme_id in ['none', '']:
        return True
    
    if confidence < confidence_threshold:
        print(f"⏭️ Skip meme '{meme_id}' - confidence {confidence:.3f} below {confidence_threshold}")
        return True
    
    return False

def process_transcript_context(transcript_path_str, knowledge_base, confidence_threshold=0.6):
    print(f"📖 Loading transcript: {transcript_path_str}")
    transcript_path = Path(transcript_path_str)
    
    with open(transcript_path, "r", encoding="utf-8") as f:
        words = json.load(f)

    print(f"📝 Creating word chunks...")
    word_chunks = chunk_words(words, chunk_size=12, overlap=4)
    meme_map = []
    processed_count = 0
    skipped_count = 0

    print(f"🎯 Processing {len(word_chunks)} chunks with threshold: {confidence_threshold}")

    for chunk_idx, chunk in enumerate(word_chunks):
        print(f"\n🔍 Chunk {chunk_idx + 1}/{len(word_chunks)}")
        
        if not chunk or not all(isinstance(w, dict) for w in chunk):
            print("⚠️ Invalid chunk structure")
            continue

        hindi_line = " ".join([w.get("hindi", "") for w in chunk]).strip()
        english_line = " ".join([w.get("english", "") for w in chunk]).strip()
        hinglish_line = " ".join([w.get("hinglish", "") for w in chunk]).strip()

        if not any([hindi_line, english_line, hinglish_line]):
            print("⏭️ Empty content")
            continue

        segment = {
            "hindi": hindi_line,
            "english": english_line,
            "hinglish": hinglish_line
        }

        chunk_start_time = chunk[2]["start"] if len(chunk) > 2 else chunk[0]["start"]
        chunk_end_time = chunk[-1]["end"]
        
        if chunk_end_time - chunk_start_time < 2.0:
            print("⏭️ Too short segment")
            continue

        print(f"⏰ Time: {chunk_start_time:.1f}s-{chunk_end_time:.1f}s")
        print(f"📝 Text: {hinglish_line[:60]}...")

        prompt = build_context_prompt(segment, knowledge_base)
        meme_result = query_groq_context(prompt)
        
        if should_skip_meme(meme_result, confidence_threshold):
            skipped_count += 1
            continue
        
        if meme_result:
            meme_id = meme_result['id']
            
            meme_item = next((item for item in knowledge_base if item['id'] == meme_id), None)
            
            if meme_item:
                enhanced_confidence = calculate_contextual_score(segment, meme_item)
                original_confidence = float(meme_result.get('confidence', 0.0))
                final_confidence = max(enhanced_confidence, original_confidence)
                
                if final_confidence < confidence_threshold:
                    print(f"⏭️ Skip after enhanced calc: {final_confidence:.3f}")
                    skipped_count += 1
                    continue
                
                meme_entry = {
                    "start": chunk_start_time,
                    "end": chunk_end_time,
                    "hinglish": hinglish_line,
                    "broll": {
                        "id": meme_id,
                        "type": "meme",
                        "confidence": final_confidence,
                        "reason": meme_result.get('reason', 'Context match'),
                        "max_duration": 5
                    }
                }
                
                meme_map.append(meme_entry)
                processed_count += 1
                print(f"✅ Added meme: {meme_id} (confidence: {final_confidence:.3f})")
            else:
                print(f"⚠️ Meme '{meme_id}' not in knowledge base")
                skipped_count += 1
        else:
            skipped_count += 1
        
        time.sleep(random.uniform(1.5, 2.5))

    print(f"\n📊 Final: {processed_count} memes added, {skipped_count} skipped")
    return meme_map

def save_meme_map(meme_map, output_path_str):
    print(f"💾 Saving meme map...")
    output_path_obj = Path(output_path_str)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    result = {
        "metadata": {
            "total_memes": len(meme_map),
            "avg_confidence": round(sum(m.get('broll', {}).get('confidence', 0) for m in meme_map) / max(1, len(meme_map)), 3),
            "generated_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "broll_mappings": meme_map
    }
    
    with open(output_path_obj, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Meme mapping saved: {output_path_obj}")
    print(f"📈 Stats: {result['metadata']['total_memes']} memes, avg confidence: {result['metadata']['avg_confidence']}")

if __name__ == "__main__":
    print("🚀 Starting Meme Mapper...")
    
    if not GROQ_API_KEY:
        print("❌ GROQ_API_KEY missing")
        exit(1)
    
    try:
        print("📚 Loading meme knowledge base...")
        knowledge = load_broll_knowledge()
        meme_count = len([item for item in knowledge if item.get('type') == 'meme'])
        print(f"🎭 Loaded {meme_count} memes")
        
        print("📝 Processing transcript...")
        meme_map_result = process_transcript_context(
            str(TRANSCRIPT_PATH_DEFAULT), 
            knowledge, 
            confidence_threshold=0.6
        )
        
        print("💾 Saving results...")
        save_meme_map(meme_map_result, str(OUTPUT_PATH_DEFAULT))
        
        print("🎉 Meme mapping completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()