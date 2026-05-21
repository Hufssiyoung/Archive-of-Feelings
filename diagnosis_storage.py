import os
import json

DATA_DIR = "data"


def get_diagnosis_path(username):
    return os.path.join(DATA_DIR, username, "diagnosis.json")


def save_diagnosis(username: str, date_str: str, empathy: str, diagnosis: str) -> None:
    """날짜별 진단 결과를 diagnosis.json에 저장합니다."""
    path = os.path.join(DATA_DIR, username)
    if not os.path.exists(path):
        os.makedirs(path)

    json_path = get_diagnosis_path(username)
    data = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass

    data[date_str] = {
        "date": date_str,
        "empathy": empathy,
        "diagnosis": diagnosis,
    }

    # 최신순 정렬
    sorted_data = dict(sorted(data.items(), reverse=True))
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(sorted_data, f, ensure_ascii=False, indent=4)


def load_diagnoses(username: str) -> list:
    """모든 진단 결과를 최신순으로 반환합니다."""
    json_path = get_diagnosis_path(username)
    if not os.path.exists(json_path):
        return []
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return sorted(data.values(), key=lambda x: x["date"], reverse=True)
    except Exception:
        return []
