import streamlit as st
import datetime
import calendar
from storage import load_diary, save_diary
from model_utils import analyze_diary, emotion_icon
from proactive_doctor import analyze_trigger, stream_generation
from memory_explorer import MemoryExplorer, add_diary_to_vectorstore
from tts_utils import generate_tts

def render_calendar():
    st.title("📅 감정 일기장")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀ 이전 달"):
            curr = st.session_state.current_month
            if curr.month == 1:
                st.session_state.current_month = datetime.date(curr.year - 1, 12, 1)
            else:
                st.session_state.current_month = datetime.date(curr.year, curr.month - 1, 1)
            st.rerun()
    with col2:
        st.markdown(f"<h3 style='text-align: center;'>{st.session_state.current_month.strftime('%Y년 %m월')}</h3>", unsafe_allow_html=True)
    with col3:
        if st.button("다음 달 ▶"):
            curr = st.session_state.current_month
            if curr.month == 12:
                st.session_state.current_month = datetime.date(curr.year + 1, 1, 1)
            else:
                st.session_state.current_month = datetime.date(curr.year, curr.month + 1, 1)
            st.rerun()

    st.write("---")

    days = ["월", "화", "수", "목", "금", "토", "일"]
    cols = st.columns(7)
    for i, day in enumerate(days):
        cols[i].markdown(f"<div style='text-align: center; font-weight: bold;'>{day}</div>", unsafe_allow_html=True)


    year = st.session_state.current_month.year
    month = st.session_state.current_month.month
    cal = calendar.monthcalendar(year, month)

    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].write("")
                continue

            date_obj = datetime.date(year, month, day)
            date_str = date_obj.strftime("%Y-%m-%d")


            _, emotion = load_diary(st.session_state.username, date_str)
            icon = emotion_icon.get(emotion, "")

            # Button label
            label = f"{day}\n{icon}" if icon else str(day)

            if cols[i].button(label, key=f"btn_{date_str}", use_container_width=True):
                st.session_state.selected_date = date_str
                st.rerun()

def render_diary_entry(tokenizer, model):
    date_str = st.session_state.selected_date
    st.subheader(f"{date_str} 의 일기")

    if st.button("🔙 캘린더로 돌아가기"):
        st.session_state.selected_date = None
        st.session_state.saved_date = None
        st.rerun()

    existing_text, existing_emotion = load_diary(st.session_state.username, date_str)

    if existing_emotion:
        icon = emotion_icon.get(existing_emotion, "")
        st.markdown(f"**이날의 감정**: {existing_emotion} {icon}")

    diary_text = st.text_area("일기를 작성해주세요:", value=existing_text, height=200)

    is_existing = bool(existing_emotion)

    if is_existing:
        clicked = st.button("✏️ 수정하기")
    else:
        clicked = st.button("💾 저장하기")

    if clicked:
        if diary_text.strip():
            with st.spinner("감정을 분석 중입니다..."):
                emotion, _ = analyze_diary(diary_text, tokenizer, model)
                if emotion == '분석불가':
                    st.warning("분석할 수 없는 문장입니다. 조금 더 길게 작성해주세요.")
                else:
                    save_diary(st.session_state.username, date_str, diary_text, emotion)

                    # vectorstore 업데이트 (캐시된 MemoryExplorer 인스턴스가 있으면 재사용, 없으면 독립 함수 호출)
                    me_key = f"me_instance_{st.session_state.username}"
                    if me_key in st.session_state:
                        st.session_state[me_key].add_entry(date_str, emotion, diary_text)
                    else:
                        add_diary_to_vectorstore(st.session_state.username, date_str, emotion, diary_text)

                    icon = emotion_icon.get(emotion, "")
                    if is_existing:
                        st.success(f"수정되었습니다! (분석된 감정: {emotion} {icon})")
                        # 수정 시에는 감정 주치의 미동작
                    else:
                        st.success(f"저장되었습니다! (분석된 감정: {emotion} {icon})")
                        st.session_state.saved_date = date_str
                        # 이전 진단 결과 초기화
                        st.session_state.doctor_analyzed = False
                        st.session_state.doctor_triggered = None
                        st.session_state.doctor_message = None
                        st.session_state.doctor_tts_path = None
        else:
            st.warning("일기 내용을 입력해주세요.")

    if st.session_state.get("saved_date") == date_str:
        st.markdown("---")
        if st.button("🩺 감정 주치의 진단 보기"):
            st.session_state.show_doctor = True
            st.rerun()


