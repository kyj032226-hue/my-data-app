from datetime import datetime, timedelta
import pytz
import requests
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon="🎬",
    layout="wide"
)

@st.cache_data(ttl=3600)
def fetch_box_office_data(api_key: str, target_dt: str):
    """
    KOBIS API를 호출하여 해당 날짜의 일별 박스오피스 데이터를 가져옵니다.
    @st.cache_data(ttl=3600) 데코레이터를 이용해 동일한 날짜 요청은 1시간(3600초) 동안 캐싱합니다.
    """
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    params = {
        "key": api_key,
        "targetDt": target_dt
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        # 네트워크 응답 코드가 200이 아닌 경우 예외(Exception)를 발생시킵니다.
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.RequestException as e:
        return None, f"네트워크 통신 오류가 발생했습니다: {str(e)}"


def get_yesterday_kst():
    """
    배포 서버의 시계와 무관하게 '한국 표준시(KST)' 기준으로 어제 날짜를 계산합니다.
    - target_dt: API 요청용 여덟 자리 날짜 (YYYYMMDD)
    - formatted_date: 화면 표시용 날짜 문자열
    """
    kst_tz = pytz.timezone('Asia/Seoul')
    now_kst = datetime.now(kst_tz)
    yesterday_kst = now_kst - timedelta(days=1)
    
    target_dt = yesterday_kst.strftime('%Y%m%d')
    formatted_date = yesterday_kst.strftime('%Y년 %m월 %d일')
    return target_dt, formatted_date


st.title("🎬 어제의 대한민국 박스오피스")

# KST 기준 어제 날짜 계산
target_dt, formatted_date = get_yesterday_kst()

st.subheader(f"📅 기준일자: {formatted_date} ({target_dt})")
st.caption("※ 오늘 박스오피스는 아직 집계 전이므로, 한국 시간 기준 어제 데이터를 자동으로 불러옵니다.")

# Streamlit Secrets(비밀 금고)에서 KOBIS_KEY를 읽어옵니다.
api_key = st.secrets.get("KOBIS_KEY")

# API 인증키가 설정되어 있지 않은 경우 오류 안내
if not api_key:
    st.error("🚨 KOBIS API 인증키가 설정되지 않았습니다.")
    st.markdown("""
    ### 💡 사용 전 확인 필요 사항
    1. **Streamlit Cloud에 배포할 경우:**
       - 대시보드의 **App Settings** > **Secrets** 메뉴에 아래 코드를 추가해 주세요:
         ```toml
         KOBIS_KEY = "발급받은_KOBIS_키입력"
         ```
    2. **로컬 컴퓨터에서 실행할 경우:**
       - 프로젝트 폴더 안에 `.streamlit/secrets.toml` 파일을 만들고 키를 작성해 주세요.
    """)
    st.stop()

with st.spinner("영화진흥위원회(KOBIS)에서 박스오피스 데이터를 불러오는 중..."):
    json_data, error_msg = fetch_box_office_data(api_key, target_dt)

# 1. 네트워크 통신 에러 처리
if error_msg:
    st.error("🚨 데이터를 불러오는 데 실패했습니다.")
    st.write(f"**상세 내용:** {error_msg}")
    st.info("💡 **확인 사항:** 인터넷 연결 상태를 점검하거나 잠시 후 다시 시도해 주세요.")
    st.stop()

# 2. KOBIS API의 faultInfo 오류 처리 (인증키 오류 등 status_code=200 이면서 에러 전달 시)
if "faultInfo" in json_data:
    fault = json_data["faultInfo"]
    st.error("🚨 KOBIS API 인증 및 처리 과정에서 오류가 발생했습니다.")
    st.warning(f"**오류 메시지:** {fault.get('message', '알 수 없는 오류')}")
    st.markdown("""
    ### 💡 해결 방법 안내
    - `secrets.toml` 또는 Streamlit Cloud Secrets에 입력한 **KOBIS_KEY**가 정확한지 확인해 주세요.
    - [KOBIS 오픈 API 홈페이지](https://www.kobis.or.kr/kobisopenapi)에서 키 승인 상태를 확인해 주세요.
    """)
    st.stop()

# 3. 영화 데이터 추출 및 빈 데이터 검증
boxoffice_result = json_data.get("boxOfficeResult", {})
movie_list = boxoffice_result.get("dailyBoxOfficeList", [])

if not movie_list:
    st.warning("⚠️ 조회된 박스오피스 영화 목록이 없습니다.")
    st.info("💡 **확인 사항:** 해당 일자의 데이터 집계가 완료되지 않았거나 일시적인 데이터 부재일 수 있습니다.")
    st.stop()

# 데이터프레임 변환
df = pd.DataFrame(movie_list)

# 문자열로 들어온 숫자 데이터를 계산 및 정렬이 가능한 정수형(int)으로 변환
df['rank'] = df['rank'].astype(int)
df['audiCnt'] = df['audiCnt'].astype(int)
df['audiAcc'] = df['audiAcc'].astype(int)
df['scrnCnt'] = df['scrnCnt'].astype(int)

st.markdown("---")
st.subheader("🥇 어제의 박스오피스 1위")

top_1 = df.iloc[0]

# 3개의 대형 지표 카드로 표시
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label=f"🏆 {top_1['movieNm']}",
        value=f"{top_1['audiCnt']:,} 명",
        delta="어제 당일 관객수"
    )

with col2:
    st.metric(
        label="🎬 누적 관객수",
        value=f"{top_1['audiAcc']:,} 명"
    )

with col3:
    st.metric(
        label="🖥️ 상영 스크린수",
        value=f"{top_1['scrnCnt']:,} 개"
    )

st.markdown("---")
st.subheader("📊 관객수 상위 5개 영화 비교")

# 순위 상위 5개 추출 후 차트 시각화를 위해 순서 정렬
top_5_df = df.head(5).sort_values(by="rank", ascending=False)

# 막대그래프 생성을 위한 데이터 준비
chart_data = pd.DataFrame({
    "영화명": top_5_df["movieNm"],
    "관객수": top_5_df["audiCnt"]
}).set_index("영화명")

st.bar_chart(chart_data, horizontal=True)

st.markdown("---")
st.subheader("📋 전체 박스오피스 순위표")

# 표에 보여줄 필요한 컬럼만 선택하고 보기 쉽게 컬럼명 변경
display_df = df[['rank', 'movieNm', 'openDt', 'audiCnt', 'audiAcc', 'scrnCnt']].copy()
display_df.columns = ['순위', '영화명', '개봉일', '관객수', '누적관객', '스크린수']

# 숫자에 천 단위 쉼표(,) 및 단위 접미사를 자동으로 붙여 표 출력
st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "순위": st.column_config.NumberColumn("순위", format="%d위"),
        "관객수": st.column_config.NumberColumn("관객수 (명)", format="%,d명"),
        "누적관객": st.column_config.NumberColumn("누적관객 (명)", format="%,d명"),
        "스크린수": st.column_config.NumberColumn("스크린수 (개)", format="%,d개"),
    }
)

st.caption("데이터 출처: 영화진흥위원회(KOBIS) 영화관입장권통합전산망 오픈 API")
