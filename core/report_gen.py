import os
import tempfile
from datetime import datetime
from fpdf import FPDF

# Streamlit Cloud 백그라운드 드로잉을 위한 Matplotlib 및 NetworkX 탑재
import matplotlib
matplotlib.use('Agg')  # 가상 GUI 서버가 없는 서버용 논-인터랙티브 백엔드 강제 설정
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm  # Matplotlib 폰트 직접 지정을 위해 주입
import networkx as nx

# 폰트 탐색 경로 정의
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

FONT_DIR = os.path.join(project_root, "data", "fonts")
FONT_REGULAR_PATH = os.path.join(FONT_DIR, "NanumGothic.ttf")
FONT_BOLD_PATH = os.path.join(FONT_DIR, "NanumGothic-Bold.ttf")

# Linux OS 패키지(packages.txt) 설치 시 매핑되는 시스템 기본 경로
SYSTEM_FONT_REGULAR = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
SYSTEM_FONT_BOLD = "/usr/share/fonts/truetype/nanum/NanumGothic-Bold.ttf"

def ensure_korean_fonts():
    """
    한글 나눔고딕 폰트 파일이 손상되었거나 없을 경우 구글 저장소에서 다운로드합니다.
    """
    # 1. 시스템 자체 폰트가 설치되어 있다면 즉시 통과
    if os.path.exists(SYSTEM_FONT_REGULAR) and os.path.exists(SYSTEM_FONT_BOLD):
        print("[INFO] 리눅스 시스템 폰트(fonts-nanum)가 이미 감지되어 다운로드를 건너뜁니다.")
        return

    os.makedirs(FONT_DIR, exist_ok=True)
    import urllib.request
    
    targets = [
        (FONT_REGULAR_PATH, "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"),
        (FONT_BOLD_PATH, "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf")
    ]
    
    for path, url in targets:
        # 파일이 비정상적으로 작다면 손상된 파일로 간주하고 삭제
        if os.path.exists(path) and os.path.getsize(path) < 1000000:
            try:
                os.remove(path)
                print(f"[WARN] 비정상적이거나 손상된 폰트 파일을 감지하여 삭제했습니다: {path}")
            except Exception as delete_err:
                print(f"[ERROR] 기존 손상 폰트 제거 실패: {delete_err}")
                
        if not os.path.exists(path):
            try:
                print(f"[INFO] 폰트 다운로드 시작: {url} -> {path}")
                urllib.request.urlretrieve(url, path, timeout=10)
                print(f"[INFO] 폰트 다운로드 성공: {path} (크기: {os.path.getsize(path)} bytes)")
            except Exception as e:
                print(f"[ERROR] 폰트 실시간 다운로드 실패: {e}")
                # 다운로드 도중 깨진 파편 파일이 있다면 정리
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass

# [CoachKG 전용 PDF 커스텀 헤더/푸터 드로잉 클래스]
class CoachKGPDF(FPDF):
    def __init__(self, font_family="Helvetica", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_font_family = font_family

    def header(self):
        title_text = "CoachKG Strength Navigator - Personal Report" if self.custom_font_family == "Helvetica" else "CoachKG 강점 동적 내비게이터 - 개인 분석 리포트"
        self.set_font(self.custom_font_family, "", 8.5)
        self.set_text_color(150, 150, 150)
        self.cell(0, 6, title_text, ln=True, align="L")
        self.set_draw_color(220, 224, 230)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)
        
    def footer(self):
        self.set_y(-15)
        self.set_font(self.custom_font_family, "", 8.5)
        self.set_text_color(150, 150, 150)
        self.set_draw_color(220, 224, 230)
        self.line(10, self.get_y() - 1, 200, self.get_y() - 1)
        
        footer_text = f"Page {self.page_no()} | Temp Download File" if self.custom_font_family == "Helvetica" else f"Page {self.page_no()} | 본 리포트는 회원가입 없이 생성된 일회성 임시 소장 파일입니다."
        self.cell(0, 10, footer_text, align="C")

