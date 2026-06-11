import streamlit as st
import pandas as pd
import re

# ==================== НАСТРОЙКИ СВЯЗИ С GOOGLE SHEETS ====================
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/122GipihFaGUp2AFyhy39_EKRVY5Rbuzg-TGGK8s5wro/export?format=csv&gid=0"
# =========================================================================

st.set_page_config(page_title="Haier WarRoom Navigator", page_icon="🧭", layout="centered")

# Функция загрузки реестра файлов из Google Sheets с кэшированием
@st.cache_data(ttl=60)  # Сброс кэша каждую минуту, чтобы новые файлы сразу находились
def load_google_files_registry():
    try:
        df = pd.read_csv(GOOGLE_SHEET_CSV_URL)
        df.columns = [c.strip() for c in df.columns]
        
        # Индексы колонок: 1-я — Имя файла, 6-я — Ссылка
        name_col = 'Имя файла' if 'Имя файла' in df.columns else df.columns[1]
        link_col = 'Ссылка' if 'Ссылка' in df.columns else df.columns[6]
        
        # Создаем чистый плоский словарь {имя_файла.lower(): ссылка}
        registry = {}
        for _, row in df.iterrows():
            f_name = str(row[name_col]).strip()
            f_link = str(row[link_col]).strip()
            if f_name and f_link:
                registry[f_name.lower()] = f_link
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

# Одно универсальное поле ввода
search_query = st.text_area(
    "Запрос:",
    placeholder="Вставь скопированное или напиши цифры модели...",
    height=120,
    label_visibility="collapsed"
)

if st.button("Найти файлы на Диске", type="primary", use_container_width=True):
    if not search_query.strip():
        st.warning("Поле ввода пустое.")
    else:
        st.markdown("---")
        query_clean = search_query.strip().lower()
        
        # СЦЕНАРИЙ 1: Вставили ячейку из Excel (есть квадратные скобки)
        if '[' in search_query and ']' in search_query:
            clean_file_names = parse_excel_file_cell(search_query)
            
            for name in clean_file_names:
                link = files_registry.get(name.lower(), None)
                if link:
                    st.success(f"🔗 **[{name}]({link})**")
                else:
                    # Если точного совпадения нет, ищем по части имени файла
                    found_part = False
                    for f_name, f_link in files_registry.items():
                        if name.lower() in f_name:
                            st.success(f"🔗 **[{f_name}]({f_link})**")
                            found_part = True
                    if not found_part:
                        st.error(f"❌ **{name}** — *Файл не найден в реестре*")
                        
        # СЦЕНАРИЙ 2: Тот самый первый сквозной поиск по цифрам / части слова
        else:
            found_any = False
            for f_name, f_link in files_registry.items():
                if query_clean in f_name:
                    st.success(f"🔗 **[{f_name}]({f_link})**")
                    found_any = True
            
            if not found_any:
                st.warning(f"По запросу '{search_query}' ничего не найдено. Убедись, что файл залит на Диск.")