def render_memory_explorer():
    st.title("🔍 기억 탐험가")
    st.caption("과거의 일기 기록을 함께 탐험해봐요.")

    username = st.session_state.get("username", "").strip()

    # MemoryExplorer 인스턴스 초기화 (사용자별로 session_state에 캐시)
    me_key = f"me_instance_{username}"
    if me_key not in st.session_state:
        with st.spinner("일기 데이터베이스에 연결 중..."):
            try:
                st.session_state[me_key] = MemoryExplorer(username)
            except Exception as e:
                st.error(f"데이터베이스 연결 실패: {e}")
                return

    explorer: MemoryExplorer = st.session_state[me_key]

    # 대화 기록 초기화
    if "me_messages" not in st.session_state:
        st.session_state.me_messages = []

    # 상단 정보 + 대화 초기화 버튼
    col1, col2 = st.columns([3, 1])
    with col1:
        count = explorer.diary_count()
        st.caption(f"저장된 일기: **{count}개**")
    with col2:
        if st.button("🔄 대화 초기화", use_container_width=True):
            explorer.reset()
            st.session_state.me_messages = []
            st.rerun()

    st.write("---")

    # 대화 히스토리 렌더링
    for msg in st.session_state.me_messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant" and msg.get("date_tag"):
                st.caption(msg["date_tag"])
            st.markdown(msg["content"])

    # 첫 진입 안내 메시지
    if not st.session_state.me_messages:
        with st.chat_message("assistant"):
            st.markdown(
                "안녕하세요! 과거의 기억을 함께 찾아드릴게요. 😊\n\n"
                "언제 어떤 일이 있었는지 자유롭게 말씀해주세요.\n\n"
                "예) *'작년 12월에 가족이랑 여행 갔던 거 기억나?'*"
            )

    # 사용자 입력
    if prompt := st.chat_input("기억을 떠올려볼까요?"):
        # 사용자 메시지 표시
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.me_messages.append({"role": "user", "content": prompt})

        # AI 응답 생성
        with st.chat_message("assistant"):
            with st.spinner("기억을 찾는 중..."):
                try:
                    response = explorer.chat(prompt)
                except Exception as e:
                    response = f"오류가 발생했습니다: {e}"

            # 날짜 태그 분리 렌더링
            date_tag = None
            display_text = response
            if response.startswith("[") and "]\n" in response:
                bracket_end = response.index("]\n")
                date_tag = response[1:bracket_end]
                display_text = response[bracket_end + 2:]

            if date_tag:
                st.caption(date_tag)
            st.markdown(display_text)

        st.session_state.me_messages.append({
            "role": "assistant",
            "content": display_text,
            "date_tag": date_tag,
        })


def _render_tts_player(message: str, username: str) -> None:
    """감정 주치의 메시지를 TTS로 변환하여 오디오 플레이어를 표시."""
    st.markdown("---")
    tts_path = st.session_state.get("doctor_tts_path")

    # 아직 생성되지 않은 경우 생성
    if not tts_path:
        with st.spinner("음성을 생성하는 중..."):
            try:
                tts_path = generate_tts(message, username)
                st.session_state.doctor_tts_path = tts_path
            except Exception as e:
                st.warning(f"음성 생성에 실패했습니다: {e}")
                return

    with open(tts_path, "rb") as f:
        audio_bytes = f.read()
    st.markdown("🔊 **음성으로 듣기**")
    st.audio(audio_bytes, format="audio/mp3")


def render_doctor_view():
    st.title("🩺 감정 주치의")

    if st.button("🔙 일기로 돌아가기"):
        st.session_state.show_doctor = False
        st.rerun()

    st.write("---")

    # 이미 분석 완료된 경우 저장된 결과 표시
    if st.session_state.get("doctor_analyzed"):
        if not st.session_state.get("doctor_triggered"):
            with st.status("분석 완료", state="complete", expanded=False):
                pass
            st.info(f"necessity_score: **{st.session_state.get('doctor_score', 0):.4f}**\n\n현재는 감정 주치의의 개입이 필요하지 않습니다.")
            st.markdown("---")
            st.markdown(st.session_state.get("doctor_message", ""))
        else:
            with st.status("✅ 공감 메시지 생성 완료.", state="complete", expanded=False):
                pass
            st.markdown("---")
            st.markdown(st.session_state.doctor_message)
            _render_tts_player(st.session_state.doctor_message, st.session_state.username)
        return

    # Stage 1~2: 트리거 분석
    not_triggered = False
    with st.status("최근 7일 일기를 분석하고 있습니다...", expanded=True) as status:
        st.write("감정 패턴과 위기 신호를 파악 중입니다...")
        result = analyze_trigger(st.session_state.username)
        st.session_state.doctor_score = result["score"]

        if not result["triggered"]:
            status.update(label="분석 완료", state="complete")
            st.session_state.doctor_analyzed = True
            st.session_state.doctor_triggered = False
            st.session_state.doctor_message = "감정 주치의가 필요한 정도는 아닌 것 같습니다. 앞으로는 계속 즐거운 하루가 되시길 바랍니다."
            st.info(f"necessity_score: **{result['score']:.4f}**\n\n현재는 감정 주치의의 개입이 필요하지 않습니다.")
            not_triggered = True
        else:
            st.write(f"necessity_score: **{result['score']:.4f}** — 주치의가 메시지를 작성합니다.")
            status.update(label="공감 메시지 생성 중...", state="running")

    if not_triggered:
        st.markdown("---")
        st.markdown(st.session_state.doctor_message)
        return

    # Stage 3: 스트리밍 생성
    st.markdown("---")
    message = st.write_stream(stream_generation(result["context"]))

    status.update(label="✅ 공감 메시지 생성 완료.", state="complete", expanded=False)

    # 결과 저장 (재방문 시 재생성 방지)
    st.session_state.doctor_analyzed = True
    st.session_state.doctor_triggered = True
    st.session_state.doctor_message = message
    st.session_state.doctor_tts_path = None  # 새 메시지이므로 TTS 캐시 초기화

    _render_tts_player(message, st.session_state.username)
