import streamlit as st
import streamlit.components.v1 as components
import uuid
import os
import json

# 모듈 수입
from database.local_db import init_local_db, save_user_run, get_user_history_by_email
from database.neo4j_sync import sync_to_neo4j_safely
from core.assessment import calculate_scores, load_ontology
from core.graph_visual import build_pyvis_graph
from core.report_gen import generate_pdf_report

# 앱 최초 실행 시 SQLite 로컬 로그 테이블 초기화 보장
init_local_db()

st.set_page_config(page_title="CoachKG Navigator", layout="wide", page_icon="🧭")

# 스타일 보완을 위한 임시 CSS 패치
st.markdown("""
    <style>
    .reportview-container .main .block-container{ max-width: 1200px; }
    .stButton>button { width: 100%; border-radius: 6px; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# [세션 상태 관리 모델 정의]
# -----------------------------------------------------------------------------
if "browser_session_id" not in st.session_state:
    st.session_state.browser_session_id = uuid.uuid4().hex[:10]
if "step" not in st.session_state:
    st.session_state.step = 1
if "user_meta" not in st.session_state:
    st.session_state.user_meta = {}
if "card_sorting" not in st.session_state:
    st.session_state.card_sorting = {}
if "results" not in st.session_state:
    st.session_state.results = []

# 🧭 타이틀 헤더
st.title("🧭 동적 강점 내비게이터")
st.caption("비회원 개방형 - 3단계 하이브리드 강점 가치 지도 진단 서비스")
st.markdown("---")

# =============================================================================
# 🛠️ [실시간 시스템 진단 및 상태 모니터 대시보드 - 정밀 추적 버전]
# =============================================================================
with st.expander("🛠️ 실시간 시스템 디버깅 대시보드 (진단용)", expanded=True):
    st.write("### 🖥️ 세션 및 상태 데이터 실시간 모니터")
    db_col1, db_col2, db_col3 = st.columns(3)
    with db_col1:
        st.metric("현재 진행 단계 (Step)", st.session_state.step)
    with db_col2:
        st.metric("세션 ID (Browser ID)", st.session_state.browser_session_id)
    with db_col3:
        st.metric("유저 정보 입력 여부", "Yes" if st.session_state.user_meta else "No")
        
    st.write("📂 **1단계 분류 데이터 (card_sorting) 적재 상태:**")
    if st.session_state.card_sorting:
        a_cnt = sum(1 for v in st.session_state.card_sorting.values() if v == "A")
        b_cnt = sum(1 for v in st.session_state.card_sorting.values() if v == "B")
        c_cnt = sum(1 for v in st.session_state.card_sorting.values() if v == "C")
        
        if a_cnt == 0:
            st.error("🚨 경고: A(핵심 강점)로 분류된 강점이 0개입니다. 이 상태로는 2단계 문항이 출력되지 않습니다.")
        else:
            st.success(f"🟢 **A (핵심):** {a_cnt}개 | 🟡 **B (보완):** {b_cnt}개 | 🔴 **C (일반):** {c_cnt}개 저장 중")
    else:
        st.warning("⚠️ 분류 데이터가 완전히 비어 있습니다.")
        
    st.write("⚙️ **강제 제어 및 병목 구간 검증기:**")
    # [핵심 검증 스위치] DB 쓰기나 외부 싱크 과정에서 락(Lock)이 걸리는지 우회 점검하는 체크박스
    bypass_db = st.checkbox("⚠️ 디버그: SQLite 및 Neo4j 저장 건너뛰고 결과 바로보기 (체크 권장)", value=False)
    
    btn_col1, btn_col2, btn_col3 = st.columns(3)
    with btn_col1:
        if st.button("🔄 강제 Step 1로 리셋"):
            st.session_state.step = 1
            st.session_state.card_sorting = {}
            st.session_state.results = []
            st.session_state.user_meta = {}
            st.rerun()
    with btn_col2:
        if st.button("⚠️ 강제 Step 2로 점프"):
            st.session_state.step = 2
            st.rerun()
    with btn_col3:
        if st.button("🏆 강제 Step 3로 이동 (테스트 데이터 주입)"):
            st.session_state.step = 3
            st.session_state.user_meta = {"name": "디버그길동", "email": "debug@domain.com"}
            ontology = load_ontology()
            dummy_results = []
            for s in ontology["strengths"][:5]:
                dummy_results.append({
                    "code": s["code"],
                    "name": s["name"],
                    "virtue": s.get("virtue_name", "덕목군"),
                    "virtue_code": s.get("virtue_code", "VIR_UNKNOWN"),
                    "group": "A",
                    "final_score": 4.8,
                    "summary": s.get("summary", "테스트용 설명문구입니다."),
                    "keywords": s.get("keywords", ["키워드1", "키워드2"])
                })
            st.session_state.results = dummy_results
            st.rerun()
            
st.markdown("---")

# -----------------------------------------------------------------------------
# STEP 1: 익명 식별 정보 기입 및 1차 카드 소팅 (개선형 3분류 카드 뷰)
# -----------------------------------------------------------------------------
if st.session_state.step == 1:
    st.subheader("1단계: 정보 입력 및 자가 강점 소팅")
    st.info("💡 별도의 비밀번호가 필요 없는 완전 공개형 서비스입니다. 기재하신 정보는 중복 데이터 방지와 PDF 리포트 기입, 이력 복원에만 활용됩니다.")
    
    # 온톨로지에서 가용 강점 명단 로드
    ontology = load_ontology()
    
    # 5대 대덕목별 강점 그룹화 준비
    from collections import defaultdict
    grouped_strengths = defaultdict(list)
    for s in ontology["strengths"]:
        grouped_strengths[s.get("virtue_name", "미분류")].append(s)
        
    with st.form("user_entry_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("이름 또는 닉네임", placeholder="홍길동", help="리포트 표기용 이름")
        with col2:
            email = st.text_input("이메일 주소", placeholder="yourname@domain.com", help="이전 진단 이력 재조회 및 복원용 식별 키")
            
        st.markdown("---")
        st.write("📂 **자가 강점 카드 분류 (Self Card-Sorting)**")
        st.write("아래 제시된 50가지 강점의 설명을 읽어보시고, 나에게 해당되는 수준에 맞게 **[A: 핵심]**, **[B: 보완]**, **[C: 일반]** 그룹으로 편안하게 소팅해 주세요.")
        st.caption("💡 각 탭(대덕목)을 클릭하면 소속된 강점 목록을 차례대로 확인하실 수 있습니다. 기본값은 'C: 일반/미개발'로 세팅되어 있습니다.")
        
        # 5대 덕목에 대응하는 가로형 탭 생성
        virtue_names = list(grouped_strengths.keys())
        tabs = st.tabs(virtue_names)
        
        for tab, virtue in zip(tabs, virtue_names):
            with tab:
                st.write(f"✨ **{virtue}** 관련 강점 리스트")
                for s in grouped_strengths[virtue]:
                    with st.container(border=True):
                        c1, c2 = st.columns([1.3, 1])
                        with c1:
                            st.markdown(f"**{s['name']}**")
                            st.caption(s.get("summary", "상세 설명이 준비되어 있습니다."))
                        with c2:
                            st.radio(
                                label=f"분류 ({s['name']})",
                                options=["A: 핵심 강점", "B: 보완 강점", "C: 일반/미개발"],
                                index=2,  # 기본값 C로 세팅
                                horizontal=True,
                                key=f"sort_{s['code']}",
                                label_visibility="collapsed"
                            )
                            
        st.markdown("---")
        submit_step1 = st.form_submit_button("설문 저장 및 다음 검증 단계로")
        
        if submit_step1:
            if not name or not email:
                st.error("성함과 이메일 식별자를 기재해 주셔야 이력 복원 및 진행이 가능합니다.")
            else:
                temp_sorting = {}
                for s in ontology["strengths"]:
                    selected_val = st.session_state.get(f"sort_{s['code']}", "C: 일반/미개발")
                    temp_sorting[s["code"]] = selected_val[0]
                
                selected_a_count = sum(1 for v in temp_sorting.values() if v == "A")
                
                if selected_a_count < 1:
                    st.error("최소 한 개 이상의 강점을 'A: 핵심 강점'으로 분류해 주셔야 다음 단계 행동 검증 질문지가 구성됩니다.")
                else:
                    st.session_state.user_meta = {"name": name, "email": email}
                    st.session_state.card_sorting = temp_sorting
                    st.session_state.step = 2
                    st.rerun()

    # --- 무인증 이력 복원 레이어 (하단 배치) ---
    st.markdown("---")
    with st.expander("🔍 내 이전 진단 이력 즉시 복원하기"):
        st.write("과거에 이메일을 기재하여 진행했던 진단 이력이 있다면, 아래에 동일한 이메일을 기입하여 실시간으로 복원할 수 있습니다.")
        search_email = st.text_input("식별용 이메일 입력", key="search_email_input")
        if st.button("과거 기록 추적"):
            if search_email:
                history = get_user_history_by_email(search_email)
                if history:
                    st.success(f"과거 {len(history) // 24 if len(history) >= 24 else 1}건의 누적 데이터 로그를 발견했습니다.")
                    latest_run = history[:24]
                    
                    rebuilt_results = []
                    ontology = load_ontology()
                    s_map = {s["code"]: s for s in ontology["strengths"]}
                    
                    for r in latest_run:
                        s_info = s_map.get(r["strength_code"], {})
                        rebuilt_results.append({
                            "code": r["strength_code"],
                            "name": s_info.get("name", "미분류"),
                            "virtue": s_info.get("virtue_name", "미분류"),
                            "virtue_code": s_info.get("virtue_code", "VIR_UNKNOWN"),
                            "group": r["sorting_group"],
                            "final_score": r["final_score"],
                            "summary": s_info.get("summary", ""),
                            "keywords": s_info.get("keywords", [])
                        })
                    
                    st.session_state.user_meta = {"name": latest_run[0]["name"], "email": search_email}
                    st.session_state.results = rebuilt_results
                    st.session_state.step = 3
                    st.rerun()
                else:
                    st.warning("입력하신 이메일로 저장된 과거 진단 이력이 존재하지 않습니다.")

# -----------------------------------------------------------------------------
# STEP 2: 축소 지표 검증 (리커트 척도 평정)
# -----------------------------------------------------------------------------
elif st.session_state.step == 2:
    st.subheader("2단계: 선별 대표 강점 입증 검증")
    meta = st.session_state.user_meta
    st.write(f"✍️ **{meta['name']}님**, 고르신 핵심 강점들을 실제 자주 실천하고 보람을 느끼는지 척도 검증을 수행합니다.")
    
    # 1단계에서 가져온 ontology 매핑
    ontology = load_ontology()
    s_map = {s["code"]: s for s in ontology["strengths"]}
    
    # data/questions.json에서 축소 문항 로드
    questions_path = os.path.join(os.path.dirname(__file__), "data", "questions.json")
    with open(questions_path, "r", encoding="utf-8") as qf:
        questions_dict = json.load(qf)
        
    selected_a_codes = [k for k, v in st.session_state.card_sorting.items() if v == "A"]
    survey_responses = {}
    
    with st.form("verification_form"):
        for code in selected_a_codes:
            s_name = s_map[code]["name"]
            st.write(f"**[{s_name}]** 강점 검증 질문")
            st.info(f"👉 질문: {questions_dict.get(code, '나는 해당 강점 사용에 큰 가치와 의미를 부여한다.')}")
            
            # 슬라이더 평정
            score_val = st.slider(
                "전혀 그렇지 않다 (1)  ~  매우 그렇다 (5)", 
                min_value=1, max_value=5, value=3, key=f"q_{code}"
            )
            survey_responses[code] = score_val
            st.markdown("<br>", unsafe_allow_html=True)
            
        submit_step2 = st.form_submit_button("최종 분석 완료 및 우주 지도 펼치기")
        
    # -------------------------------------------------------------------------
    # [정밀 디버깅 실행기] 단계별 출력 로그를 화면에 실시간으로 심어 먹통 원인을 규명합니다.
    # -------------------------------------------------------------------------
    if submit_step2:
        transition_to_step3 = False
        st.write("🔄 **[디버그 로그]** 제출 버튼 동작 감지됨. 연산 처리를 시작합니다...")
        
        try:
            # 1. 연산 실행
            st.write("🔄 **[디버그 로그]** 1단계: 강점 가중치 연산(`calculate_scores`) 호출 중...")
            raw_results = calculate_scores(st.session_state.card_sorting, survey_responses)
            st.session_state.results = raw_results
            st.write("✅ **[디버그 로그]** 1단계 연산 완료!")
            
            # 2. DB 및 외부 싱크 제어
            if not bypass_db:
                st.write("🔄 **[디버그 로그]** 2단계: 로컬 SQLite 데이터베이스 쓰기 수행 중...")
                save_user_run(
                    st.session_state.browser_session_id, 
                    meta["email"], 
                    meta["name"], 
                    raw_results
                )
                st.write("✅ **[디버그 로그]** 2단계 SQLite3 백업 완료!")
                
                st.write("🔄 **[디버그 로그]** 3단계: Neo4j AuraDB 클라우드 동기화 중...")
                top_5_for_sync = [
                    {"code": r["code"], "final_score": r["final_score"]} 
                    for r in raw_results if r["group"] == "A"
                ][:5]
                sync_to_neo4j_safely(meta["email"], meta["name"], top_5_for_sync)
                st.write("✅ **[디버그 로그]** 3단계 외부 Neo4j 싱크 프로세스 완료!")
            else:
                st.warning("⚠️ **[디버그 모드]** DB 및 API 동기화 단계를 우회(Bypass)했습니다.")
                
            transition_to_step3 = True
            
        except Exception as e:
            st.error("❌ **[디버그 로그]** 비즈니스 로직 처리 중 예상치 못한 에러가 발생했습니다.")
            st.exception(e)  # 상세한 에러 정보 및 코드 발생 라인을 화면에 고정 표시
            
        if transition_to_step3:
            st.write("🔄 **[디버그 로그]** 모든 로직 성공. 3단계 결과 페이지로 이동(Rerun)합니다.")
            st.session_state.step = 3
            st.rerun()

# -----------------------------------------------------------------------------
# STEP 3: 동적 결과 분석 리포트 및 시각화 탐색
# -----------------------------------------------------------------------------
elif st.session_state.step == 3:
    meta = st.session_state.user_meta
    results = st.session_state.results
    
    # 최종 점수로 필터링된 상위 5대 핵심 강점 정의
    top_5 = [r for r in results if r["group"] == "A"][:5]
    if not top_5:
        # A가 없을 시 최상위 5개 대체
        top_5 = results[:5]
        
    st.subheader(f"🏆 {meta['name']}님의 지능형 강점 지도 피드백")
    
    col1, col2 = st.columns([1.2, 1])
    
    with col1:
        st.write("### 🌌 나의 강점 지식 지도")
        st.caption("대표 강점 5종과 이들의 소속 덕목(삼각형), 그리고 강점들 사이에 흐르는 유기적인 보완 및 시너지 지형도입니다.")
        
        # 1. 파일 생성 및 저장 절대 경로 반환 받기
        html_path = build_pyvis_graph(st.session_state.browser_session_id, top_5)
        
        if os.path.exists(html_path):
            try:
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # [핵심 패치] PyVis가 생성한 로컬 자바스크립트 종속성을 HTML에 통째로 내장시킵니다.
                base_dir = os.path.dirname(html_path)
                utils_js_path = os.path.join(base_dir, "lib", "bindings", "utils.js")
                
                if os.path.exists(utils_js_path):
                    with open(utils_js_path, 'r', encoding='utf-8') as js_f:
                        utils_js_content = js_f.read()
                    
                    # 다양한 형태의 script 태그 정의에 대비해 일괄 직접 치환 수행
                    tag_double = '<script type="text/javascript" src="lib/bindings/utils.js"></script>'
                    tag_single = "<script type='text/javascript' src='lib/bindings/utils.js'></script>"
                    tag_simple = '<script src="lib/bindings/utils.js"></script>'
                    
                    inline_script = f'<script type="text/javascript">{utils_js_content}</script>'
                    
                    html_content = html_content.replace(tag_double, inline_script)
                    html_content = html_content.replace(tag_single, inline_script)
                    html_content = html_content.replace(tag_simple, inline_script)
                
                # HTTPS 환경 보안 우회 패치 추가 적용
                html_content = html_content.replace("http://cdnjs.cloudflare.com", "https://cdnjs.cloudflare.com")
                html_content = html_content.replace("http://cdn.jsdelivr.net", "https://cdn.jsdelivr.net")
                html_content = html_content.replace('src="http://', 'src="https://')
                
                # 2. 완전히 독립적인 HTML 데이터를 iframe 주입
                components.html(html_content, height=420, scrolling=True)
                
            except Exception as e:
                st.error(f"❌ 지도 템플릿을 인라인화하는 과정에서 오류가 발생했습니다: {e}")
        else:
            st.warning(f"⚠️ 임시 지도가 생성되지 않았습니다. (지정 경로: {html_path})")
                
    with col2:
        st.write("### 📑 최상위 강점 상세 정보")
        for idx, r in enumerate(top_5, 1):
            with st.expander(f"**{idx}순위 : {r['name']}** (분석 평점 : {r['final_score']} / 5.0)"):
                st.write(f"📂 **소속 덕목** : {r['virtue']}")
                st.write(f"💬 **핵심 요약** : {r['summary']}")
                if r['keywords']:
                    st.write(f"🏷️ **키워드** : {', '.join(r['keywords'])}")
                    
    # 리포트 다운로드 및 리셋 제어 버튼 설계
    st.markdown("---")
    c1, c2 = st.columns(2)
    
    with c1:
        # PDF 파일 조기 생성
        pdf_path = generate_pdf_report(st.session_state.browser_session_id, meta, top_5)
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as pdf_file:
                st.download_button(
                    label="📥 소장용 PDF 리포트 파일 다운로드",
                    data=pdf_file,
                    file_name=f"CoachKG_Report_{meta['name']}.pdf",
                    mime="application/pdf"
                )
                
    with col2:
        if st.button("🔄 새로 진단 시작하기"):
            # 세션 변수 올인원 포맷 리셋
            st.session_state.step = 1
            st.session_state.user_meta = {}
            st.session_state.card_sorting = {}
            st.session_state.results = []
            st.session_state.browser_session_id = uuid.uuid4().hex[:10]
            st.rerun()