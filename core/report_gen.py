# core/report_gen.py
import os
import tempfile
from datetime import datetime
from fpdf import FPDF

# Streamlit Cloud 백그라운드 드로잉을 위한 Matplotlib 및 NetworkX 탑재
import matplotlib
matplotlib.use('Agg')  # 가상 GUI 서버용 논-인터랙티브 백엔드 설정
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.lines import Line2D
import networkx as nx

# 폰트 탐색 경로 정의
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

FONT_DIR = os.path.join(project_root, "data", "fonts")
FONT_REGULAR_PATH = os.path.join(FONT_DIR, "NanumGothic.ttf")
FONT_BOLD_PATH = os.path.join(FONT_DIR, "NanumGothic-Bold.ttf")

# Linux OS 패키지 설치 시 시스템 기본 경로
SYSTEM_FONT_REGULAR = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
SYSTEM_FONT_BOLD = "/usr/share/fonts/truetype/nanum/NanumGothic-Bold.ttf"

def ensure_korean_fonts():
    """ 한글 나눔고딕 폰트 파일 무결성 확인 및 필요 시 자동 보완 """
    if os.path.exists(SYSTEM_FONT_REGULAR) and os.path.exists(SYSTEM_FONT_BOLD):
        return

    os.makedirs(FONT_DIR, exist_ok=True)
    import urllib.request
    
    targets = [
        (FONT_REGULAR_PATH, "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"),
        (FONT_BOLD_PATH, "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf")
    ]
    
    for path, url in targets:
        if os.path.exists(path) and os.path.getsize(path) < 1000000:
            try:
                os.remove(path)
            except:
                pass
                
        if not os.path.exists(path):
            try:
                urllib.request.urlretrieve(url, path, timeout=10)
            except Exception as e:
                print(f"[ERROR] 폰트 다운로드 실패: {e}")

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

