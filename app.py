import streamlit as st
import pandas as pd
import re
import requests

# ==================== НАСТРОЙКИ СВЯЗИ С GOOGLE SHEETS ====================
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/122GipihFaGUp2AFyhy39_EKRVY5Rbuzg-TGGK8s5wro/export?format=csv&gid=0"
# =========================================================================

st.set_page_config(page_title="Haier WarRoom Navigator", page_icon="🧭", layout="centered")

@st.cache_data(ttl=10)  # Кэш всего 10 секунд, чтобы мгновенно видеть обновления
def load_google_files_registry():
    try:
        # Скачиваем напрямую через requests с жестким указанием кодировки UTF-8
        response = requests.get(GOOGLE_SHEET_CSV_URL)
        response.encoding = 'utf-8'
        
        # Читаем текст как CSV
        from io import StringIO
        df = pd.read_csv(StringIO(response.text))
        
        if df.empty:
            return {}
            
        df.columns = [str(c).strip() for c in df.columns]
        
        # Ищем колонку с именем файла и колонку со ссылкой
        name_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        link_col = df.columns[-1]
        
        for col in df.columns:
            col_lower = str(col).lower()
            if 'name' in col_lower or 'имя' in col_lower:
                name_col = col
                break
                
        for col in df.columns:
            if df[col].empty:
                continue
            first_val = str(df[col].iloc[0]).lower()
            if 'http' in first_val or 'drive' in first_val or 'url' in str(col).lower() or 'ссылка' in str(col).lower():
                link_col = col
                break

        # Наполняем чистый словарь
        registry = {}
        for _, row in df.iterrows():
            f_name = str(row[name_col]).strip()
            f_link = str(row[link_col]).strip()
            if f_name and f_link and f_link.startswith('http'):
                registry[f_name] = f_link
                
        return registry
    except Exception:
        return {}

def parse_excel_file_cell(cell_text):
    """Очищает многострочную вставку из Excel от тегов контента"""
    lines = cell_text.strip().split('\n')
    return [re.sub(r'^\[.*?\]\s*', '', line).strip() for line in lines if line.strip()]

# Загружаем базу ссылок
files_registry = load_google_files_registry()

st.title("🧭 Поиск файлов в Google Drive")
st.markdown("Вставь ячейку из Excel или просто напиши номер модели / цифры.")

# Одно поле для ввода
search_query = st.text_area(
    "Запрос:",
    placeholder="Вставь скопированное или напиши цифры модели (например, 2959 или 14979)...",
    height=120,
    label_visibility="collapsed"
)

if st.button("Найти файлы на Диске", type="primary", use_container_width=True):
    if not search_query.strip():
        st.warning("Поле ввода пустое.")
    else:
        st.markdown("---")
        query_clean = search_query.strip().lower()
        
        # СЦЕНАРИЙ 1: Вставка из Excel со скобками
        if '[' in search_query and ']' in search_query:
            clean_file_names = parse_excel_file_cell(search_query)
            
            for name in clean_file_names:
                # Ищем без учета регистра
                found_link = None
                for f_name, f_link in files_registry.items():
                    if f_name.lower() == name.lower():
                        found_link = f_link
                        break
                
                if found_link:
                    st.success(f"🔗 **[{name}]({found_link})**")
                else:
                    # Поиск по части имени, если точного совпадения нет
                    found_part = False
                    for f_name, f_link in files_registry.items():
                        if name.lower() in f_name.lower():
                            st.success(f"🔗 **[{f_name}]({f_link})**")
                            found_part = True
                    if not found_part:
                        st.error(f"❌ **{name}** — *Файл не найден в реестре*")
                        
        # СЦЕНАРИЙ 2: Обычный сквозной поиск по цифрам модели
        else:
            found_any = False
            for f_name, f_link in files_registry.items():
                if query_clean in f_name.lower():
                    st.success(f"🔗 **[{f_name}]({f_link})**")
                    found_any = True
            
            if not found_any:
                st.warning(f"По запросу '{search_query}' ничего не найдено. Проверь, залит ли файл на Гугл Диск и обновлена ли таблица.")
