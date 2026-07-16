import os
import urllib.request
from fpdf import FPDF
from datetime import datetime

# 폰트를 임시 저장할 디렉토리 경로 지정
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
FONT_REGULAR_PATH = os.path.join(DATA_DIR, "NanumGothic.ttf")
FONT_BOLD_PATH = os.path.join(DATA_DIR, "NanumGothic-Bold.ttf")

def ensure_korean_fonts():
    """
    한글 나눔고딕 폰트의 존재 여부를 검사하고, 없을 경우 구글 폰트 공인 리포지토리에서 자동 다운로드합니다.
    Streamlit Cloud 배포 시 발생할 수 있는 폰트 누락 리스크를 사전 차단합니다.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # 1. 나눔고딕 Regular 다운로드
    if not os.path.exists(FONT_REGULAR_PATH):
        url_reg = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        try:
            urllib.request.urlretrieve(url_reg, FONT_REGULAR_PATH)
        except Exception as e:
            print(f"[Warning] Regular 폰트 다운로드 실패: {e}")
            
    # 2. 나눔고딕 Bold 다운로드
    if not os.path.exists(FONT_BOLD_PATH):
        url_bold = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf"
        try:
            urllib.request.urlretrieve(url_bold, FONT_BOLD_PATH)
        except Exception as e:
            print(f"[Warning] Bold 폰트 다운로드 실패: {e}")

class CoachKGPDF(FPDF):
    """
    브랜딩 요소(머리말, 꼬리말, 쪽 번호 등)를 포함하기 위해 FPDF 기본 클래스를 확장합니다.
    """
    def header(self):
        # 상단 테두리 선 및 리포트 기본 타이틀 렌더링
        self.set_text_color(120, 120, 120)
        self.set_font("NanumGothic", "", 9)
        self.cell(0, 10, "🧭 CoachKG 강점 동적 내비게이터 - 개인 분석 리포트", align="L", ln=True)
        self.set_draw_color(200, 200, 200)
        self.line(10, 18, 200, 18)
        self.ln(5)

    def footer(self):
        # 하단 여백 위에 바닥글 및 쪽 번호 생성
        self.set_y(-15)
        self.set_draw_color(220, 220, 220)
        self.line(10, self.get_y() - 2, 200, self.get_y() - 2)
        self.set_text_color(150, 150, 150)
        self.set_font("NanumGothic", "", 8)
        self.cell(0, 10, f"Page {self.page_no()} | 본 리포트는 회원가입 없이 생성된 일회성 임시 소장 파일입니다.", align="C")

def generate_pdf_report(session_token, user_meta, top_5_results):
    """
    session_token: 사용자 세션 고유 토큰 (파일 충돌 차단 목적)
    user_meta: {"name": "홍길동", "email": "hong@test.com"}
    top_5_results: 상위 5대 강점 연산 결과 사전 리스트
    """
    # 1. 시스템 폰트 준비
    ensure_korean_fonts()
    
    # 2. PDF 인스턴스 초기화 및 한글 폰트 레지스트리 등록
    pdf = CoachKGPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    
    # fpdf2에 폰트 수동 등록
    pdf.add_font("NanumGothic", "", FONT_REGULAR_PATH)
    pdf.add_font("NanumGothic", "B", FONT_BOLD_PATH)
    
    # 새 페이지 삽입
    pdf.add_page()
    
    # 3. 타이틀 및 사용자 메타데이터 출력
    pdf.set_text_color(44, 62, 80) # 세련된 다크네이비 톤
    pdf.set_font("NanumGothic", "B", 22)
    pdf.cell(0, 15, "🏆 나의 5대 지능형 강점 분석 리포트", ln=True, align="L")
    pdf.ln(2)
    
    # 기본 정보 상자 렌더링
    pdf.set_font("NanumGothic", "", 10)
    pdf.set_text_color(80, 80, 80)
    today_str = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")
    
    pdf.cell(0, 6, f"피진단자 :  {user_meta.get('name', '미기재')} 님", ln=True)
    pdf.cell(0, 6, f"식별 이메일 :  {user_meta.get('email', '미기재')}", ln=True)
    pdf.cell(0, 6, f"진단 일시 :  {today_str}", ln=True)
    pdf.ln(8)
    
    # 안내 메시지
    pdf.set_fill_color(245, 247, 250)
    pdf.set_font("NanumGothic", "", 9.5)
    pdf.set_text_color(50, 50, 50)
    info_text = (
        "아래 강점 정보는 1차 자가 카드 소팅 검증과 2차 정밀 스케일 척도 합산을 통해 도출된 "
        "당신의 상위 5대 핵심 잠재 역량입니다. 온톨로지(Ontology) 기반으로 분석된 개별 강점의 정의와 "
        "과사용 그림자, 그리고 상호보완적이고 유기적인 관계성 역동 지도를 성찰과 성장의 기준으로 삼아보시기 바랍니다."
    )
    pdf.multi_cell(0, 6, info_text, border=0, fill=True, align="L")
    pdf.ln(8)
    
    # [풍부성 보강] 온톨로지 싱크 준비
    from core.assessment import load_ontology
    ontology = load_ontology()
    s_map = {s["code"]: s for s in ontology["strengths"]}
    
    # 4. 상위 5대 강점 상세 데이터 루프 출력
    for idx, r in enumerate(top_5_results, 1):
        # [레이아웃 보완] 3순위 시작 전에 강제로 페이지를 나누어 5순위 끈기/지속력 잘림 문제를 해결합니다.
        if idx == 3:
            pdf.add_page()
            # 2페이지 상단 보조 타이틀 렌더링
            pdf.set_font("NanumGothic", "B", 9)
            pdf.set_text_color(150, 150, 150)
            pdf.cell(0, 6, "CoachKG 강점 동적 내비게이터 - 개인 분석 리포트 (계속)", ln=True, align="R")
            pdf.set_draw_color(220, 224, 230)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(6)
            
        # 각 강점별 헤더 상자 (덕목 및 순위 표시)
        pdf.set_fill_color(230, 240, 250) # 연한 청록색 계열 배경
        pdf.set_font("NanumGothic", "B", 11)
        pdf.set_text_color(41, 128, 185) # 블루 톤 포인트
        
        header_text = f"  [{idx}순위]  {r['name']}  (분석 평점: {r['final_score']} / 5.0)   | 소속 덕목: {r['virtue']}"
        pdf.cell(0, 8, header_text, ln=True, fill=True)
        pdf.ln(1)
        
        # 1) 강점 한 줄 요약
        pdf.set_font("NanumGothic", "B", 9)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(0, 5, "💡 핵심 요약", ln=True)
        
        pdf.set_font("NanumGothic", "", 9)
        pdf.set_text_color(80, 80, 80)
        summary_text = r.get("summary", "상세 요약 설명이 포함되지 않은 강점입니다.")
        pdf.multi_cell(0, 5, summary_text)
        pdf.ln(1)
        
        # 온톨로지 상세 속성 매핑 파싱
        s_detail = s_map.get(r.get("code"), {}) if r.get("code") else {}
        overuse_text = s_detail.get("overuse", "과사용 시 주변과의 불협화음 혹은 번아웃을 유발할 우려가 있으니 성찰해 보시기 바랍니다.")
        
        synergy_list = [s_map[s_code]["name"] for s_code in s_detail.get("synergy_with", []) if s_code in s_map]
        balances_list = [s_map[b_code]["name"] for b_code in s_detail.get("balances", []) if b_code in s_map]
        conflicts_list = [s_map[c_code]["name"] for c_code in s_detail.get("conflicts_with", []) if c_code in s_map]
        
        # 2) [속성 보강 1] 과사용(Overuse) 그림자 기입
        pdf.set_font("NanumGothic", "B", 9)
        pdf.set_text_color(192, 57, 43) # 부드러운 다크레드 경고 톤
        pdf.cell(0, 5, "⚠️ 과사용(Overuse) 위험성 및 그림자", ln=True)
        
        pdf.set_font("NanumGothic", "", 9)
        pdf.set_text_color(80, 80, 80)
        pdf.multi_cell(0, 5, overuse_text)
        pdf.ln(1)
        
        # 3) [속성 보강 2] 유기적 관계망 역동성 기입
        relations_text_parts = []
        if synergy_list:
            relations_text_parts.append(f"🤝 시너지: {', '.join(synergy_list)}")
        if balances_list:
            relations_text_parts.append(f"⚖️ 보완균형: {', '.join(balances_list)}")
        if conflicts_list:
            relations_text_parts.append(f"⚡ 주의상충: {', '.join(conflicts_list)}")
            
        if relations_text_parts:
            pdf.set_font("NanumGothic", "B", 9)
            pdf.set_text_color(39, 174, 96) # 차분한 그린 톤 포인트
            pdf.cell(0, 5, "🔗 유기적 지식 관계망 역동성", ln=True)
            
            pdf.set_font("NanumGothic", "", 8.5)
            pdf.set_text_color(100, 100, 100)
            relation_str = "  |  ".join(relations_text_parts)
            pdf.cell(0, 5, f"  {relation_str}", ln=True)
            pdf.ln(1)
        
        # 4) 키워드 나열
        keywords = r.get("keywords", [])
        if keywords:
            pdf.set_font("NanumGothic", "B", 9)
            pdf.set_text_color(50, 50, 50)
            pdf.cell(0, 5, "🏷️ 연관 키워드", ln=True)
            
            pdf.set_font("NanumGothic", "", 8.5)
            pdf.set_text_color(100, 100, 100)
            keyword_str = ", ".join(keywords)
            pdf.cell(0, 5, f"  {keyword_str}", ln=True)
            
        pdf.ln(4) # 다음 강점 상자와의 정교한 여백 조절
        
    # 5. 임시 격리 파일명으로 파일 쓰기
    output_filename = f"report_{session_token}.pdf"
    # 프로젝트 루트에 임시 리포트 빌드 저장
    output_pdf_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), output_filename)
    
    pdf.output(output_pdf_path)
    return output_pdf_path