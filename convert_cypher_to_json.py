import os
import re
import json
import ast
import tkinter as tk
from tkinter import filedialog, messagebox

# --- 개선된 변환 핵심 로직 ---
def parse_cypher_to_json(cypher_file_path, output_json_path):
    virtues = {}
    strengths = {}
    var_to_code = {}
    var_to_virtue_name = {}

    with open(cypher_file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # [핵심 수정] 주석(//)으로 시작하는 줄만 줄바꿈 단위로 먼저 제거하여 데이터 손실 방지
    clean_lines = []
    for line in content.splitlines():
        if not line.strip().startswith("//"):
            clean_lines.append(line)
    clean_content = "\n".join(clean_lines)

    # 세미콜론 기준으로 문장 분할
    statements = clean_content.split(";")
    
    for stmt in statements:
        stmt = stmt.strip()
        if not stmt:
            continue
            
        if ":Virtue" in stmt:
            prefix_match = re.search(r'\(([a-zA-Z0-9_]+):Virtue\s*\{name:\s*["\']([^"\']+)["\']\}\)', stmt)
            if prefix_match:
                var_name, virtue_name = prefix_match.groups()
                var_to_virtue_name[var_name] = virtue_name
                
                set_match = re.search(r'SET\s+(.*)', stmt, re.DOTALL)
                if set_match:
                    set_clause = set_match.group(1).strip()
                    parts = re.split(fr',\s*{var_name}\.', set_clause)
                    parts[0] = re.sub(fr'^{var_name}\.', '', parts[0])
                    
                    v_data = {"name": virtue_name}
                    for part in parts:
                        if '=' in part:
                            key, val_str = part.split('=', 1)
                            key = key.strip()
                            try:
                                v_data[key] = ast.literal_eval(val_str.strip())
                            except Exception:
                                v_data[key] = val_str.strip().strip('"').strip("'")
                    virtues[virtue_name] = v_data

        elif ":Strength" in stmt:
            prefix_match = re.search(r'\(([a-zA-Z0-9_]+):Strength\s*\{code:\s*["\']([^"\']+)["\']\}\)', stmt)
            if prefix_match:
                var_name, strength_code = prefix_match.groups()
                var_to_code[var_name] = strength_code
                
                set_match = re.search(r'SET\s+(.*)', stmt, re.DOTALL)
                if set_match:
                    set_clause = set_match.group(1).strip()
                    parts = re.split(fr',\s*{var_name}\.', set_clause)
                    parts[0] = re.sub(fr'^{var_name}\.', '', parts[0])
                    
                    s_data = {
                        "code": strength_code,
                        "synergy_with": [],
                        "conflicts_with": [],
                        "supports": [],
                        "balances": []
                    }
                    
                    for part in parts:
                        if '=' in part:
                            key, val_str = part.split('=', 1)
                            key = key.strip()
                            try:
                                s_data[key] = ast.literal_eval(val_str.strip())
                            except Exception:
                                s_data[key] = val_str.strip().strip('"').strip("'")
                    strengths[strength_code] = s_data

    for stmt in statements:
        stmt = stmt.strip()
        if not stmt:
            continue
            
        if "MATCH" in stmt and "-[" in stmt:
            local_mappings = {}
            var_matches = re.findall(r'\(([a-zA-Z0-9_]+):(Strength|Virtue)\s*\{([a-zA-Z0-9_]+):\s*["\']([^"\']+)["\']\}\)', stmt)
            for var_name, node_type, attr_name, attr_val in var_matches:
                local_mappings[var_name] = (node_type, attr_val)

            rel_match = re.search(r'MERGE\s+\(([a-zA-Z0-9_]+)\)-\[:([A-Z_]+)\]->\(([a-zA-Z0-9_]+)\)', stmt)
            if rel_match:
                source_var, rel_type, target_var = rel_match.groups()
                source_code = var_to_code.get(source_var) or (local_mappings.get(source_var)[1] if source_var in local_mappings else None)
                target_code = var_to_code.get(target_var) or (local_mappings.get(target_var)[1] if target_var in local_mappings else None)
                target_virtue_name = var_to_virtue_name.get(target_var) or (local_mappings.get(target_var)[1] if target_var in local_mappings and local_mappings[target_var][0] == "Virtue" else None)

                if source_code and source_code in strengths:
                    if rel_type == "BELONGS_TO" and target_virtue_name:
                        v_info = virtues.get(target_virtue_name, {})
                        strengths[source_code]["virtue_code"] = v_info.get("code")
                        strengths[source_code]["virtue_name"] = target_virtue_name
                    elif rel_type == "SYNERGY_WITH" and target_code:
                        if target_code not in strengths[source_code]["synergy_with"]:
                            strengths[source_code]["synergy_with"].append(target_code)
                    elif rel_type == "CONFLICTS_WITH" and target_code:
                        if target_code not in strengths[source_code]["conflicts_with"]:
                            strengths[source_code]["conflicts_with"].append(target_code)
                    elif rel_type == "SUPPORTS" and target_code:
                        if target_code not in strengths[source_code]["supports"]:
                            strengths[source_code]["supports"].append(target_code)
                    elif rel_type == "BALANCES" and target_code:
                        if target_code not in strengths[source_code]["balances"]:
                            strengths[source_code]["balances"].append(target_code)

    output_data = {
        "virtues": list(virtues.values()),
        "strengths": list(strengths.values())
    }

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    # 팝업 알림 시 개수 반환 기능 추가
    return len(virtues), len(strengths)

# --- GUI 인터페이스 관리 ---
def select_file():
    path = filedialog.askopenfilename(
        title="Cypher 텍스트 파일 선택",
        filetypes=[("Text Files", "*.txt"), ("Cypher Files", "*.cypher"), ("All Files", "*.*")]
    )
    if path:
        entry_input.delete(0, tk.END)
        entry_input.insert(0, path)

def select_dir():
    path = filedialog.askdirectory(title="결과물 저장 폴더 선택")
    if path:
        entry_output.delete(0, tk.END)
        entry_output.insert(0, path)

def start_process():
    input_file = entry_input.get()
    output_dir = entry_output.get()

    if not input_file or not os.path.exists(input_file):
        messagebox.showerror("오류", "가져올 Cypher 텍스트 파일을 올바르게 선택해 주세요.")
        return
    if not output_dir or not os.path.isdir(output_dir):
        messagebox.showerror("오류", "저장할 대상 폴더를 올바르게 선택해 주세요.")
        return

    output_file_path = os.path.join(output_dir, "strengths.json")

    try:
        v_count, s_count = parse_cypher_to_json(input_file, output_file_path)
        messagebox.showinfo(
            "완료", 
            f"데이터 변환에 성공하였습니다!\n\n"
            f"■ 추출된 덕목(Virtue): {v_count}개\n"
            f"■ 추출된 강점(Strength): {s_count}개\n\n"
            f"저장 경로:\n{output_file_path}"
        )
    except Exception as e:
        messagebox.showerror("변환 오류", f"작업 중 에러가 발생했습니다:\n{str(e)}")

# --- Tkinter 창 설정 ---
root = tk.Tk()
root.title("Cypher to JSON Converter")
root.geometry("520x200")
root.resizable(False, False)

# 입력 파일 영역
label_input = tk.Label(root, text="가져올 Cypher 파일:")
label_input.grid(row=0, column=0, padx=10, pady=15, sticky="e")

entry_input = tk.Entry(root, width=40)
entry_input.grid(row=0, column=1, padx=5, pady=15)

btn_input = tk.Button(root, text="찾아보기", command=select_file)
btn_input.grid(row=0, column=2, padx=10, pady=15)

# 출력 폴더 영역
label_output = tk.Label(root, text="저장할 폴더:")
label_output.grid(row=1, column=0, padx=10, pady=5, sticky="e")

entry_output = tk.Entry(root, width=40)
entry_output.grid(row=1, column=1, padx=5, pady=5)

btn_output = tk.Button(root, text="폴더선택", command=select_dir)
btn_output.grid(row=1, column=2, padx=10, pady=5)

# 실행 버튼
btn_run = tk.Button(root, text="JSON 변환 시작", width=25, height=2, bg="#4CAF50", fg="white", command=start_process)
btn_run.grid(row=2, column=0, columnspan=3, pady=25)

root.mainloop()