import streamlit as st
import datetime
from ui import render_calendar, render_diary_entry, render_doctor_view, render_memory_explorer
from model_utils import load_model
from tts_utils import clear_user_cache

def render_login():
    """로그인 화면 - 사용자 이름 입력 후 진입."""
    page = st.session_state.get("current_page", "diary")
    if page == "memory":
        st.title("🔍 기억 탐험가")
        st.info("사용자 이름을 입력하면 기억 탐험가를 시작할 수 있습니다.")
    else:
        st.title("📖 감정 일기장")
        st.info("사용자 이름을 입력하면 감정 일기장을 사용할 수 있습니다.")

    with st.form("login_form"):
        name_input = st.text_input("👤 사용자 이름", placeholder="이름을 입력하세요 (예: 홍길동)")
        submitted = st.form_submit_button("시작하기", use_container_width=True, type="primary")
        if submitted:
            if name_input.strip():
                st.session_state.logged_in_user = name_input.strip()
                st.rerun()
            else:
                st.warning("이름을 입력해주세요.")

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
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "diary"
    if 'logged_in_user' not in st.session_state:
        st.session_state.logged_in_user = None

    # 로그인 전: 로그인 화면만 표시
    if not st.session_state.logged_in_user:
        render_login()
        return

    # 로그인 후: username을 logged_in_user로 고정
    st.session_state.username = st.session_state.logged_in_user

    # 사이드바
    with st.sidebar:
        st.markdown("## 메뉴")
        if st.button("📖 감정 일기장", use_container_width=True,
                     type="primary" if st.session_state.current_page == "diary" else "secondary"):
            st.session_state.current_page = "diary"
            st.session_state.show_doctor = False
            st.rerun()
        if st.button("🔍 기억 탐험가", use_container_width=True,
                     type="primary" if st.session_state.current_page == "memory" else "secondary"):
            st.session_state.current_page = "memory"
            st.rerun()

        st.divider()
        st.markdown(f"**{st.session_state.logged_in_user}** 님")
        if st.button("로그아웃", use_container_width=True):
            current_user = st.session_state.logged_in_user
            # MemoryExplorer 인스턴스 먼저 제거 (logged_in_user 사용)
            me_key = f"me_instance_{current_user}"
            st.session_state.pop(me_key, None)
            # TTS 캐시 삭제
            clear_user_cache(current_user)
            # 사용자 관련 상태 초기화
            for key in ["logged_in_user", "username", "selected_date", "saved_date",
                        "show_doctor", "doctor_analyzed", "doctor_triggered",
                        "doctor_message", "doctor_score", "doctor_tts_path", "me_messages"]:
                st.session_state.pop(key, None)
            st.rerun()

    # 페이지 라우팅
    if st.session_state.current_page == "memory":
        render_memory_explorer()
    elif st.session_state.show_doctor:
        render_doctor_view()
    elif st.session_state.selected_date is None:
        tokenizer, model = load_model()
        render_calendar()
    else:
        tokenizer, model = load_model()
        render_diary_entry(tokenizer, model)

if __name__ == "__main__":
    main()
