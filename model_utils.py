import re
import torch
import torch.nn.functional as F
import streamlit as st
from transformers import AutoTokenizer, AutoModelForSequenceClassification


emotion_icon = {
    '기쁨': '😊',
    '놀라움': '😮',
    '두려움': '😨',
    '분노': '😠',
    '불쾌함': '😒',
    '설렘': '🤩',
    '슬픔': '😢',
    '평범함': '😐'
}

@st.cache_resource
def load_model():
    load_path = 'model'
    tokenizer = AutoTokenizer.from_pretrained(load_path)
    model = AutoModelForSequenceClassification.from_pretrained(load_path)
    return tokenizer, model

def analyze_diary(diary_text, tokenizer, model):
    id2label = model.config.id2label
    sentences = re.split(r'(?<=[.?!])\s+', diary_text.strip())
    sentences = [s for s in sentences if len(s) > 2]
    
    if not sentences:
        return '분석불가', None

    emotion_stats = {
        k: {'total_prob': 0.0, 'count': 0, 'last_step': -1}
        for k in id2label.keys()
    }

    for step, sentence in enumerate(sentences):
        inputs = tokenizer(sentence,
                           return_tensors='pt',
                           padding=True,
                           truncation=True,
                           max_length=256)

        with torch.no_grad():
            outputs = model(**inputs)
            probs = F.softmax(outputs.logits, dim=1)

            max_prob, predicted_idx = torch.max(probs, dim=1)
            prob_val = max_prob.item()
            idx_val = predicted_idx.item()

            emotion_stats[idx_val]['total_prob'] += prob_val
            emotion_stats[idx_val]['count'] += 1
            emotion_stats[idx_val]['last_step'] = step

    best_emotion_idx = max(
        emotion_stats,
        key=lambda k: (
            emotion_stats[k]['total_prob'],
            emotion_stats[k]['count'],
            emotion_stats[k]['last_step']
        )
    )

    final_emotion = id2label[best_emotion_idx]
    return final_emotion, emotion_stats
