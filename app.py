import streamlit as st
import pandas as pd
import re
import requests
from io import StringIO

# ==================== ССЫЛКА НА ТВОЮ ТАБЛИЦУ ====================
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/122GipihFaGUp2AFyhy39_EKRVY5Rbuzg-TGGK8s5wro/export?format=csv&gid=0"
# ================================================================

st.set_page_config(page_title="Haier WarRoom Navigator", page_icon="🧭", layout="centered")

@st.cache_data(ttl=10)  # Данные обновляются каждые 10 секунд
def load_data():
    try:
        # Скачиваем таблицу в сыром текстовом виде с жесткой кодировкой UTF-8
        res = requests.get(GOOGLE_SHEET_CSV_URL)
        res.encoding = 'utf-8'
        df = pd.read_csv(StringIO(res.text))
        return df
    except Exception:
        return pd.DataFrame()

def parse_excel_cell(cell_text):
    """Очищает многострочную вставку из Excel от тегов [📄 PDF·RU]"""
    lines = cell_text.strip().split('\n')
    return [re.sub(r'^\[.*?\]\s*', '', line).strip() for line in lines if line.strip()]

# Загружаем сырые данные из Google Sheets
df = load_data()

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
    elif df.empty:
        st.error("Не удалось подключиться к Google Таблице. Проверь общую ссылку.")
    else:
        st.markdown("---")
        query_clean = search_query.strip().lower()
        
        # Определяем колонки по их порядковому номеру (1-я — имя, 6-я — ссылка)
        name_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        link_col = df.columns[6] if len(df.columns) > 6 else df.columns[-1]

        # СЦЕНАРИЙ 1: Вставка многострочной ячейки из Excel
        if '[' in search_query and ']' in search_query:
            clean_file_names = parse_excel_cell(search_query)
            
            for name in clean_file_names:
                found_link = None
                # Ищем точное совпадение по всей таблице
                for _, row in df.iterrows():
                    if str(row[name_col]).strip().lower() == name.lower():
                        found_link = str(row[link_col]).strip()
                        break
                
                if found_link and found_link.startswith('http'):
                    st.success(f"🔗 **[{name}]({found_link})**")
                else:
                    # Если точного нет, ищем частичное совпадение в строках
                    found_part = False
                    for _, row in df.iterrows():
                        f_name = str(row[name_col]).strip()
                        f_link = str(row[link_col]).strip()
                        if name.lower() in f_name.lower() and f_link.startswith('http'):
                            st.success(f"🔗 **[{f_name}]({f_link})**")
                            found_part = True
                    if not found_part:
                        st.error(f"❌ **{name}** — *Файл не найден в реестре*")
                        
        # СЦЕНАРИЙ 2: Обычный сквозной поиск по цифрам модели (14979, 2959)
        else:
            found_any = False
            for _, row in df.iterrows():
                f_name = str(row[name_col]).strip()
                f_link = str(row[link_col]).strip()
                
                # Если введенные цифры есть в имени файла — выводим его
                if query_clean in f_name.lower() and f_link.startswith('http'):
                    st.success(f"🔗 **[{f_name}]({f_link})**")
                    found_any = True
            
            if not found_any:
                st.warning(f"По запросу '{search_query}' ничего не найдено. Убедись, что модель есть на Гугл Диске.")
