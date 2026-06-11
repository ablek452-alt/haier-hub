import streamlit as st
import pandas as pd
import os
import re

st.set_page_config(page_title="Haier WarRoom Navigator", page_icon="🧭", layout="centered")

# Жестко смотрим на локальный Excel-файл, как в Терминале
EXCEL_FILE = "haier_file_registry.xlsx"

@st.cache_data(ttl=5)  # Быстрое чтение файла
def load_local_excel():
    if not os.path.exists(EXCEL_FILE):
        return []
    try:
        df = pd.read_excel(EXCEL_FILE)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Названия колонок из твоего самого первого сканера
        name_col = 'file_name' if 'file_name' in df.columns else df.columns[0]
        link_col = 'drive_link' if 'drive_link' in df.columns else df.columns[1]
        
        registry_data = []
        for _, row in df.iterrows():
            f_name = str(row[name_col]).strip()
            f_link = str(row[link_col]).strip()
            if f_name and f_link:
                registry_data.append({'name': f_name, 'link': f_link})
        return registry_data
    except Exception:
        return []

def parse_excel_cell(cell_text):
    """Очищает многострочную вставку из Excel от тегов [📄 PDF·RU]"""
    lines = cell_text.strip().split('\n')
    return [re.sub(r'^\[.*?\]\s*', '', line).strip() for line in lines if line.strip()]

# Загружаем базу из локального Excel
files_registry = load_local_excel()

st.title("🧭 Поиск файлов в Google Drive")
st.markdown("Вставь ячейку из Excel или просто напиши номер модели / цифры.")

# Одно поле ввода
search_query = st.text_area(
    "Запрос:",
    placeholder="Вставь скопированное или напиши цифры модели (например, 2959 или 14979)...",
    height=120,
    label_visibility="collapsed"
)

if st.button("Найти файлы на Диске", type="primary", use_container_width=True):
    if not search_query.strip():
        st.warning("Поле ввода пустое.")
    elif not files_registry:
        st.error(f"Файл {EXCEL_FILE} не найден в папке проекта или он пустой! Запусти сначала scanner.py на компьютере.")
    else:
        st.markdown("---")
        query_clean = search_query.strip().lower()
        
        # СЦЕНАРИЙ 1: Вставка многострочной ячейки из Excel
        if '[' in search_query and ']' in search_query:
            clean_file_names = parse_excel_cell(search_query)
            
            for name in clean_file_names:
                found_link = None
                for file_item in files_registry:
                    if file_item['name'].lower() == name.lower():
                        found_link = file_item['link']
                        break
                
                if found_link:
                    st.success(f"🔗 **[{name}]({found_link})**")
                else:
                    # Частичный поиск, если точного нет
                    found_part = False
                    for file_item in files_registry:
                        if name.lower() in file_item['name'].lower():
                            st.success(f"🔗 **[{file_item['name']}]({file_item['link']})**")
                            found_part = True
                    if not found_part:
                        st.error(f"❌ **{name}** — *Файл не найден в реестре*")
                        
        # СЦЕНАРИЙ 2: Обычный сквозной поиск по цифрам модели (14979, 2959)
        else:
            found_any = False
            for file_item in files_registry:
                if query_clean in file_item['name'].lower():
                    st.success(f"🔗 **[{file_item['name']}]({file_item['link']})**")
                    found_any = True
            
            if not found_any:
                st.warning(f"По запросу '{search_query}' ничего не найдено.")