# [메인 분석 PDF 리포트 파일 생성 엔진]
def generate_pdf_report(session_token, user_meta, top_5_results):
    ensure_korean_fonts()
    
    font_family = "NanumGothic"
    active_regular_path = None
    active_bold_path = None
    
    # 1. 폰트 물리 경로 스캔 및 크기 무결성 검증
    if os.path.exists(SYSTEM_FONT_REGULAR) and os.path.exists(SYSTEM_FONT_BOLD):
        active_regular_path = SYSTEM_FONT_REGULAR
        active_bold_path = SYSTEM_FONT_BOLD
        print("[INFO] PDF 렌더링에 리눅스 시스템 패키지 폰트 경로를 사용합니다.")
    elif (os.path.exists(FONT_REGULAR_PATH) and os.path.exists(FONT_BOLD_PATH) and 
          os.path.getsize(FONT_REGULAR_PATH) > 1000000 and os.path.getsize(FONT_BOLD_PATH) > 1000000):
        active_regular_path = FONT_REGULAR_PATH
        active_bold_path = FONT_BOLD_PATH
        print("[INFO] PDF 렌더링에 로컬 레포지토리 커밋 폰트 경로를 사용합니다.")
    else:
        print("[WARN] 유효한 한글 나눔고딕 폰트 경로를 확보하지 못했습니다. Helvetica로 폴백합니다.")

    # 2. PDF 엔진 기동 및 폰트 최종 등록
    if active_regular_path and active_bold_path:
        try:
            pdf = CoachKGPDF(font_family="NanumGothic")
            pdf.set_auto_page_break(auto=True, margin=20)
            pdf.add_font("NanumGothic", style="", fname=active_regular_path)
            pdf.add_font("NanumGothic", style="B", fname=active_bold_path)
        except Exception as e:
            print(f"[ERROR] FPDF add_font 과정에서 실패하여 Helvetica로 최종 전환합니다: {e}")
            font_family = "Helvetica"
            pdf = CoachKGPDF(font_family="Helvetica")
            pdf.set_auto_page_break(auto=True, margin=20)
    else:
        font_family = "Helvetica"
        pdf = CoachKGPDF(font_family="Helvetica")
        pdf.set_auto_page_break(auto=True, margin=20)
        
    # 헬베티카 상태라면 안전하게 영문 경고 페이지로 우회하여 충돌 방지
    def clean(text):
        if font_family == "Helvetica":
            return "".join(c if ord(c) < 128 else "?" for c in str(text))
        return str(text)
    
    pdf.add_page()
    
    # 타이틀 출력
    pdf.set_text_color(44, 62, 80)
    pdf.set_font(font_family, "B", 22)
    pdf.cell(0, 15, clean("🏆 나의 5대 지능형 강점 분석 리포트"), ln=True, align="L")
    pdf.ln(2)
    
    # 기본 정보 상자 렌더링
    pdf.set_font(font_family, "", 10.5)
    pdf.set_text_color(80, 80, 80)
    today_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    pdf.cell(0, 6, clean(f"피진단자 성함 : {user_meta.get('name', '미기재')} 님"), ln=True)
    pdf.cell(0, 6, clean(f"이메일 계정 : {user_meta.get('email', '미기재')}"), ln=True)
    pdf.cell(0, 6, clean(f"진단 시각 : {today_str}"), ln=True)
    pdf.ln(8)
    
    # 안내 메시지
    pdf.set_fill_color(245, 247, 250)
    pdf.set_font(font_family, "", 10)
    pdf.set_text_color(50, 50, 50)
    info_text = (
        "This is a digital report based on your top 5 core strengths. Please use this to reflect on your potentials."
        if font_family == "Helvetica" else
        "아래 강점 정보는 1차 자가 카드 소팅 검증과 2차 정밀 스케일 척도 합산을 통해 도출된 "
        "당신의 상위 5대 핵심 잠재 역량입니다. 온톨로지(Ontology) 기반으로 분석된 개별 강점의 정의와 "
        "과사용 그림자, 그리고 상호보완적이고 유기적인 관계성 역동 지도를 성찰과 성장의 기준으로 삼아보시기 바랍니다."
    )
    pdf.multi_cell(0, 6, info_text, border=0, fill=True, align="L")
    pdf.ln(8)
    
    from core.assessment import load_ontology
    ontology = load_ontology()
    s_map = {s["code"]: s for s in ontology["strengths"]}
    
    # 상위 5대 강점 루프 출력
    for idx, r in enumerate(top_5_results, 1):
        if idx == 3:
            pdf.add_page()
            pdf.set_font(font_family, "B", 9)
            pdf.set_text_color(150, 150, 150)
            pdf.cell(0, 6, clean("CoachKG 강점 분석 리포트 (이어서 계속)"), ln=True, align="R")
            pdf.set_draw_color(220, 224, 230)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(6)
            
        pdf.set_fill_color(230, 240, 250)
        pdf.set_font(font_family, "B", 12)  # 제목 폰트 크기 상향
        pdf.set_text_color(41, 128, 185)
        
        header_text = f"  [{idx}순위]  {r['name']}  (평점: {r['final_score']} / 5.0)   | 소속 덕목: {r['virtue']}"
        pdf.cell(0, 9, clean(header_text), ln=True, fill=True)
        pdf.ln(2)
        
        pdf.set_font(font_family, "B", 10.5)  # 소제목 폰트 크기 상향
        pdf.set_text_color(50, 50, 50)
        pdf.cell(0, 5, clean("💬 핵심 요약 및 정의"), ln=True)
        pdf.ln(1)
        
        pdf.set_font(font_family, "", 10)  # 내용 본문 크기 상향
        pdf.set_text_color(80, 80, 80)
        summary_text = r.get("summary", "상세 요약 설명이 포함되지 않은 강점입니다.")
        pdf.multi_cell(0, 5.5, clean(summary_text))
        pdf.ln(2)
        
        s_detail = s_map.get(r.get("code"), {}) if r.get("code") else {}
        overuse_text = s_detail.get("overuse", "과사용 시 주변과의 불협화음 혹은 번아웃을 유발할 우려가 있으니 성찰해 보시기 바랍니다.")
        
        synergy_list = [s_map[s_code]["name"] for s_code in s_detail.get("synergy_with", []) if s_code in s_map]
        balances_list = [s_map[b_code]["name"] for b_code in s_detail.get("balances", []) if b_code in s_map]
        conflicts_list = [s_map[c_code]["name"] for c_code in s_detail.get("conflicts_with", []) if c_code in s_map]
        
        pdf.set_font(font_family, "B", 10.5)
        pdf.set_text_color(192, 57, 43)
        pdf.cell(0, 5, clean("⚠️ 과사용(Overuse) 위험성과 그림자"), ln=True)
        pdf.ln(1)
        
        pdf.set_font(font_family, "", 10)
        pdf.set_text_color(80, 80, 80)
        pdf.multi_cell(0, 5.5, clean(overuse_text))
        pdf.ln(2)
        
        relations_text_parts = []
        if synergy_list:
            relations_text_parts.append(f"🤝 시너지: {', '.join(synergy_list)}")
        if balances_list:
            relations_text_parts.append(f"⚖️ 보완균형: {', '.join(balances_list)}")
        if conflicts_list:
            relations_text_parts.append(f"⚡ 주의상충: {', '.join(conflicts_list)}")
            
        if relations_text_parts:
            pdf.set_font(font_family, "B", 10.5)
            pdf.set_text_color(39, 174, 96)
            pdf.cell(0, 5, clean("🔗 유기적 지식 관계망 역동성"), ln=True)
            pdf.ln(1)
            
            pdf.set_font(font_family, "", 9.5)
            pdf.set_text_color(100, 100, 100)
            relation_str = "  |  ".join(relations_text_parts)
            pdf.cell(0, 5, clean(f"  {relation_str}"), ln=True)
            pdf.ln(2)
        
        keywords = r.get("keywords", [])
        if keywords:
            pdf.set_font(font_family, "B", 10.5)
            pdf.set_text_color(50, 50, 50)
            pdf.cell(0, 5, clean("🏷️ 연관 키워드"), ln=True)
            pdf.ln(1)
            
            pdf.set_font(font_family, "", 9.5)
            pdf.set_text_color(100, 100, 100)
            keyword_str = ", ".join(keywords)
            pdf.cell(0, 5, clean(f"  {keyword_str}"), ln=True)
            
        pdf.ln(6)
        
    # NetworkX 기반 정적 지도 생성 및 인쇄
    pdf.add_page()
    pdf.set_font(font_family, "B", 15)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 10, clean("나의 5대 지능형 강점 네트워크 지형도"), ln=True, align="L")
    pdf.ln(5)
    
    G = nx.Graph()
    top_codes = [r["code"] for r in top_5_results]
    added_nodes = set(top_codes)
    
    node_colors = []
    node_labels = {}
    
    for r in top_5_results:
        code = r["code"]
        G.add_node(code)
        node_colors.append('#2ecc71')
        node_labels[code] = r["name"]
        
        virtue_name = r["virtue"]
        if virtue_name not in G:
            G.add_node(virtue_name)
            node_colors.append('#9b5de5')
            node_labels[virtue_name] = virtue_name
        G.add_edge(code, virtue_name, color='#bdc3c7', weight=2, style='solid')
        
        s_detail = s_map.get(code, {})
        related = s_detail.get("synergy_with", []) + s_detail.get("balances", []) + s_detail.get("conflicts_with", [])
        for rel_code in related:
            if rel_code not in added_nodes and rel_code in s_map:
                G.add_node(rel_code)
                node_colors.append('#dfe6e9')
                node_labels[rel_code] = s_map[rel_code]["name"]
                added_nodes.add(rel_code)
                
    edge_colors = []
    edge_styles = []
    
    for r in top_5_results:
        code = r["code"]
        s_detail = s_map.get(code, {})
        
        for u, v, d in G.edges(data=True):
            if d.get('color') == '#bdc3c7':
                continue
                
        for syn in s_detail.get("synergy_with", []):
            if G.has_node(syn) and not G.has_edge(code, syn):
                G.add_edge(code, syn, color='#2ecc71', style='solid')
                
        for bal in s_detail.get("balances", []):
            if G.has_node(bal) and not G.has_edge(code, bal):
                G.add_edge(code, bal, color='#e67e22', style='dashed')
                
        for con in s_detail.get("conflicts_with", []):
            if G.has_node(con) and not G.has_edge(code, con):
                G.add_edge(code, con, color='#e74c3c', style='dotted')

    edges = G.edges(data=True)
    colors = [edge[2].get('color', '#bdc3c7') for edge in edges]
    styles = [edge[2].get('style', 'solid') for edge in edges]
    
    plt.figure(figsize=(7.5, 6), dpi=300)
    
    # =========================================================================
    # [Matplotlib 폰트 설정 무결성 확보 단계]
    # =========================================================================
    # Regular 폰트 에러 가능성을 배제하고, 타이틀과 노드 그리기 전반에 걸쳐
    # 이미 성공적으로 한글 렌더링이 증명된 Bold 폰트 경로(active_bold_path)를 일괄 바인딩합니다.
    matplotlib_font_path = None
    if active_bold_path and os.path.exists(active_bold_path) and os.path.getsize(active_bold_path) > 1000000:
        matplotlib_font_path = active_bold_path
    elif active_regular_path and os.path.exists(active_regular_path) and os.path.getsize(active_regular_path) > 1000000:
        matplotlib_font_path = active_regular_path

    if matplotlib_font_path:
        print(f"[DEBUG_FONT] Matplotlib이 지형도를 그리기 위해 물리 경로를 타겟팅합니다: {matplotlib_font_path}")
        # 중요: 특정 물리 경로(.ttf) 직접 바인딩 시, 메타데이터 매칭 오류를 원천 차단하기 위해
        # FontProperties 생성자 내부에는 오직 fname과 size만 단독 전달합니다 (weight, style 매개변수 전면 제거).
        font_prop_node = fm.FontProperties(fname=matplotlib_font_path, size=8)
        font_prop_title = fm.FontProperties(fname=matplotlib_font_path, size=11)
    else:
        print("[DEBUG_FONT_WARN] Matplotlib용 물리 한글 폰트를 찾지 못했습니다. sans-serif로 대체합니다.")
        font_prop_node = fm.FontProperties(family="sans-serif", size=8)
        font_prop_title = fm.FontProperties(family="sans-serif", size=11)
        
    plt.rcParams['axes.unicode_minus'] = False
    
    pos = nx.spring_layout(G, k=0.8, iterations=50)
    
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=800)
    
    # =========================================================================
    # [NetworkX 내부 폰트 덮어쓰기 우회 - Matplotlib 순수 텍스트 레이아웃 배치]
    # =========================================================================
    clean_labels = {k: clean(v) for k, v in node_labels.items()}
    for node, (x, y) in pos.items():
        if node in clean_labels:
            plt.text(
                x, y, 
                clean_labels[node], 
                fontproperties=font_prop_node, 
                ha='center', 
                va='center',
                zorder=10
            )
    
    for edge, color, style in zip(edges, colors, styles):
        nx.draw_networkx_edges(
            G, pos, 
            edgelist=[(edge[0], edge[1])], 
            edge_color=color, 
            style=style, 
            width=1.5
        )
        
    # 타이틀 드로잉 영역에도 물리 주소 폰트 객체 적용 (이모지 제거)
    plt.title(clean("CoachKG 강점 시너제틱 지형망"), fontproperties=font_prop_title, pad=15)
    plt.axis('off')
    plt.tight_layout()
    
    temp_img_name = f"temp_mat_{session_token}.png"
    temp_dir = tempfile.gettempdir()
    temp_img_path = os.path.join(temp_dir, temp_img_name)
    plt.savefig(temp_img_path, format="png", bbox_inches='tight')
    plt.close()
    
    if os.path.exists(temp_img_path):
        pdf.image(temp_img_path, x=15, y=35, w=180)
        try:
            os.remove(temp_img_path)
        except:
            pass

    output_filename = f"report_{session_token}.pdf"
    output_pdf_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), output_filename)
    
    pdf.output(output_pdf_path)
    return output_pdf_path

