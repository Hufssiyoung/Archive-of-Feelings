# 데이터 저장 방식에 대해서는 조금 더 고민이 필요할 것 같음. -> 일단은 임시로 데이터 data 파일내에서 처리
import os
import json

DATA_DIR = "data"

def get_diary_path(username):
    return os.path.join(DATA_DIR, username)

def load_diary(username, date_str):
    path = get_diary_path(username)
    diary_text = ""
    emotion = ""
    if os.path.exists(path):
        json_file = os.path.join(path, "diary.json")
        if os.path.exists(json_file):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if date_str in data:
                        entry = data[date_str]
                        diary_text = entry.get("diary", "")
                        emotion = entry.get("emotion", "")
            except json.JSONDecodeError:
                pass
    return diary_text, emotion

def save_diary(username, date_str, text, emotion):
    path = get_diary_path(username)
    if not os.path.exists(path):
        os.makedirs(path)
    json_path = os.path.join(path, "diary.json")
    
    data = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    data = {}
        except Exception:
            pass

    data[date_str] = {
        "date": date_str,
        "emotion": emotion,
        "diary": text
    }
    
    sorted_data = dict(sorted(data.items()))

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(sorted_data, f, ensure_ascii=False, indent=4)
