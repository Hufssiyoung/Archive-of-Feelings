import streamlit as st
import datetime
from ui import render_calendar, render_diary_entry, render_doctor_view
from model_utils import load_model

def main():
    st.set_page_config(page_title="감정 일기장", page_icon="📖", layout="centered")

    if 'selected_date' not in st.session_state:
        st.session_state.selected_date = None
    if 'current_month' not in st.session_state:
        st.session_state.current_month = datetime.date.today().replace(day=1)
    if 'show_doctor' not in st.session_state:
        st.session_state.show_doctor = False
    if 'saved_date' not in st.session_state:
        st.session_state.saved_date = None
    if 'doctor_analyzed' not in st.session_state:
        st.session_state.doctor_analyzed = False
    if 'doctor_triggered' not in st.session_state:
        st.session_state.doctor_triggered = None
    if 'doctor_message' not in st.session_state:
        st.session_state.doctor_message = None
    if 'doctor_score' not in st.session_state:
        st.session_state.doctor_score = 0.0

    st.text_input("👤 사용자 이름", key="username", placeholder="이름을 입력하세요 (예: 홍길동)")

    if not st.session_state.get('username', '').strip():
        st.info("사용자 이름을 입력하면 감정 일기장을 사용할 수 있습니다.")
        return

    tokenizer, model = load_model()

    if st.session_state.show_doctor:
        render_doctor_view()
    elif st.session_state.selected_date is None:
        render_calendar()
    else:
        render_diary_entry(tokenizer, model)

if __name__ == "__main__":
    main()