def generate_pdf_report(session_token, user_meta, results):
    ensure_korean_fonts()
    
    font_family = "NanumGothic"
    active_regular_path = None
    active_bold_path = None
    
    if os.path.exists(SYSTEM_FONT_REGULAR) and os.path.exists(SYSTEM_FONT_BOLD):
        active_regular_path = SYSTEM_FONT_REGULAR
        active_bold_path = SYSTEM_FONT_BOLD
    elif (os.path.exists(FONT_REGULAR_PATH) and os.path.exists(FONT_BOLD_PATH) and 
          os.path.getsize(FONT_REGULAR_PATH) > 1000000 and os.path.getsize(FONT_BOLD_PATH) > 1000000):
        active_regular_path = FONT_REGULAR_PATH
        active_bold_path = FONT_BOLD_PATH

    if active_regular_path and active_bold_path:
        try:
            pdf = CoachKGPDF(font_family="NanumGothic")
            pdf.set_auto_page_break(auto=True, margin=20)
            pdf.add_font("NanumGothic", style="", fname=active_regular_path)
            pdf.add_font("NanumGothic", style="B", fname=active_bold_path)
        except Exception as e:
            font_family = "Helvetica"
            pdf = CoachKGPDF(font_family="Helvetica")
            pdf.set_auto_page_break(auto=True, margin=20)
    else:
        font_family = "Helvetica"
        pdf = CoachKGPDF(font_family="Helvetica")
        pdf.set_auto_page_break(auto=True, margin=20)
        
    def clean(text):
        if font_family == "Helvetica":
            return "".join(c if ord(c) < 128 else "?" for c in str(text))
        return str(text)
    
    # 분석 전 영역 분할 수집
    top_5_results = [r for r in results if r["group"] == "A"][:5]
    if not top_5_results:
        top_5_results = results[:5]
        
    group_b_results = [r for r in results if r["group"] == "B"]
    group_c_results = [r for r in results if r["group"] == "C"]
    
    # ---------------------------------------------------------
    # PAGE 1 & 2: 대표 강점 리포트
    # ---------------------------------------------------------
    pdf.add_page()
    pdf.set_text_color(44, 62, 80)
    pdf.set_font(font_family, "B", 21)
    pdf.cell(0, 15, clean("🏆 나의 5대 지능형 강점 분석 리포트"), ln=True, align="L")
    pdf.ln(2)
    
    pdf.set_font(font_family, "", 10.5)
    pdf.set_text_color(80, 80, 80)
    today_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    pdf.cell(0, 6, clean(f"피진단자 성함 : {user_meta.get('name', '미기재')} 님"), ln=True)
    pdf.cell(0, 6, clean(f"이메일 계정 : {user_meta.get('email', '미기재')}"), ln=True)
    pdf.cell(0, 6, clean(f"진단 시각 : {today_str}"), ln=True)
    pdf.ln(8)
    
    pdf.set_fill_color(245, 247, 250)
    pdf.set_font(font_family, "", 10)
    pdf.set_text_color(50, 50, 50)
    info_text = (
        "This is your personal report." if font_family == "Helvetica" else
        "아래 정보는 1차 자가 카드 소팅 검증과 2차 정밀 척도 합산을 통해 도출된 당신의 상위 5대 핵심 잠재 역량입니다. "
        "온톨로지(Ontology) 기반으로 분석된 개별 강점의 정의와 과사용 그림자, 그리고 유기적인 관계성 지도를 성찰의 지표로 활용하십시오."
    )
    pdf.multi_cell(0, 6, info_text, border=0, fill=True, align="L")
    pdf.ln(6)
    
    from core.assessment import load_ontology
    ontology = load_ontology()
    s_map = {s["code"]: s for s in ontology["strengths"]}
    
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
        pdf.set_font(font_family, "B", 11.5)
        pdf.set_text_color(41, 128, 185)
        
        header_text = f"  [{idx}순위]  {r['name']}  (평점: {r['final_score']} / 5.0)   | 소속 덕목: {r['virtue']}"
        pdf.cell(0, 9, clean(header_text), ln=True, fill=True)
        pdf.ln(2)
        
        pdf.set_font(font_family, "B", 10)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(0, 5, clean("💬 핵심 요약 및 정의"), ln=True)
        pdf.ln(1)
        
        pdf.set_font(font_family, "", 9.5)
        pdf.set_text_color(80, 80, 80)
        summary_text = r.get("summary", "상세 설명이 포함되지 않은 강점입니다.")
        pdf.multi_cell(0, 5.5, clean(summary_text))
        pdf.ln(2)
        
        s_detail = s_map.get(r.get("code"), {}) if r.get("code") else {}
        overuse_text = s_detail.get("overuse", "과사용 시 주변과의 불협화음 유발 우려가 있으니 유의하십시오.")
        
        synergy_list = [s_map[s_code]["name"] for s_code in s_detail.get("synergy_with", []) if s_code in s_map]
        balances_list = [s_map[b_code]["name"] for b_code in s_detail.get("balances", []) if b_code in s_map]
        conflicts_list = [s_map[c_code]["name"] for c_code in s_detail.get("conflicts_with", []) if c_code in s_map]
        
        pdf.set_font(font_family, "B", 10)
        pdf.set_text_color(192, 57, 43)
        pdf.cell(0, 5, clean("⚠️ 과사용(Overuse) 위험성과 그림자"), ln=True)
        pdf.ln(1)
        
        pdf.set_font(font_family, "", 9.5)
        pdf.set_text_color(80, 80, 80)
        pdf.multi_cell(0, 5.5, clean(overuse_text))
        pdf.ln(2)
        
        relations_text_parts = []
        if synergy_list:
            relations_text_parts.append(f"시너지: {', '.join(synergy_list)}")
        if balances_list:
            relations_text_parts.append(f"보완균형: {', '.join(balances_list)}")
        if conflicts_list:
            relations_text_parts.append(f"주의상충: {', '.join(conflicts_list)}")
            
        if relations_text_parts:
            pdf.set_font(font_family, "B", 10)
            pdf.set_text_color(39, 174, 96)
            pdf.cell(0, 5, clean("🔗 유기적 지식 관계망 역동성"), ln=True)
            pdf.ln(1)
            
            pdf.set_font(font_family, "", 9)
            pdf.set_text_color(100, 100, 100)
            relation_str = "  |  ".join(relations_text_parts)
            pdf.cell(0, 5, clean(f"  {relation_str}"), ln=True)
            pdf.ln(2)
        
        keywords = r.get("keywords", [])
        if keywords:
            pdf.set_font(font_family, "B", 10)
            pdf.set_text_color(50, 50, 50)
            pdf.cell(0, 5, clean("🏷️ 연관 키워드"), ln=True)
            pdf.ln(1)
            
            pdf.set_font(font_family, "", 9)
            pdf.set_text_color(100, 100, 100)
            keyword_str = ", ".join(keywords)
            pdf.cell(0, 5, clean(f"  {keyword_str}"), ln=True)
            
        pdf.ln(6)
        
    # ---------------------------------------------------------
    # PAGE 3: 개선된 레이아웃 및 범례 표시의 네트워크 지형도
    # ---------------------------------------------------------
    pdf.add_page()
    pdf.set_font(font_family, "B", 15)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 10, clean("나의 5대 지능형 강점 네트워크 지형도 (탐색 깊이: 1단계)"), ln=True, align="L")
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
                
    edges = G.edges(data=True)
    for r in top_5_results:
        code = r["code"]
        s_detail = s_map.get(code, {})
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
    
    # 범례 영역 확보를 위해 차트 높이를 약간 늘리고 정밀도를 확보합니다.
    fig = plt.figure(figsize=(7.5, 7.5), dpi=300)
    
    matplotlib_font_path = active_bold_path if active_bold_path else active_regular_path
    if matplotlib_font_path:
        font_prop_node = fm.FontProperties(fname=matplotlib_font_path, size=7.5)
        font_prop_title = fm.FontProperties(fname=matplotlib_font_path, size=11)
    else:
        font_prop_node = fm.FontProperties(family="sans-serif", size=7.5)
        font_prop_title = fm.FontProperties(family="sans-serif", size=11)
        
    plt.rcParams['axes.unicode_minus'] = False
    
    # [개선 1] 겹침을 최소화하고 유기적 관계 분산에 수월한 Kamada-Kawai 레이아웃으로 변경
    pos = nx.kamada_kawai_layout(G)
    
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=600)
    
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
            width=1.3
        )
        
    plt.title(clean("CoachKG 강점 시너제틱 지형망"), fontproperties=font_prop_title, pad=15)
    plt.axis('off')
    
    # [개선 2] Matplotlib 캔버스 하단에 고무적인 범례(Legend) 추가
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#2ecc71', markersize=8, label=clean('대표 강점 (Group A)')),
        Line2D([0], [0], marker='^', color='w', markerfacecolor='#9b5de5', markersize=8, label=clean('상위 대덕목 (Virtues)')),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#dfe6e9', markersize=8, label=clean('연계 강점 영역 (이웃)')),
        Line2D([0], [0], color='#2ecc71', lw=1.5, label=clean('시너지 효과 (Synergy)')),
        Line2D([0], [0], color='#e67e22', lw=1.5, linestyle='--', label=clean('상호보완 균형 (Balances)')),
        Line2D([0], [0], color='#e74c3c', lw=1.5, linestyle=':', label=clean('주의필요 상충 (Conflicts)'))
    ]
    plt.legend(handles=legend_elements, loc='lower center', ncol=2, prop=font_prop_node, bbox_to_anchor=(0.5, -0.1))
    plt.tight_layout()
    
    temp_img_name = f"temp_mat_{session_token}.png"
    temp_dir = tempfile.gettempdir()
    temp_img_path = os.path.join(temp_dir, temp_img_name)
    plt.savefig(temp_img_path, format="png", bbox_inches='tight')
    plt.close()
    
    if os.path.exists(temp_img_path):
        pdf.image(temp_img_path, x=15, y=30, w=180)
        try:
            os.remove(temp_img_path)
        except:
            pass

    # ---------------------------------------------------------
    # PAGE 4 [개선 4]: 보완(Group B) 및 일반/미개발(Group C) 강점 전수 분석 레이어
    # ---------------------------------------------------------
    pdf.add_page()
    pdf.set_font(font_family, "B", 15)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 10, clean("🧭 보완 강점 및 일반/미개발 가이드 (Group B & C)"), ln=True, align="L")
    pdf.ln(4)
    
    # 1) 보완 강점 전수 진단 영역
    pdf.set_font(font_family, "B", 11)
    pdf.set_text_color(230, 126, 34)  # 주황색 (B그룹 상징)
    pdf.cell(0, 8, clean("■ 보완적 균형 지대 (Group B) - 핵심 보조 및 성과 안착 자원"), ln=True)
    pdf.ln(1)
    
    pdf.set_font(font_family, "", 9.5)
    pdf.set_text_color(80, 80, 80)
    if group_b_results:
        # 상위 2개 보완 강점 상세 분석 수록
        for r in group_b_results[:2]:
            s_detail = s_map.get(r["code"], {})
            interp = s_detail.get("interpretation", {}).get("complementary", "핵심 강점을 보조하여 성과의 기둥 역할을 합니다.")
            pdf.set_font(font_family, "B", 10)
            pdf.cell(0, 6, clean(f" - {r['name']} ({r['virtue']})"), ln=True)
            pdf.set_font(font_family, "", 9)
            pdf.multi_cell(0, 5, clean(interp))
            pdf.ln(2)
        
        # 나머지 전수 리스트 출력
        pdf.set_font(font_family, "B", 9.5)
        pdf.set_text_color(120, 120, 120)
        other_b_names = [r["name"] for r in group_b_results[2:]]
        if other_b_names:
            pdf.multi_cell(0, 5, clean(f"※ 기타 분류된 보완 강점 명단: {', '.join(other_b_names)}"))
    else:
        pdf.cell(0, 6, clean("  분류된 보완 강점이 존재하지 않습니다."), ln=True)
        
    pdf.ln(6)
    
    # 2) 일반/미개발 강점 전수 진단 영역
    pdf.set_font(font_family, "B", 11)
    pdf.set_text_color(231, 76, 60)  # 빨간색 (C그룹 상징)
    pdf.cell(0, 8, clean("■ 일반 및 미개발 지대 (Group C) - 협업 지대 및 시스템 우회 자원"), ln=True)
    pdf.ln(1)
    
    pdf.set_font(font_family, "", 9.5)
    pdf.set_text_color(80, 80, 80)
    if group_c_results:
        # 상위 2개 일반/미개발 강점 상세 분석 수록
        for r in group_c_results[:2]:
            s_detail = s_map.get(r["code"], {})
            interp = s_detail.get("interpretation", {}).get("undeveloped", "외부 협업 및 시스템의 지원을 받아 효율을 보완합니다.")
            pdf.set_font(font_family, "B", 10)
            pdf.cell(0, 6, clean(f" - {r['name']} ({r['virtue']})"), ln=True)
            pdf.set_font(font_family, "", 9)
            pdf.multi_cell(0, 5, clean(interp))
            pdf.ln(2)
            
        # 나머지 전수 리스트 출력
        pdf.set_font(font_family, "B", 9.5)
        pdf.set_text_color(120, 120, 120)
        other_c_names = [r["name"] for r in group_c_results[2:]]
        if other_c_names:
            pdf.multi_cell(0, 5, clean(f"※ 기타 분류된 일반/미개발 강점 명단: {', '.join(other_c_names)}"))
    else:
        pdf.cell(0, 6, clean("  분류된 일반/미개발 강점이 존재하지 않습니다."), ln=True)

    output_filename = f"report_{session_token}.pdf"
    output_pdf_path = os.path.join(tempfile.gettempdir(), output_filename)
    
    pdf.output(output_pdf_path)
    return output_pdf_path