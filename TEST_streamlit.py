import streamlit as st
import datetime
from ui import render_calendar, render_diary_entry
from model_utils import load_model

def main():
    st.set_page_config(page_title="감정 일기장", page_icon="📖", layout="centered")

    if 'selected_date' not in st.session_state:
        st.session_state.selected_date = None
    if 'current_month' not in st.session_state:
        st.session_state.current_month = datetime.date.today().replace(day=1)

    st.text_input("👤 사용자 이름", key="username", placeholder="이름을 입력하세요 (예: 홍길동)")

    if not st.session_state.get('username', '').strip():
        st.info("사용자 이름을 입력하면 감정 일기장을 사용할 수 있습니다.")
        return

    tokenizer, model = load_model()

    if st.session_state.selected_date is None:
        render_calendar()
    else:
        render_diary_entry(tokenizer, model)

if __name__ == "__main__":
    main()


