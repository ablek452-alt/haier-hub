import streamlit as st
import pandas as pd
import requests
import io

st.set_page_config(page_title="Haier Material Hub", layout="wide", page_icon="☁️")

st.title("☁️ Портал материалов Haier (СНГ)")
st.markdown("Мгновенный поиск презентаций, PDF-файлов и графики напрямую из облачного реестра.")
st.markdown("---")

# Константы твоей экосистемы
API_KEY = "AIzaSyAQy_9IMampwFE6-zUW0UyO_vFH45bXGEk"
SHEET_ID = "122GipihFaGUp2AFyhy39_EKRVY5Rbuzg-TGGK8s5wro"
SHEET_NAME = "Реестр_файлов"

@st.cache_data(ttl=60)  # Кэш на 1 минуту, чтобы не спамить таблицу запросами
def load_data_from_sheet():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}&key={API_KEY}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            df = pd.read_csv(io.StringIO(response.text), header=None)
            return df
        return None
    except:
        return None

df = load_data_from_sheet()

if df is None or df.empty:
    st.warning("⚠️ База данных реестра временно недоступна. Попробуйте обновить страницу.")
    st.stop()

search_query = st.text_input("🔍 Введите модель, серию или код (например: 14979, Flexis, X11, Coral):").strip()

if search_query:
    df_str = df.astype(str)
    mask = df_str.apply(lambda row: row.str.contains(search_query, case=False, na=False)).any(axis=1)
    results = df[mask]
    
    if not results.empty:
        st.success(f"📊 Найдено материалов: {len(results)}")
        
        for idx, row in results.iterrows():
            if idx == 0 and ("Имя" in str(row[1]) or "Name" in str(row[1])):
                continue
                
            fname = str(row[1])
            ext = str(row[2]).upper().strip()
            folder_path = str(row[3])
            drive_id = str(row[5]).strip()
            backup_url = str(row[6]).strip()
            
            if not drive_id or drive_id == "nan" or len(drive_id) < 10:
                if "file/d/" in backup_url:
                    drive_id = backup_url.split("file/d/")[1].split("/")[0]
                elif "id=" in backup_url:
                    drive_id = backup_url.split("id=")[1].split("&")[0]
            
            f_type = f"📄 {ext}"
            if ext in ['PNG', 'JPG', 'JPEG', 'WEBP']: f_type = "🖼 Фото"
            elif ext in ['PPTX', 'PPT', 'PDF']: f_type = "📄 Презентация / PDF"
            elif ext in ['ZIP', 'RAR']: f_type = "📦 Архив"
            elif ext in ['XLSX', 'XLS']: f_type = "📊 Таблица"

            view_link = f"https://drive.google.com/file/d/{drive_id}/view?usp=sharing"
            download_link = f"https://drive.google.com/uc?export=download&id={drive_id}"
            
            with st.container():
                col1, col2, col3 = st.columns([2, 5, 3])
                with col1:
                    st.markdown(f"**{f_type}**")
                with col2:
                    st.write(fname)
                    st.caption(f"📂 Путь в облаке: {folder_path}")
                with col3:
                    if drive_id and drive_id != "nan" and len(drive_id) > 10:
                        st.markdown(f"[👁 Открыть]({view_link}) | [📥 Скачать]({download_link})")
                    else:
                        st.caption("⚠️ Ссылка недоступна")
                st.markdown("<hr style='margin:0.5em 0px;'>", unsafe_allow_html=True)
    else:
        st.warning("❌ В реестре ничего не найдено.")
