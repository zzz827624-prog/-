import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from PIL import Image
import json
import os
import datetime

# ==========================================
# 0. 網頁基本設定與 CSS 樣式
# ==========================================
st.set_page_config(
    page_title="QRE 委測案件智慧數據看板",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
    <style>
    .main .block-container {padding-top: 1rem; padding-bottom: 1rem;}
    h1, h2, h3 { font-family: "Microsoft JhengHei", sans-serif; }
    /* 保持分頁二表格樣式 */
    .styled-table { width: 100%; border-collapse: collapse; }
    .styled-table th { font-size: 20px !important; font-weight: bold !important; text-align: center !important; background-color: #f8f9fa !important; color: #000000 !important; padding: 10px !important;}
    .styled-table td { text-align: center !important; padding: 8px 10px !important; color: #000000 !important; border: 1px solid #000000; vertical-align: middle !important; }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 1. 系統常數與資料初始化 (含前兩個分頁與出勤分頁)
# ==========================================
DATA_FILE = "test_data.json"
categories = [
    "整機壽命測試", "單體壽命測試", "破壞測試", "Wobble測試", 
    "振動測試", "環境測試", "鹽霧測試"
]
theme_colors = ['#4361EE', '#F72585', '#10B981', '#F59E0B', '#7209B7', '#00BCD4', '#F97316']
color_map = {cat: theme_colors[i % len(theme_colors)] for i, cat in enumerate(categories)}

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            return pd.read_json(DATA_FILE, orient='index')
        except Exception:
            pass
    cols = [f"W{i}" for i in range(1, 29)]
    return pd.DataFrame(0, index=categories, columns=cols)

def save_data(df):
    df.to_json(DATA_FILE, orient='index', force_ascii=False)

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- App 2 (產能看板) 專用設定 ---
CAPACITY_DATA_FILE = "capacity_data.json"
DEFAULT_CAPACITY_DATA = [
    {"測試類別": "破壞", "機型/項目": "APP", "週完成件數目標值": 150, "機台數": 2, "上週未完成件數": 84, "本週新收件數": 130, "本週完成總件數": 125, "說明": "根據以往周正常工時平均計算，每人37.5件/周"},
    {"測試類別": "APP單體", "機型/項目": "H202S/H205AS", "週完成件數目標值": 120, "機台數": 34, "上週未完成件數": 255, "本週新收件數": 7, "本週完成總件數": 135, "說明": "每機台3.5件/周"},
    {"測試類別": "整機", "機型/項目": "5300S", "週完成件數目標值": 27, "機台數": 27, "上週未完成件數": 10, "本週新收件數": 0, "本週完成總件數": 2, "說明": "每機台1件/周"},
    {"測試類別": "非APP單體", "機型/項目": "5308S", "週完成件數目標值": 24, "機台數": 24, "上週未完成件數": 12, "本週新收件數": 8, "本週完成總件數": 8, "說明": "根據以往周正常工時平均計算，每人6件/周"},
    {"測試類別": "Wobble測試", "機型/項目": "NB/LCD", "週完成件數目標值": 5, "機台數": 1, "上週未完成件數": 11, "本週新收件數": 0, "本週完成總件數": 11, "說明": "根據以往周正常工時平均計算，每人1.25件/周"},
    {"測試類別": "振動", "機型/項目": "NB", "週完成件數目標值": 5, "機台數": 1, "上週未完成件數": 1, "本週新收件數": 0, "本週完成總件數": 1, "說明": "根據以往周正常工時平均計算，每人1.25件/周"},
    {"測試類別": "落下", "機型/項目": "ALL", "週完成件數目標值": 5, "機台數": 1, "上週未完成件數": 0, "本週新收件數": 0, "本週完成總件數": 0, "說明": "根據以往周正常工時平均計算，每人1.25件/周"}
]

def load_capacity_data():
    if os.path.exists(CAPACITY_DATA_FILE):
        try:
            with open(CAPACITY_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"W1": DEFAULT_CAPACITY_DATA}

def save_capacity_data(data_dict):
    with open(CAPACITY_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data_dict, f, ensure_ascii=False, indent=4)

def get_next_cap_week(keys):
    max_w = 0
    for k in keys:
        if k.startswith('W') and k[1:].isdigit():
            max_w = max(max_w, int(k[1:]))
    return f"W{max_w + 1}" if max_w > 0 else f"W{len(keys) + 1}"

if "capacity_db" not in st.session_state:
    st.session_state.capacity_db = load_capacity_data()
if "current_cap_week" not in st.session_state:
    st.session_state.current_cap_week = list(st.session_state.capacity_db.keys())[-1]

# --- App 3 (加班系統) 專用設定 ---
OVERTIME_DB_FILE = "overtime_data.json"

def load_overtime_data():
    if os.path.exists(OVERTIME_DB_FILE):
        try:
            df = pd.read_json(OVERTIME_DB_FILE, dtype={"加班日期": str})
            if not df.empty:
                return df
        except Exception as e:
            st.error(f"讀取加班 JSON 失敗，改用初始數據。錯誤: {e}")
            
    mock_records = [
        {"姓名": "葉昱冠", "加班日期": "2026-07-01", "加班時數": 2.0, "日期屬性": "工作日"},
        {"姓名": "林辰瑄", "加班日期": "2026-07-01", "加班時數": 4.0, "日期屬性": "工作日"},
        {"姓名": "蕭泳嘉", "加班日期": "2026-07-01", "加班時數": 4.0, "日期屬性": "工作日"},
        {"姓名": "徐偉騰", "加班日期": "2026-07-01", "加班時數": 0.0, "日期屬性": "工作日"},
    ]
    return pd.DataFrame(mock_records)

def save_overtime_data(df):
    try:
        df.to_json(OVERTIME_DB_FILE, orient='records', force_ascii=False, indent=4)
    except Exception as e:
        st.error(f"儲存 JSON 檔案失敗：{e}")

if 'employees' not in st.session_state:
    st.session_state.employees = ["葉昱冠", "林辰瑄", "蕭泳嘉", "徐偉騰"]
if 'overtime_data' not in st.session_state:
    st.session_state.overtime_data = load_overtime_data()

def detect_date_info(selected_date):
    """自動判定台灣行事曆的日期屬性"""
    weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    w_name = weekday_names[selected_date.weekday()]
    if selected_date.weekday() == 5:
        return w_name, "休息日(週六)", True
    elif selected_date.weekday() == 6:
        return w_name, "例假日(週日)", True
    else:
        return w_name, "工作日", False


# ==========================================
# 2. 側邊欄：AI 截圖辨識區
# ==========================================
with st.sidebar:
    st.header("📸 截圖自動辨識帶入")
    st.caption(f"📍 目前辨識的資料將寫入至: **分頁2 ({st.session_state.current_cap_week})**")
    api_key = st.text_input("請輸入 Gemini API Key", type="password")
    uploaded_file = st.file_uploader("上傳週報表格截圖 (PNG/JPG)", type=["png", "jpg", "jpeg"])

    if uploaded_file and api_key:
        if st.button("🚀 開始智慧辨識轉換"):
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                image = Image.open(uploaded_file)
                prompt = """
                請精確讀取這張表格數據並轉換為標準 JSON 陣列輸出，格式欄位：
                "測試類別", "機型/項目", "週完成件數目標值", "機台數", "上週未完成件數", "本週新收件數", "本週完成總件數", "說明"
                注意：只返回純 JSON 陣列，不要包含任何 markdown 標籤。
                """
                response = model.generate_content([prompt, image])
                cleaned_text = response.text.strip().replace("```json", "").replace("```", "")
                
                parsed_data = json.loads(cleaned_text)
                st.session_state.capacity_db[st.session_state.current_cap_week] = parsed_data
                save_capacity_data(st.session_state.capacity_db)
                
                st.success(f"✅ AI 辨識成功！已覆蓋 {st.session_state.current_cap_week} 的資料。")
                st.rerun()
            except Exception as e:
                st.error(f"AI 辨識錯誤: {e}")


# ==========================================
# 3. 主畫面頂部標題與分頁 (Tabs) 設定
# ==========================================
st.markdown("""
    <h1 style='color: #000000; font-weight: 700; margin-bottom: 0;'>🚀 QRE 委測案件智慧數據看板</h1>
    <p style='color: #333333; font-size: 16px; margin-top: 5px;'>Modern Unified Dashboard for Test Analytics</p>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📈 1. 測試年度統計 (週數趨勢)", "📊 2. 實驗室產能與消化進度看板", "⏰ 3. 人員出勤與加班管理"])

# ==========================================
# 分頁 1: 各項測試年度統計 (完全保留最新2分頁版)
# ==========================================
with tab1:
    st.markdown("<h3 style='color: #000000; margin-top: 20px;'>📝 填寫每週測試件數</h3>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 2, 8])
    with col1:
        if st.button("➕ 新增下一週", use_container_width=True, key="add_w_tab1"):
            next_week_num = len(st.session_state.df.columns) + 1
            st.session_state.df[f"W{next_week_num}"] = 0
            save_data(st.session_state.df) 
            st.rerun()
    with col2:
        if st.button("➖ 移除最後一週", use_container_width=True, key="rm_w_tab1"):
            if len(st.session_state.df.columns) > 1:
                st.session_state.df = st.session_state.df.iloc[:, :-1]
                save_data(st.session_state.df) 
                st.rerun()
            else:
                st.warning("⚠️ 至少需保留一週資料！")

    edited_df = st.data_editor(st.session_state.df, use_container_width=True)

    if not edited_df.equals(st.session_state.df):
        st.session_state.df = edited_df
        save_data(edited_df)

    st.divider()
    st.markdown("<h3 style='color: #000000;'>📈 綜合圖表與對照表</h3>", unsafe_allow_html=True)

    total_weeks = len(edited_df.columns)
    display_weeks = st.slider(
        "顯示最近幾週", 
        min_value=1, max_value=total_weeks, 
        value=total_weeks if total_weeks <= 15 else 15
    )

    plot_df = edited_df.iloc[:, -display_weeks:]
    plot_total = plot_df.sum(axis=0)
    plot_total.name = "Total"

    fig1 = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04,  
        row_heights=[0.55, 0.45], specs=[[{"secondary_y": True}], [{"secondary_y": False}]]
    )

    # 背景 Bar
    fig1.add_trace(
        go.Bar(
            x=plot_total.index, y=plot_total.values, name="每週總計 (Total)", 
            marker=dict(color='rgba(148, 163, 184, 0.15)', line=dict(color='rgba(148, 163, 184, 0.4)', width=1)),
            hoverinfo='x+y+name', opacity=0.9, showlegend=True 
        ), secondary_y=True, row=1, col=1
    )

    # 折線
    for category in plot_df.index:
        line_color = color_map.get(category, '#000000')
        fig1.add_trace(
            go.Scatter(
                x=plot_df.columns, y=plot_df.loc[category].values, 
                mode='lines+markers', name=category,
                line=dict(width=4.5, color=line_color), 
                marker=dict(size=9, color=line_color, line=dict(width=2.0, color='white')), 
                showlegend=True 
            ), secondary_y=False, row=1, col=1
        )

    # 下方數據表格矩陣
    table_df = pd.concat([pd.DataFrame(plot_total).T, plot_df])
    n_rows = len(table_df)
    y_pos = list(range(n_rows-1, -1, -1)) 

    for i, idx in enumerate(table_df.index):
        y = y_pos[i]
        bg_col = "#f8fafc" if idx == "Total" else ("#ffffff" if i % 2 == 0 else "#f1f5f9")
        fig1.add_hrect(y0=y-0.5, y1=y+0.5, fillcolor=bg_col, opacity=1, layer="below", line_width=0, row=2, col=1)

    for y_line in range(n_rows + 1):
        fig1.add_hline(y=(n_rows - 1 - y_line) + 0.5, line_color='#cbd5e1', line_width=1.5, layer="below", row=2, col=1)

    # 數據矩陣內置數字 (保持 24px 純黑)
    for i, col_name in enumerate(table_df.columns):
        col_data = table_df[col_name].values
        text_labels = [f"<b>{int(col_data[0])}</b>"] + [str(int(val)) for val in col_data[1:]]
        fig1.add_trace(
            go.Scatter(
                x=[col_name]*n_rows, y=y_pos, text=text_labels, mode="text",
                textfont=dict(size=24, color="#000000", family="Microsoft JhengHei"), showlegend=False, hoverinfo="skip"
            ), row=2, col=1
        )

    # 全域佈景設定
    fig1.update_layout(
        height=1100, font=dict(family="Microsoft JhengHei, sans-serif", size=14, color="#000000"), 
        hovermode="x unified",
        plot_bgcolor='white', paper_bgcolor='white', margin=dict(t=40, l=20, r=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=14, color="#000000"))
    )
    
    # 🎯 【關鍵修正】左右兩側紅框區域字體全面放大至至少 24px 且加粗純黑
    fig1.update_yaxes(
        title_text="<b>各項測試件數 (件)</b>", 
        title_font=dict(size=24, color="#000000"),    # 左側 Y 軸標題放大至 24
        tickfont=dict(size=24, color="#000000"),      # 左側刻度數字放大至 24
        secondary_y=False, showgrid=True, gridcolor='#e2e8f0', griddash='dash', zeroline=False, row=1, col=1
    )
    fig1.update_yaxes(
        title_text="<b>每週總計 (件)</b>", 
        title_font=dict(size=24, color="#000000"),    # 右側次要 Y 軸標題放大至 24
        tickfont=dict(size=24, color="#000000"),      # 右側刻度數字放大至 24
        secondary_y=True, showgrid=False, zeroline=False, row=1, col=1
    )

    custom_y_labels = []
    for idx in table_df.index:
        if idx == "Total":
            custom_y_labels.append("<b>Total</b>")
        else:
            cat_color = color_map.get(idx, '#000000')
            custom_y_labels.append(f"<span style='color: {cat_color};'>●</span> <b>{idx}</b>")

    # 下方數據對照矩陣的左側項目標籤 (同樣屬於左側紅框範疇) 放大至 24
    fig1.update_yaxes(
        tickmode="array", tickvals=y_pos, ticktext=custom_y_labels, 
        tickfont=dict(size=24, color="#000000"),       # 項目名稱文字放大至 24
        showgrid=False, zeroline=False, range=[-0.5, n_rows-0.5], row=2, col=1
    )
    
    fig1.update_xaxes(showgrid=True, gridcolor='#e2e8f0', griddash='dash', zeroline=False, row=1, col=1)
    fig1.update_xaxes(side="top", showgrid=True, gridcolor='#e2e8f0', tickfont=dict(size=16, color="#000000"), zeroline=False, row=2, col=1)

    st.plotly_chart(fig1, use_container_width=True)


# ==========================================
# 分頁 2: 實驗室產能與消化進度看板 (完全保留最新2分頁版)
# ==========================================
with tab2:
    st.markdown("<h3 style='color: #000000; margin-top: 20px;'>📝 填寫與切換產能週別</h3>", unsafe_allow_html=True)
    
    col_btn, col_sel, _ = st.columns([2, 3, 7])
    with col_btn:
        if st.button("➕ 新增下一週產能", use_container_width=True):
            next_w = get_next_cap_week(st.session_state.capacity_db.keys())
            st.session_state.capacity_db[next_w] = st.session_state.capacity_db[st.session_state.current_cap_week]
            st.session_state.current_cap_week = next_w
            save_capacity_data(st.session_state.capacity_db)
            st.rerun()
    with col_sel:
        cap_weeks = list(st.session_state.capacity_db.keys())
        selected_week = st.selectbox(
            "切換檢視週別", 
            cap_weeks, 
            index=cap_weeks.index(st.session_state.current_cap_week), 
            label_visibility="collapsed"
        )
        if selected_week != st.session_state.current_cap_week:
            st.session_state.current_cap_week = selected_week
            st.rerun()

    current_cap_data = st.session_state.capacity_db[st.session_state.current_cap_week]
    df_calc = pd.DataFrame(current_cap_data)

    num_cols = ["週完成件數目標值", "機台數", "上週未完成件數", "本週新收件數", "本週完成總件數"]
    for col in num_cols:
        df_calc[col] = pd.to_numeric(df_calc[col], errors='coerce').fillna(0).astype(int)

    df_calc["本週測試總件數"] = df_calc["上週未完成件數"] + df_calc["本週新收件數"]
    df_calc["本週未完成件數"] = df_calc["本週測試總件數"] - df_calc["本週完成總件數"]
    df_calc["消化週數"] = (df_calc["本週未完成件數"] / df_calc["週完成件數目標值"].replace(0, 1)).round(2)

    st.markdown(f"<h3 style='color: #000000; margin-top: 20px;'>📊 產能與消化進度動態圖表 ({st.session_state.current_cap_week})</h3>", unsafe_allow_html=True)
    
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    fig2.add_trace(go.Bar(x=df_calc["測試類別"], y=df_calc["本週未完成件數"], name="本週未完成", marker_color="#dc3545", offsetgroup=0), secondary_y=False)
    fig2.add_trace(go.Bar(x=df_calc["測試類別"], y=df_calc["本週完成總件數"], name="本週完成", marker_color="#007bff", offsetgroup=0, base=df_calc["本週未完成件數"]), secondary_y=False)
    fig2.add_trace(go.Bar(x=df_calc["測試類別"], y=df_calc["週完成件數目標值"], name="週完成件數目標值", marker_color="#6c757d", opacity=0.4, offsetgroup=1), secondary_y=False)

    fig2.add_trace(go.Scatter(
        x=df_calc["測試類別"], y=df_calc["消化週數"], name="消化週數趨勢", 
        mode="lines+markers+text", text=df_calc["消化週數"].map(lambda x: f"{x:.2f}"), 
        textposition="top center", textfont=dict(size=14, family="Microsoft JhengHei", color="#000000"), 
        marker=dict(size=10, color="#fd7e14"), line=dict(width=3, color="#fd7e14")
    ), secondary_y=True)

    fig2.add_trace(go.Scatter(x=df_calc["測試類別"], y=[1.0]*len(df_calc), name="消化週數目標值(≤1)", mode="lines", line=dict(color="#ffc107", width=2, dash="dash")), secondary_y=True)

    fig2.update_layout(
        height=450, barmode="group",
        font=dict(size=15, family="Microsoft JhengHei", color="#000000"), 
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=14)), 
        hovermode="x unified", margin=dict(t=20, b=10)
    )
    fig2.update_yaxes(title_text="件數 (件)", title_font=dict(size=15, color="#000000"), tickfont=dict(size=14, color="#000000"), secondary_y=False)
    fig2.update_yaxes(title_text="消化週數 (週)", title_font=dict(size=15, color="#000000"), tickfont=dict(size=14, color="#000000"), range=[0, max(2.0, df_calc["消化週數"].max() + 0.5)], secondary_y=True)
    fig2.update_xaxes(tickfont=dict(size=15, color="#000000", family="Microsoft JhengHei"))

    _, chart_col, _ = st.columns([0.5, 11, 0.5])
    with chart_col:
        st.plotly_chart(fig2, use_container_width=True)

    df_summary = df_calc[["測試類別", "機型/項目", "機台數", "週完成件數目標值", "本週完成總件數", "本週未完成件數", "消化週數", "說明"]].copy()
    df_summary.rename(columns={"消化週數": "消化週數 目標值≤1"}, inplace=True)

    def style_high_risk(row):
        return ['background-color: #f8d7da; color: #721c24;' if row['消化週數 目標值≤1'] > 1.0 else '' for _ in row]

    styled_html = df_summary.style.hide(axis='index')\
        .apply(style_high_risk, axis=1)\
        .format({'消化週數 目標值≤1': '{:.2f}'})\
        .set_properties(**{'text-align': 'center', 'vertical-align': 'middle'})\
        .set_properties(subset=["機型/項目", "機台數", "週完成件數目標值", "本週完成總件數", "本週未完成件數", "消化週數 目標值≤1"], **{'font-size': '24px', 'color': '#000000', 'font-weight': 'bold'})\
        .set_properties(subset=['測試類別'], **{'font-size': '24px', 'white-space': 'nowrap', 'color': '#000000', 'font-weight': 'bold'})\
        .set_properties(subset=['說明'], **{'font-size': '12px', 'line-height': '1.3', 'color': '#000000'})\
        .to_html(classes="styled-table")

    _, table_col, _ = st.columns([0.5, 10, 1.5])
    with table_col:
        st.markdown(styled_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True) 
    with st.expander(f"✏️ 點擊展開/收合：手動修改面板 (目前編輯: {st.session_state.current_cap_week})", expanded=False):
        edited_raw_df = st.data_editor(
            pd.DataFrame(current_cap_data),
            use_container_width=True,
            num_rows="dynamic",
            height=280,
            key=f"raw_editor_{st.session_state.current_cap_week}"
        )
        
        if not edited_raw_df.equals(pd.DataFrame(current_cap_data)):
            st.session_state.capacity_db[st.session_state.current_cap_week] = edited_raw_df.to_dict(orient="records")
            save_capacity_data(st.session_state.capacity_db)
            st.rerun()

    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    total_test_sum = df_calc["本週測試總件數"].sum()
    total_done_sum = df_calc["本週完成總件數"].sum()
    over_items = df_calc[df_calc["消化週數"] > 1.0]

    with col1:
        st.metric(label="📊 本週累計應測試總件數", value=f"{total_test_sum} 件")
    with col2:
        st.metric(label="✅ 本週已完成案件總數", value=f"{total_done_sum} 件")
    with col3:
        if not over_items.empty:
            st.error(f"⚠️ Risk 警示：【{over_items.iloc[0]['測試類別']}】消化週數達 {over_items.iloc[0]['消化週數']:.2f} 週")
        else:
            st.success("✅ 目前所有測試類別進度均在安全水位")


# ==========================================
# 分頁 3: 人員出勤與加班管理 (還原第1版本的出勤系統)
# ==========================================
with tab3:
    st.markdown("<h2 style='color: #000000; font-weight: 900; margin-top: 10px;'>⏰ QRE 快速出勤與加班看板</h2>", unsafe_allow_html=True)
    
    # ------------------------------------------
    # 區塊 A：人員名冊管理 (預設收合不佔空間)
    # ------------------------------------------
    with st.expander("👥 人員名冊管理 (點擊展開設定人員)", expanded=False):
        col_emp1, col_emp2 = st.columns([1, 2])
        with col_emp1:
            new_emp = st.text_input("新增人員姓名：", key="new_emp_input").strip()
            if st.button("➕ 確認新增", key="btn_add_emp"):
                if new_emp and new_emp not in st.session_state.employees:
                    st.session_state.employees.append(new_emp)
                    st.toast(f"成功新增人員：{new_emp}")
                    st.rerun()
                elif new_emp in st.session_state.employees:
                    st.warning("該人員已存在！")
        with col_emp2:
            if st.session_state.employees:
                st.write(f"目前名冊：{', '.join(st.session_state.employees)}")
                del_emp = st.selectbox("選擇要移除的人員：", ["請選擇..."] + st.session_state.employees)
                if del_emp != "請選擇...":
                    if st.button("🗑️ 確認刪除", type="primary"):
                        st.session_state.employees.remove(del_emp)
                        st.toast(f"已移除人員：{del_emp}")
                        st.rerun()

    # ------------------------------------------
    # 區塊 B：快速週曆填報 (數據輸入區)
    # ------------------------------------------
    st.markdown("<h3 style='margin-top: 25px;'>📅 1. 快速週曆填報 (Key-in 數據)</h3>", unsafe_allow_html=True)
    
    col_date1, col_date2 = st.columns([2, 1])
    with col_date1:
        target_date = st.date_input("請選擇該週的任意一天：", datetime.date.today())
    
    start_of_week = target_date - datetime.timedelta(days=target_date.weekday())
    end_of_week = start_of_week + datetime.timedelta(days=6)
    week_num = start_of_week.isocalendar()[1]
    
    with col_date2:
        st.markdown(f"<h3 style='margin-top:25px; color:#1f77b4;'>週別：W{week_num}</h3>", unsafe_allow_html=True)
    
    st.info(f"📅 正在編輯：**{start_of_week.strftime('%Y/%m/%d')}** 至 **{end_of_week.strftime('%Y/%m/%d')}** 的加班時數")
    
    if not st.session_state.employees:
        st.warning("⚠️ 目前名冊中沒有人員，請先展開『人員名冊管理』新增人員。")
    else:
        week_dates = [start_of_week + datetime.timedelta(days=i) for i in range(7)]
        col_mappings = {}
        col_properties = {}
        grid_columns = []
        
        for d in week_dates:
            w_name, holiday_name, is_holiday = detect_date_info(d)
            short_w_name = w_name[-1]
            prefix = "🔴 " if is_holiday else "⚪ "
            col_label = f"{prefix}{d.strftime('%m/%d')} ({short_w_name})"
            grid_columns.append(col_label)
            date_str = d.strftime('%Y-%m-%d')
            col_mappings[col_label] = date_str
            col_properties[date_str] = holiday_name
            
        ot_db = st.session_state.overtime_data.copy()
        init_grid = pd.DataFrame(0.0, index=st.session_state.employees, columns=grid_columns)
        
        if not ot_db.empty:
            for _, row in ot_db.iterrows():
                emp = row["姓名"]
                d_str = str(row["加班日期"])
                if emp in init_grid.index:
                    for col_label, date_str in col_mappings.items():
                        if date_str == d_str:
                            init_grid.at[emp, col_label] = float(row["加班時數"])
                            
        grid_to_edit = init_grid.reset_index().rename(columns={"index": "姓名"})
        st.write("📝 **請直接在下方儲存格中輸入加班時數（0 代表未加班）：**")
        
        column_config = {"姓名": st.column_config.TextColumn("姓名", disabled=True, width=130)}
        for col in grid_columns:
            column_config[col] = st.column_config.NumberColumn(col, min_value=0.0, max_value=24.0, step=0.5, format="%.1f", width=95)
            
        ot_edited_df = st.data_editor(
            grid_to_edit,
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            key="weekly_attendance_editor"
        )
        
        if st.button("💾 儲存並更新此週加班資料", type="primary", use_container_width=True):
            melted = ot_edited_df.melt(id_vars=["姓名"], value_vars=grid_columns, var_name="日期欄位", value_name="加班時數")
            melted["加班日期"] = melted["日期欄位"].map(col_mappings)
            melted["日期屬性"] = melted["加班日期"].map(col_properties)
            new_records = melted[["姓名", "加班日期", "加班時數", "日期屬性"]].copy()
            
            current_db = st.session_state.overtime_data.copy()
            if not current_db.empty:
                week_date_strs = list(col_mappings.values())
                mask = (current_db["加班日期"].isin(week_date_strs)) & (current_db["姓名"].isin(st.session_state.employees))
                current_db = current_db[~mask]
            
            updated_db = pd.concat([current_db, new_records], ignore_index=True)
            st.session_state.overtime_data = updated_db
            save_overtime_data(updated_db)
            st.success(f"🎉 成功更新！已同步儲存至 JSON 檔案。")
            st.rerun() 

    st.divider()

    # ------------------------------------------
    # 區塊 C：各項統計與圖表 (同頁展示區)
    # ------------------------------------------
    st.markdown("<h3 style='margin-top: 25px;'>📊 2. 各項統計與圖表 (同頁即時產生)</h3>", unsafe_allow_html=True)
    
    ot_df = st.session_state.overtime_data.copy()
    if ot_df.empty:
        st.info("💡 目前尚無加班數據，請先在上方輸入數值並點擊儲存。")
    else:
        ot_df["月份"] = ot_df["加班日期"].apply(lambda x: str(x)[:7])
        
        # 關鍵 KPI
        k1, k2, k3 = st.columns(3)
        k1.metric("總累計加班時數", f"{ot_df['加班時數'].sum():.1f} 小時")
        k2.metric("總加班總筆數", f"{len(ot_df[ot_df['加班時數'] > 0])} 筆")
        k3.metric("單筆平均時數", f"{ot_df[ot_df['加班時數'] > 0]['加班時數'].mean():.1f} 小時" if len(ot_df[ot_df['加班時數'] > 0]) > 0 else "0.0 小時")
        
        st.markdown("<h3 style='margin-top: 25px;'>📅 1. 本週加班狀況檢視 (看板模式)</h3>", unsafe_allow_html=True)

        # 讓使用者在這個頁面也能自由選週別
        view_target_date = st.date_input("請選擇欲檢視週別的任意一天：", datetime.date.today(), key="view_date_picker")
        view_start_week = view_target_date - datetime.timedelta(days=view_target_date.weekday())
        view_week_dates = [view_start_week + datetime.timedelta(days=i) for i in range(7)]
        
        # 建立結構
        view_columns = []
        view_mappings = {}
        for d in view_week_dates:
            w_name, _, is_holiday = detect_date_info(d)
            short_w_name = w_name[-1]
            prefix = "🔴 " if is_holiday else "⚫ "
            col_label = f"{prefix}{d.strftime('%m/%d')}({short_w_name})"
            view_columns.append(col_label)
            view_mappings[col_label] = d.strftime('%Y-%m-%d')
            
        # 初始化空白對比 DataFrame
        view_grid = pd.DataFrame(0.0, index=st.session_state.employees, columns=view_columns)
        
        # 填入現有資料
        df = st.session_state.overtime_data
        if not df.empty:
            for _, row in df.iterrows():
                emp = row["姓名"]
                d_str = str(row["加班日期"])
                if emp in view_grid.index:
                    for col_label, date_str in view_mappings.items():
                        if date_str == d_str:
                            view_grid.at[emp, col_label] = float(row["加班時數"])
                            
        # 🛠️ HTML 表格：完全不受限制的網頁高對比表格
        html_table = """
        <table style="width:100%; border-collapse:collapse; border:3px solid #000000; font-family:'Microsoft JhengHei', sans-serif; box-shadow: 0px 4px 12px rgba(0,0,0,0.1);">
            <thead>
                <tr style="background-color:#E8E8E8; border-bottom:3px solid #000000;">
                    <th style="border:2px solid #000000; padding:15px 10px; font-size:20px; color:#000000; font-weight:900; text-align:center; width:140px;">姓名</th>
        """
        for col in view_columns:
            # 讓假日的標題顏色呈現鮮明紅色
            th_color = "#D9383A" if "🔴" in col else "#000000"
            html_table += f'<th style="border:2px solid #000000; padding:15px 10px; font-size:18px; color:{th_color}; font-weight:900; text-align:center;">{col}</th>'
        html_table += "</tr></thead><tbody>"
        
        for emp, row in view_grid.iterrows():
            html_table += '<tr style="border-bottom:2px solid #000000;">'
            html_table += f'<td style="border:2px solid #000000; padding:15px 10px; font-size:22px; color:#000000; font-weight:900; text-align:center; background-color:#F5F5F5;">{emp}</td>'
            for col in view_columns:
                val = row[col]
                # 💡 如果有加班（時數大於 0），格子自動染成黃色背景，並將字體加粗凸顯
                if val > 0:
                    bg_style = "background-color:#FFF2CC;" # 淡金黃色凸顯
                    val_str = f"<b>{val:.1f}</b>"
                else:
                    bg_style = "background-color:#FFFFFF;"
                    val_str = "0.0"
                    
                html_table += f'<td style="border:2px solid #000000; padding:15px 10px; font-size:22px; color:#000000; font-weight:900; text-align:center; {bg_style}">{val_str}</td>'
            html_table += "</tr>"
            
        html_table += "</tbody></table>"
        
        # 🔥【關鍵修復 1】：移除所有換行與行首縮進，防止 Markdown 誤將其渲染為 Code block 灰框
        html_table_clean = "".join([line.strip() for line in html_table.split("\n")])
        st.markdown(html_table_clean, unsafe_allow_html=True)
        
        # ==============================================================================
        # 移除多餘分隔線與文字，直接放置月份選擇器與圖表區塊
        # 建立雙欄版面：左邊(圖表占 80%)，右邊(總計表占 20%)
        # ==============================================================================
        st.markdown("<br><br>", unsafe_allow_html=True) # 利用一點空白取代原本的文字，視覺更舒暢

        available_months = sorted(ot_df["月份"].unique(), reverse=True)
        
        col_chart, col_summary = st.columns([4, 1])
        with col_chart:
            selected_month = st.selectbox("▼ 選擇統計月份：", available_months, key="select_trend_month")
            
            num_days = pd.Period(selected_month).days_in_month
            all_dates_in_month = pd.date_range(start=f"{selected_month}-01", periods=num_days).strftime('%Y-%m-%d').tolist()
            full_grid = pd.MultiIndex.from_product([all_dates_in_month, st.session_state.employees], names=["加班日期", "姓名"]).to_frame(index=False)
            
            df_month = ot_df[ot_df["月份"] == selected_month].copy()
            daily_trend_existing = df_month.groupby(["加班日期", "姓名"])["加班時數"].sum().reset_index()
            daily_trend_existing["加班日期"] = daily_trend_existing["加班日期"].astype(str)
            
            daily_trend = pd.merge(full_grid, daily_trend_existing, on=["加班日期", "姓名"], how="left")
            daily_trend["加班時數"] = daily_trend["加班時數"].fillna(0.0)
            daily_trend = daily_trend.sort_values(by="加班日期")
            
            # 水平錯開時間軸防重疊
            daily_trend["繪圖時間軸"] = pd.to_datetime(daily_trend["加班日期"])
            jitter_hours = [-3, -1, 1, 3]
            jitter_map = {emp: jitter_hours[i % 4] for i, emp in enumerate(st.session_state.employees)}
            daily_trend["繪圖時間軸"] = daily_trend.apply(lambda r: r["繪圖時間軸"] + pd.Timedelta(hours=jitter_map.get(r["姓名"], 0)), axis=1)
            
            fig_line = px.line(
                daily_trend, x="繪圖時間軸", y="加班時數", color="姓名", symbol="姓名",
                labels={"繪圖時間軸": "<b>日期</b>", "加班時數": "<b>時數 (hr)</b>", "姓名": "<b>姓名</b>"},
                title=f"<b>📅 {selected_month} 月份 - 全員每日加班走勢對比</b>"
            )
            fig_line.update_traces(line=dict(width=5), marker=dict(size=14, line=dict(width=2, color='#000000')))
            fig_line.update_xaxes(tickformat="%m/%d", dtick="D1", title_font=dict(size=18, color="#000000"), tickfont=dict(size=14, color="#000000"))
            fig_line.update_yaxes(title_font=dict(size=18, color="#000000"), tickfont=dict(size=14, color="#000000"))
            fig_line.update_layout(plot_bgcolor='#FFFFFF', hovermode="closest", title_font=dict(size=24, color="#000000"), legend=dict(font=dict(size=14, color="#000000"), borderwidth=2, bordercolor="#000000"))
            
            st.plotly_chart(fig_line, use_container_width=True)

        with col_summary:
            sum_data = {emp: 0.0 for emp in st.session_state.employees}
            if not df_month.empty:
                grouped = df_month.groupby("姓名")["加班時數"].sum()
                for emp, val in grouped.items():
                    if emp in sum_data:
                        sum_data[emp] = val
                        
            grand_total = sum(sum_data.values())
            
            summary_html = f"""
            <div style="margin-top: 75px;">
                <table style="width:100%; border-collapse:collapse; border:3px solid #000000; font-family:'Microsoft JhengHei', 'Arial Black', sans-serif; box-shadow: 0px 4px 10px rgba(0,0,0,0.1);">
                    <thead>
                        <tr style="background-color:#E8E8E8; border-bottom:3px solid #000000;">
                            <th style="border:2px solid #000000; padding:12px 5px; font-size:16px; color:#000000; font-weight:900; text-align:center;">姓名</th>
                            <th style="border:2px solid #000000; padding:12px 5px; font-size:16px; color:#000000; font-weight:900; text-align:center;">當月總計</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            for emp, val in sum_data.items():
                bg_color = "#FFF2CC" if val > 0 else "#FFFFFF"
                summary_html += f"""
                        <tr>
                            <td style="border:2px solid #000000; padding:10px; font-size:16px; color:#000000; font-weight:900; text-align:center; background-color:#F5F5F5;">{emp}</td>
                            <td style="border:2px solid #000000; padding:10px; font-size:20px; color:#000000; font-weight:900; text-align:center; background-color:{bg_color};">{val:.1f}</td>
                        </tr>
                """
            summary_html += f"""
                        <tr style="border-top:3px solid #000000; background-color:#D9D9D9;">
                            <td style="border:2px solid #000000; padding:10px; font-size:16px; color:#000000; font-weight:900; text-align:center;">所有人加總</td>
                            <td style="border:2px solid #000000; padding:10px; font-size:20px; color:#000000; font-weight:900; text-align:center;">{grand_total:.1f}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            """
            summary_html_clean = "".join([line.strip() for line in summary_html.split("\n")])
            st.markdown(summary_html_clean, unsafe_allow_html=True)
            
        # 3. 原始資料匯出
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("📥 點擊展開：完整數據明細與 CSV 導出", expanded=False):
            df_export = ot_df.copy()
            st.dataframe(df_export[["姓名", "加班日期", "加班時數", "日期屬性"]].sort_values(by="加班日期", ascending=False), use_container_width=True)
            csv = df_export.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載加班統計報表 (CSV)", data=csv, file_name=f"加班統計報表_{datetime.date.today()}.csv", mime="text/csv", key="download_csv_tab3")