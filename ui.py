import streamlit as st
import datetime
import calendar
from storage import load_diary, save_diary
from model_utils import analyze_diary, emotion_icon
from proactive_doctor import analyze_trigger, stream_generation

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

    if st.button("💾 저장하기"):
        if diary_text.strip():
            with st.spinner("감정을 분석 중입니다..."):
                emotion, _ = analyze_diary(diary_text, tokenizer, model)
                if emotion == '분석불가':
                    st.warning("분석할 수 없는 문장입니다. 조금 더 길게 작성해주세요.")
                else:
                    save_diary(st.session_state.username, date_str, diary_text, emotion)
                    icon = emotion_icon.get(emotion, "")
                    st.success(f"저장되었습니다! (분석된 감정: {emotion} {icon})")
                    st.session_state.saved_date = date_str
                    # 이전 진단 결과 초기화
                    st.session_state.doctor_analyzed = False
                    st.session_state.doctor_triggered = None
                    st.session_state.doctor_message = None
        else:
            st.warning("일기 내용을 입력해주세요.")

    if st.session_state.get("saved_date") == date_str:
        st.markdown("---")
        if st.button("🩺 감정 주치의 진단 보기"):
            st.session_state.show_doctor = True
            st.rerun()


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
