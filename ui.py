import streamlit as st
import datetime
import calendar
from storage import load_diary, save_diary
from model_utils import analyze_diary, emotion_icon

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
        else:
            st.warning("일기 내용을 입력해주세요.")
