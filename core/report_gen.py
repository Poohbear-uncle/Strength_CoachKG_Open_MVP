import os
import tempfile
from datetime import datetime
from fpdf import FPDF

# [보완] Streamlit Cloud 백그라운드 드로잉을 위한 Matplotlib 및 NetworkX 탑재
import matplotlib
matplotlib.use('Agg')  # 가상 GUI 서버가 없는 서버용 논-인터랙티브 백엔드 강제 설정
import matplotlib.pyplot as plt
import networkx as nx

# -----------------------------------------------------------------------------
# 🌐 [자가완비형 한글 폰트 자동 빌드 및 절대 경로 정의]
# -----------------------------------------------------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

FONT_DIR = os.path.join(project_root, "data", "fonts")
FONT_REGULAR_PATH = os.path.join(FONT_DIR, "NanumGothic.ttf")
FONT_BOLD_PATH = os.path.join(FONT_DIR, "NanumGothicBold.ttf")

def ensure_korean_fonts():
    """
    한글 나눔고딕 폰트 파일이 유실되었거나 없을 경우,
    서버 환경에서 구글 공식 폰트 저장소로부터 실시간으로 다운로드하여 구동 안정성을 확보합니다.
    """
    os.makedirs(FONT_DIR, exist_ok=True)
    import urllib.request
    
    # 일반 폰트 확인 및 자동 다운로드
    if not os.path.exists(FONT_REGULAR_PATH):
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        try:
            urllib.request.urlretrieve(url, FONT_REGULAR_PATH)
        except Exception as e:
            pass
            
    # 볼드 폰트 확인 및 자동 다운로드
    if not os.path.exists(FONT_BOLD_PATH):
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf"
        try:
            urllib.request.urlretrieve(url, FONT_BOLD_PATH)
        except Exception as e:
            pass

# -----------------------------------------------------------------------------
# 📑 [CoachKG 전용 PDF 커스텀 헤더/푸터 드로잉 클래스]
# -----------------------------------------------------------------------------
class CoachKGPDF(FPDF):
    def header(self):
        """매 페이지 상단에 정갈한 레이아웃 가이드 선과 보조 타이틀 인쇄"""
        self.set_font("NanumGothic", "", 8.5)
        self.set_text_color(150, 150, 150)
        self.cell(0, 6, "CoachKG 강점 동적 내비게이터 - 개인 분석 리포트", ln=True, align="L")
        
        # 헤더 보조 가이드 씬 실선 드로잉
        self.set_draw_color(220, 224, 230)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)
        
    def footer(self):
        """매 페이지 하단에 페이지 번호 및 저작권 명세 배치 (하단 마진 15mm 고정 보호)"""
        self.set_y(-15)
        self.set_font("NanumGothic", "", 8.5)
        self.set_text_color(150, 150, 150)
        
        # 푸터 상단 가이드 씬 실선 드로잉
        self.set_draw_color(220, 224, 230)
        self.line(10, self.get_y() - 1, 200, self.get_y() - 1)
        
        footer_text = f"Page {self.page_no()} | 본 리포트는 회원가입 없이 생성된 일회성 임시 소장 파일입니다."
        self.cell(0, 10, footer_text, align="C")