# core/report_gen.py 내의 PDF 빌더 메서드 가상 패치 예시

def add_complementary_section(pdf, results, ontology_map):
    """
    PDF 보고서의 종결부에 보완 및 미개발 강점 지반 분석 페이지를 동적으로 렌더링합니다.
    """
    # 새 페이지 추가
    pdf.add_page()
    
    # 타이틀 영역
    pdf.set_font("NanumGothic-Bold", size=14)
    pdf.cell(0, 10, txt="🧭 보완 강점 및 일반/미개발 영역 제언", ln=1, align="L")
    pdf.ln(5)
    
    # 텍스트 바디 폰트 설정
    pdf.set_font("NanumGothic", size=9)
    
    group_b = [r for r in results if r["group"] == "B"][:2] # 지면 한계 상 각각 상위 2개씩 수록
    group_c = [r for r in results if r["group"] == "C"][:2]
    
    # --- 보완 강점 출력 ---
    pdf.set_text_color(230, 126, 34) # 주황색 (B그룹 상징)
    pdf.cell(0, 8, txt="■ 보완적 균형 지대 (Group B)", ln=1)
    pdf.set_text_color(0, 0, 0)
    
    for r in group_b:
        s_detail = ontology_map.get(r["code"], {})
        # 폴백 로직 적용
        interp = "이 강점은 핵심 역량이 흐려질 때 이를 보정해 주는 보조 자원입니다."
        if "interpretation" in s_detail and "complementary" in s_detail["interpretation"]:
            interp = s_detail["interpretation"]["complementary"]
            
        pdf.set_font("NanumGothic-Bold", size=10)
        pdf.cell(0, 6, txt=f" - {r['name']} ({r['virtue']})", ln=1)
        pdf.set_font("NanumGothic", size=9)
        pdf.multi_cell(0, 5, txt=interp)
        pdf.ln(3)
        
    pdf.ln(5)
    
    # --- 일반/미개발 강점 출력 ---
    pdf.set_text_color(231, 76, 60) # 빨간색 (C그룹 상징)
    pdf.cell(0, 8, txt="■ 일반 및 미개발 지대 (Group C)", ln=1)
    pdf.set_text_color(0, 0, 0)
    
    for r in group_c:
        s_detail = ontology_map.get(r["code"], {})
        interp = "무리한 역량 보완보다는 타인과의 협업 및 시스템적 위임을 권장하는 영역입니다."
        if "interpretation" in s_detail and "undeveloped" in s_detail["interpretation"]:
            interp = s_detail["interpretation"]["undeveloped"]
            
        pdf.set_font("NanumGothic-Bold", size=10)
        pdf.cell(0, 6, txt=f" - {r['name']} ({r['virtue']})", ln=1)
        pdf.set_font("NanumGothic", size=9)
        pdf.multi_cell(0, 5, txt=interp)
        pdf.ln(3)