# app.py
import streamlit as st
import streamlit.components.v1 as components  # 표준 HTML 컴포넌트 수입
import base64
import uuid
import os
import json
import time
import tempfile

# 모듈 수입
from database.local_db import init_local_db, save_user_run, get_user_history_by_email
from database.neo4j_sync import sync_to_neo4j_safely
from core.assessment import calculate_scores, load_ontology
from core.graph_visual import build_pyvis_graph
from core.report_gen import generate_pdf_report
from core.cleaner import clean_temporary_files  # 1단계 가비지 컬렉터 수입

# =============================================================================
# 1. STREAMLIT 규정 준수 영역 (최우선 실행)
# =============================================================================
st.set_page_config(page_title="CoachKG Navigator", layout="wide", page_icon="🧭")

# 스타일 보완을 위한 임시 CSS 패치
st.markdown("""
    <style>
    .reportview-container .main .block-container{ max-width: 1200px; }
    .stButton>button { width: 100%; border-radius: 6px; }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. 세션 상태 관리 모델 정의 및 초기화
# =============================================================================
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
if "bypass_db" not in st.session_state:
    st.session_state.bypass_db = False
if "last_cleanup_time" not in st.session_state:
    st.session_state.last_cleanup_time = 0

# B, C그룹 점진적 무한 전수조사 제어용 스위치 정의
if "show_all_b" not in st.session_state:
    st.session_state.show_all_b = False
if "show_all_c" not in st.session_state:
    st.session_state.show_all_c = False

# =============================================================================
# 3. [1단계] 임시 파일 가비지 컬렉터 실행 제어
# =============================================================================
CLEANUP_INTERVAL_SECONDS = 1800 
current_time = time.time()

if current_time - st.session_state.last_cleanup_time > CLEANUP_INTERVAL_SECONDS:
    try:
        deleted, failed = clean_temporary_files(target_dir=tempfile.gettempdir(), max_age_seconds=3600)
        st.session_state.last_cleanup_time = current_time
        if deleted > 0:
            print(f"[System GC] 임시 파일 {deleted}개 청소 완료")
    except Exception as gc_err:
        print(f"[System GC] 예외 방어됨: {gc_err}")

# 앱 최초 실행 시 SQLite 로컬 로그 테이블 초기화 보장
init_local_db()

# 🧭 타이틀 헤더
st.title("🧭 동적 강점 내비게이터")
st.caption("비회원 개방형 - 3단계 하이브리드 강점 가치 지도 진단 서비스")
st.markdown("---")


# =============================================================================
# STEP 1: 익명 식별 정보 기입 및 1차 카드 소팅 (개선형 3분류 카드 뷰)
# =============================================================================
if st.session_state.step == 1:
    st.subheader("1단계: 정보 입력 및 자가 강점 소팅")
    st.info("💡 별도의 비밀번호가 필요 없는 완전 공개형 서비스입니다. 기재하신 정보는 중복 데이터 방지와 PDF 리포트 기입, 이력 복원에만 활용됩니다.")
    
    ontology = load_ontology()
    
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
        st.caption("💡 각 탭(대덕목)을 돌아가면서 클릭하여야 전체 강점을 살펴보고 선택할 수 있습니다.")
        st.caption("💡 '과거 진단 이력 복원' 기능을 통해 이전 기록을 불러올 수도 있습니다.")
        
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
                                index=2,
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

    st.markdown("---")
    with st.expander("🔍 내 이전 진단 이력 즉시 복원하기"):
        st.write("과거에 이메일을 기재하여 진행했던 진단 이력이 있다면, 아래에 동일한 이메일을 기입하여 실시간으로 복원할 수 있습니다.")
        search_email = st.text_input("식별용 이메일 입력", key="search_email_input")
        if st.button("과거 기록 추적"):
            if search_email:
                history = get_user_history_by_email(search_email)
                if history:
                    st.success(f"과거 데이터 로그를 발견했습니다.")
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


# =============================================================================
# STEP 2: 축소 지표 검증 (리커트 척도 평정)
# =============================================================================
elif st.session_state.step == 2:
    st.subheader("2단계: 선별 대표 강점 입증 검증")
    meta = st.session_state.user_meta
    st.write(f"✍️ **{meta['name']}님**, 고르신 핵심 강점들을 실제 자주 실천하고 보람을 느끼는지 척도 검증을 수행합니다.")
    
    ontology = load_ontology()
    s_map = {s["code"]: s for s in ontology["strengths"]}
    
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
            
            score_val = st.slider(
                "전혀 그렇지 않다 (1)  ~  매우 그렇다 (5)", 
                min_value=1, max_value=5, value=3, key=f"q_{code}"
            )
            survey_responses[code] = score_val
            st.markdown("<br>", unsafe_allow_html=True)
            
        submit_step2 = st.form_submit_button("최종 분석 완료 및 우주 지도 펼치기", key="btn_submit_step2")
        
    if submit_step2:
        transition_to_step3 = False
        st.write("🔄 **[디버그 로그]** 제출 버튼 동작 감지됨. 분석 연산을 시작합니다...")
        
        try:
            st.write("🔢 1. 강점 온톨로지 가중치 합산 연산 수행 중...")
            raw_results = calculate_scores(st.session_state.card_sorting, survey_responses)
            st.session_state.results = raw_results
            st.write("✅ 1단계 강점 분석 연산 완료!")
            
            transition_to_step3 = True
            
            if not st.session_state.get("bypass_db", False):
                try:
                    st.write("💾 2. 분석 로그 로컬 SQLite3 DB 적재 중...")
                    save_user_run(
                        st.session_state.browser_session_id, 
                        meta["email"], 
                        meta["name"], 
                        raw_results
                    )
                    st.write("✅ 2단계 SQLite3 백업 완료!")
                except Exception as db_err:
                    st.warning(f"⚠️ 경고: 로컬 DB 로그 백업 중 지연이 발생했으나 분석은 진행됩니다. ({db_err})")
                
                try:
                    st.write("🌐 3. Neo4j AuraDB 클라우드 동기화 중...")
                    top_5_for_sync = [
                        {"code": r["code"], "final_score": r["final_score"]} 
                        for r in raw_results if r["group"] == "A"
                    ][:5]
                    sync_to_neo4j_safely(meta["email"], meta["name"], top_5_for_sync)
                    st.write("✅ 3단계 외부 Neo4j 싱크 완료!")
                except Exception as sync_err:
                    st.warning(f"⚠️ 경고: 원격 GraphDB 동기화에 지연이 발생했으나 분석은 진행됩니다. ({sync_err})")
            else:
                st.warning("⚠️ **[디버그 모드]** DB 백업 및 API 동기화 단계를 우회(Bypass)했습니다.")
                
        except Exception as calc_err:
            st.error("❌ 분석 처리 중 치명적인 예외가 발생했습니다.")
            st.exception(calc_err)
            
        if transition_to_step3:
            st.write("🔄 분석 성공. 3단계 결과 지형도로 즉시 이동합니다.")
            st.session_state.step = 3
            st.rerun()


# =============================================================================
# STEP 3: 동적 결과 분석 리포트 및 시각화 탐색
# =============================================================================
elif st.session_state.step == 3:
    meta = st.session_state.user_meta
    results = st.session_state.results
    
    top_5 = [r for r in results if r["group"] == "A"][:5]
    if not top_5:
        top_5 = results[:5]
        
    st.subheader(f"🏆 {meta['name']}님의 지능형 강점 지도 피드백")
    
    # 상위 1차 지형도 및 상세 정보 열기
    col1, col2 = st.columns([1.2, 1])
    
    with col1:
        st.write("### 🌌 나의 강점 지식 지도")
        st.caption("대표 강점 5종과 이들의 소속 덕목(삼각형), 그리고 온톨로지 기반의 잠재적 보완/시너지 지형도입니다.")
        
        # [Phase 3] 동적 지식 필터 슬라이더 배치
        explore_depth = st.slider(
            "🧭 강점 관계도 탐색 깊이 (Relationship Depth)", 
            min_value=1, 
            max_value=2, 
            value=1,
            help="1단계는 내 핵심 강점들의 직접 연계된 요소만 보여줍니다. 2단계는 그 너머의 간접적인 연계 관계까지 온톨로지를 확장하여 심층 분석 지형을 구성합니다."
        )
        
        # 깔끔하고 정돈된 CSS 기반 범례(Legend) 레이어 출력
        st.markdown("""
        <div style="background-color: #f8f9fa; padding: 12px; border-radius: 8px; border: 1.5px solid #e2e8f0; font-size: 0.85em; line-height: 1.6; margin-bottom: 15px; color: #2c3e50;">
            <strong>🧭 강점 지형도 범례 (Legend)</strong><br>
            🟢 <b>초록 원:</b> 나의 대표 강점 (크기=점수) | 
            ▲ <b>보라 삼각:</b> 상위 대덕목 | 
            🔵 <b>남색 원:</b> 1차 이웃 강점 |
            🔘 <b>회색 원:</b> 2차 간접 연계 강점 (심층)<br>
            <span style="color:#e2e8f0;">━━</span> 회색선: 덕목 소속 관계 | 
            <span style="color:#2ecc71;">━━</span> 초록선: 상호 시너지 | 
            <span style="color:#e67e22;">- -</span> 주황 대시선: 상호 보완 균형 | 
            <span style="color:#e74c3c;">····</span> 빨간 점선: 주의 필요 상충
        </div>
        """, unsafe_allow_html=True)
        
        # =====================================================================
        # [철통 격리 보안막] 그래프 연산이 폭발하더라도 메인 쓰레드는 영향 받지 않음
        # =====================================================================
        html_path = None
        with st.spinner("🌌 강점 지형 네트워크 지도를 동적으로 그리는 중..."):
            html_path = build_pyvis_graph(
                session_id=st.session_state.browser_session_id,
                top_5=top_5,
                depth=explore_depth
            )
        
        # [최종 무결성 패치] sandbox 보안 한계를 돌파하기 위해 Base64 주입(st.iframe)을 버리고
        # Streamlit 공식 Native HTML 렌더러인 components.html 방식을 단독 채택합니다.
        if html_path:
            try:
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_data = f.read()
                
                # unpkg CDN 자바스크립트를 차단하지 않고 정상 로드하는 유일하게 신뢰받는 통로
                components.html(html_data, height=600, scrolling=False)
                
            except Exception as e:
                st.error(f"지도를 화면에 표시하는 과정에서 오류가 발생했습니다: {e}")
        else:
            st.warning(
                "⚠️ 지식 관계 지형도를 안전하게 그리지 못했습니다.\n\n"
                "사용하시는 운영체제나 서버 네트워크가 PyVis 종속성 파일을 읽지 못하는 환경일 수 있습니다. "
                "그러나 결과 보존과 우측의 상세 해석 정보, 하단의 PDF 보고서 정상 활용에는 아무런 지장이 없습니다."
            )
                
    with col2:
        st.write("### 📑 최상위 강점 상세 정보")
        st.caption("💡 각 강점을 클릭하면 온톨로지(Graph) 기반의 과사용 위험성과 유기적 보완/상충 맥락을 조회할 수 있습니다.")
        
        ontology = load_ontology()
        s_map = {s["code"]: s for s in ontology["strengths"]}
        
        for idx, r in enumerate(top_5, 1):
            s_detail = s_map.get(r["code"], {})
            overuse_text = s_detail.get("overuse", "이 강점을 지나치게 고집할 경우 주변과의 마찰이 발생할 수 있으니 유의하십시오.")
            
            synergy_list = [s_map[s_code]["name"] for s_code in s_detail.get("synergy_with", []) if s_code in s_map]
            balances_list = [s_map[b_code]["name"] for b_code in s_detail.get("balances", []) if b_code in s_map]
            conflicts_list = [s_map[c_code]["name"] for c_code in s_detail.get("conflicts_with", []) if c_code in s_map]
            
            with st.expander(f"**{idx}순위 : {r['name']}** (분석 평점 : {r['final_score']} / 5.0)"):
                st.write(f"📂 **소속 덕목** : {r['virtue']}")
                st.write(f"💬 **핵심 요약** : {r['summary']}")
                if r['keywords']:
                    st.write(f"🏷️ **연관 키워드** : {', '.join(r['keywords'])}")
                
                st.markdown("---")
                st.markdown(f"⚠️ **과사용(Overuse) 위험성 및 그림자:**")
                st.info(overuse_text)
                
                if synergy_list or balances_list or conflicts_list:
                    st.markdown("🔗 **유기적 지식 관계망 역동성:**")
                    if synergy_list:
                        st.write(f"- 🤝 **시너지 효과 (Synergy):** {', '.join(synergy_list)}")
                    if balances_list:
                        st.write(f"- ⚖️ **상호 보완적 균형 (Balances):** {', '.join(balances_list)}")
                    if conflicts_list:
                        st.write(f"- ⚡ **주의할 대립/상충 (Conflicts):** {', '.join(conflicts_list)}")

    # =============================================================================
    # [Phase 2] 보완 강점(Group B) 및 일반/미개발 강점(Group C) 입체 해석 레이어
    # =============================================================================
    st.markdown("---")
    st.write("### ⚖️ 자가 소팅 기반 강점 지형 분석 (Group B & C)")
    st.caption("대표 강점(A) 외에, 자가 소팅 과정에서 정비된 보완 강점과 일반/미개발 강점에 대한 맞춤형 행동 양식 제언입니다.")

    group_b_results = [r for r in results if r["group"] == "B"]
    group_c_results = [r for r in results if r["group"] == "C"]

    tab_b, tab_c = st.tabs(["🟡 보완적 균형 지대 (Group B)", "🔴 일반 및 미개발 지대 (Group C)"])

    ontology = load_ontology()
    s_map = {s["code"]: s for s in ontology["strengths"]}

    def get_contextual_interpretation(code, group_type):
        s_detail = s_map.get(code, {})
        if "interpretation" in s_detail and group_type in s_detail["interpretation"]:
            return s_detail["interpretation"][group_type]
        
        s_name = s_detail.get("name", "해당 강점")
        if group_type == "complementary":
            return f"이 강점({s_name})은 현재 보완 장치 역할을 수행하고 있습니다. 핵심 강점이 과사용되어 독단이나 피로감을 낳을 때, 이 보완 강점을 의식적으로 환기하여 성과의 균형(Balances)을 잡아주는 완충제로 활용하시기 바랍니다."
        else:
            return f"이 강점({s_name})은 현재 일반 또는 미개발 영역에 머무르고 있습니다. 이를 극복하기 위해 과도한 에너지를 투입하기보다는, 이 강점을 핵심 무기로 보유한 동료를 찾아 협업(Complementary Partnership) 구도를 짜는 것이 현실적으로 유용합니다."

    with tab_b:
        if group_b_results:
            st.write("💡 **보완 강점 활용법:** 핵심 강점의 부작용을 통제하고 완충 작용을 해주는 예비 가치 자원입니다.")
            
            # [개선 4] 동적 무한 전수 펼치기 인터랙션 적용
            limit_b = len(group_b_results) if st.session_state.show_all_b else 3
            for idx, r in enumerate(group_b_results[:limit_b], 1):
                with st.container(border=True):
                    st.markdown(f"**🟡 {r['name']}** (소속 덕목: {r['virtue']})")
                    st.markdown(get_contextual_interpretation(r["code"], "complementary"))
            
            # 점진적 전수 노출 제어 버튼
            if not st.session_state.show_all_b:
                if st.button("➕ 보완 강점 전체 펼쳐보기 (전수 조사)", key="btn_show_all_b"):
                    st.session_state.show_all_b = True
                    st.rerun()
            else:
                if st.button("➖ 보완 강점 요약해 보기 (3개만 보기)", key="btn_hide_all_b"):
                    st.session_state.show_all_b = False
                    st.rerun()
        else:
            st.info("자가 소팅 시 '보완 강점(B)'으로 분류된 항목이 없습니다.")

    with tab_c:
        if group_c_results:
            st.write("💡 **미개발 영역 대응법:** 약점을 억지로 극복하기보다 타인과의 협업 및 도구 사용을 통한 우회 전략을 추천합니다.")
            
            # [개선 4] 동적 무한 전수 펼치기 인터랙션 적용
            limit_c = len(group_c_results) if st.session_state.show_all_c else 3
            for idx, r in enumerate(group_c_results[:limit_c], 1):
                with st.container(border=True):
                    st.markdown(f"**🔴 {r['name']}** (소속 덕목: {r['virtue']})")
                    st.markdown(get_contextual_interpretation(r["code"], "undeveloped"))
            
            # 점진적 전수 노출 제어 버튼
            if not st.session_state.show_all_c:
                if st.button("➕ 일반/미개발 강점 전체 펼쳐보기 (전수 조사)", key="btn_show_all_c"):
                    st.session_state.show_all_c = True
                    st.rerun()
            else:
                if st.button("➖ 일반/미개발 강점 요약해 보기 (3개만 보기)", key="btn_hide_all_c"):
                    st.session_state.show_all_c = False
                    st.rerun()
        else:
            st.info("자가 소팅 시 '일반/미개발 강점(C)'으로 분류된 항목이 없습니다.")

    # =============================================================================
    # [최종 액션 영역] PDF 다운로드 및 리셋 버튼 (화면 최하단에 배치)
    # =============================================================================
    st.markdown("---")
    c1, c2 = st.columns(2)
    
    with c1:
        try:
            # [개선 4] PDF에 전수 데이터를 동적으로 처리할 수 있도록 results(전체 리스트)를 주입합니다.
            pdf_path = generate_pdf_report(st.session_state.browser_session_id, meta, results)
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as pdf_file:
                    st.download_button(
                        label="📥 소장용 PDF 리포트 파일 다운로드",
                        data=pdf_file,
                        file_name=f"CoachKG_Report_{meta['name']}.pdf",
                        mime="application/pdf"
                    )
        except Exception as pdf_error:
            st.error("⚠️ PDF 리포트 빌드 중 일시적 네트워크 지연이 관측되었습니다. (왼쪽 지도는 정상 가동 중)")
            st.caption(f"상세 정보: {pdf_error}")
                
    with c2:
        if st.button("🔄 새로 진단 시작하기"):
            st.session_state.step = 1
            st.session_state.user_meta = {}
            st.session_state.card_sorting = {}
            st.session_state.results = []
            st.session_state.show_all_b = False
            st.session_state.show_all_c = False
            st.session_state.browser_session_id = uuid.uuid4().hex[:10]
            st.rerun()