# -----------------------------------------------------------------------------
# 🏆 [메인 분석 PDF 리포트 파일 생성 엔진]
# -----------------------------------------------------------------------------
def generate_pdf_report(session_token, user_meta, top_5_results):
    """
    session_token: 사용자 세션 고유 토큰 (파일 충돌 차단 목적)
    user_meta: {"name": "홍길동", "email": "hong@test.com"}
    top_5_results: 상위 5대 강점 연산 결과 사전 리스트
    """
    # 1. 시스템 폰트 준비 (유실 시 자동 웹 다운로드 작동)
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
    
    # 온톨로지 원천 데이터 로드 및 매핑
    from core.assessment import load_ontology
    ontology = load_ontology()
    s_map = {s["code"]: s for s in ontology["strengths"]}
    
    # 4. 상위 5대 강점 상세 데이터 루프 출력
    for idx, r in enumerate(top_5_results, 1):
        # 3순위 시작 전에 강제로 페이지를 나누어 잘림 현상을 원천 방지
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
        pdf.set_fill_color(230, 240, 250)
        pdf.set_font("NanumGothic", "B", 11)
        pdf.set_text_color(41, 128, 185)
        
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
        
        # 원천 데이터에 존재하는 모든 관계망 정보를 가져옵니다.
        synergy_list = [s_map[s_code]["name"] for s_code in s_detail.get("synergy_with", []) if s_code in s_map]
        balances_list = [s_map[b_code]["name"] for b_code in s_detail.get("balances", []) if b_code in s_map]
        conflicts_list = [s_map[c_code]["name"] for c_code in s_detail.get("conflicts_with", []) if c_code in s_map]
        
        # 2) [속성 보강 1] 과사용(Overuse) 그림자 기입 (음과 양의 보강)
        pdf.set_font("NanumGothic", "B", 9)
        pdf.set_text_color(192, 57, 43)
        pdf.cell(0, 5, "⚠️ 과사용(Overuse) 위험성 및 그림자", ln=True)
        
        pdf.set_font("NanumGothic", "", 9)
        pdf.set_text_color(80, 80, 80)
        pdf.multi_cell(0, 5, overuse_text)
        pdf.ln(1)
        
        # 3) [속성 보강 2] 유기적 관계망 역동성 기입 (원천 데이터에 존재하는 것 일괄 출력)
        relations_text_parts = []
        if synergy_list:
            relations_text_parts.append(f"🤝 시너지: {', '.join(synergy_list)}")
        if balances_list:
            relations_text_parts.append(f"⚖️ 보완균형: {', '.join(balances_list)}")
        if conflicts_list:
            relations_text_parts.append(f"⚡ 주의상충: {', '.join(conflicts_list)}")
            
        if relations_text_parts:
            pdf.set_font("NanumGothic", "B", 9)
            pdf.set_text_color(39, 174, 96)
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
            
        pdf.ln(4)
        
    # =========================================================================
    # 5. [신규 이식: 대안 B] NetworkX + Matplotlib 기반 백그라운드 정적 지도 생성 및 인쇄
    # =========================================================================
    pdf.add_page()
    pdf.set_font("NanumGothic", "B", 14)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 10, "🌌 나의 5대 지능형 강점 네트워크 지형도", ln=True, align="L")
    pdf.ln(5)
    
    # 1) NetworkX 빈 그래프 생성
    G = nx.Graph()
    top_codes = [r["code"] for r in top_5_results]
    added_nodes = set(top_codes)
    
    # 대표 노드 및 관계 데이터 구축
    node_colors = []
    node_labels = {}
    
    for r in top_5_results:
        code = r["code"]
        G.add_node(code)
        node_colors.append('#2ecc71') # 대표 강점: 연록색
        node_labels[code] = r["name"]
        
        # 소속 덕목 노드 연결 준비
        virtue_name = r["virtue"]
        if virtue_name not in G:
            G.add_node(virtue_name)
            node_colors.append('#9b5de5') # 덕목: 보라색
            node_labels[virtue_name] = virtue_name
        G.add_edge(code, virtue_name, color='#bdc3c7', weight=2, style='solid')
        
        # 주변부 연계 노드 확장 탐색
        s_detail = s_map.get(code, {})
        related = s_detail.get("synergy_with", []) + s_detail.get("balances", []) + s_detail.get("conflicts_with", [])
        for rel_code in related:
            if rel_code not in added_nodes and rel_code in s_map:
                G.add_node(rel_code)
                node_colors.append('#dfe6e9') # 보완 연계 영역: 밝은 회색
                node_labels[rel_code] = s_map[rel_code]["name"]
                added_nodes.add(rel_code)
                
    # 간선 색상 및 스타일 매핑
    edge_colors = []
    edge_styles = []
    
    for r in top_5_results:
        code = r["code"]
        s_detail = s_map.get(code, {})
        
        # 덕목 소속선은 회색 실선 처리
        for u, v, d in G.edges(data=True):
            if d.get('color') == '#bdc3c7':
                continue
                
        # 시너지 관계선 (초록 실선)
        for syn in s_detail.get("synergy_with", []):
            if G.has_node(syn) and not G.has_edge(code, syn):
                G.add_edge(code, syn, color='#2ecc71', style='solid')
                
        # 보완균형 관계선 (주황색 대시선)
        for bal in s_detail.get("balances", []):
            if G.has_node(bal) and not G.has_edge(code, bal):
                G.add_edge(code, bal, color='#e67e22', style='dashed')
                
        # 주의상충 관계선 (빨간색 점선)
        for con in s_detail.get("conflicts_with", []):
            if G.has_node(con) and not G.has_edge(code, con):
                G.add_edge(code, con, color='#e74c3c', style='dotted')

    # 간선 스타일 목록 수집
    edges = G.edges(data=True)
    colors = [edge[2].get('color', '#bdc3c7') for edge in edges]
    styles = [edge[2].get('style', 'solid') for edge in edges]
    
    # 백그라운드 캔버스에 그리기 작업 수행 (한글 폰트 적용 필수)
    plt.figure(figsize=(7.5, 6), dpi=300)
    plt.rcParams['font.family'] = 'NanumGothic' # 리눅스 시스템 폰트명 바인딩
    plt.rcParams['axes.unicode_minus'] = False
    
    pos = nx.spring_layout(G, k=0.8, iterations=50) # 가시성 높은 탄성 레이아웃 배치
    
    # 노드 그리기
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=800)
    # 라벨 그리기 (노드 내부 혹은 부근에 한글 매핑)
    nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=8, font_weight='bold')
    
    # 스타일별 간선 드로잉
    for edge, color, style in zip(edges, colors, styles):
        nx.draw_networkx_edges(
            G, pos, 
            edgelist=[(edge[0], edge[1])], 
            edge_color=color, 
            style=style, 
            width=1.5
        )
        
    plt.title("🧭 CoachKG 강점 시너제틱 지형망", fontsize=11, fontweight='bold', pad=15)
    plt.axis('off') # 불필요한 축 제거
    plt.tight_layout()
    
    # 2) 임시 이미지 파일로 드로잉 결과 저장
    temp_img_name = f"temp_mat_{session_token}.png"
    temp_dir = tempfile.gettempdir()
    temp_img_path = os.path.join(temp_dir, temp_img_name)
    plt.savefig(temp_img_path, format="png", bbox_inches='tight')
    plt.close() # 메모리 누수 방지
    
    # 3) PDF에 정적 고해상도 지형망 파일 내장 및 하단 마진 배치
    if os.path.exists(temp_img_path):
        pdf.image(temp_img_path, x=15, y=35, w=180)
        # 이미지 삽입 후 사용이 끝난 임시 파일은 디스크 정리를 위해 물리적 소거
        try:
            os.remove(temp_img_path)
        except:
            pass

    # 6. 임시 격리 파일명으로 최종 PDF 쓰기
    output_filename = f"report_{session_token}.pdf"
    output_pdf_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), output_filename)
    
    pdf.output(output_pdf_path)
    return output_pdf_path