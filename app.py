import streamlit as st
import pandas as pd
import re

# ==================== НАСТРОЙКИ СВЯЗИ С GOOGLE SHEETS ====================
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/122GipihFaGUp2AFyhy39_EKRVY5Rbuzg-TGGK8s5wro/export?format=csv&gid=0"
# =========================================================================

st.set_page_config(page_title="Haier WarRoom Navigator", page_icon="🧭", layout="centered")

@st.cache_data(ttl=30)  # Обновление каждую минуту
def load_google_files_registry():
    try:
        # Качаем таблицу из облака
        df = pd.read_csv(GOOGLE_SHEET_CSV_URL)
        if df.empty:
            return {}
            
        registry = {}
        
        # Автоматически находим нужные колонки, не привязываясь к языку
        # Имя файла — это всегда то, что идет в начале (1-я или 2-я колонка)
        name_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        for col in df.columns:
            if 'name' in str(col).lower() or 'имя' in str(col).lower():
                name_col = col
                break
                
        # Ссылку ищем по содержимому: где есть веб-адреса
        link_col = df.columns[-1]
        for col in df.columns:
            # Проверяем первую живую строчку в колонке на наличие ссылки
            first_val = str(df[col].iloc[0]).lower() if not df[col].empty else ""
            if 'http' in first_val or 'drive' in first_val or 'url' in str(col).lower() or 'ссылка' in str(col).lower():
                link_col = col
                break

        # Забиваем данные в чистый словарь для моментального сквозного поиска
        for _, row in df.iterrows():
            f_name = str(row[name_col]).strip()
            f_link = str(row[link_col]).strip()
            if f_name and f_link and f_link.startswith('http'):
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
    placeholder="Вставь скопированное или напиши цифры модели (например, 2959)...",
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
                        
        # СЦЕНАРИЙ 2: Обычный сквозной поиск по цифрам / части слова
        else:
            found_any = False
            for f_name, f_link in files_registry.items():
                if query_clean in f_name:
                    st.success(f"🔗 **[{f_name}]({f_link})**")
                    found_any = True
            
            if not found_any:
                st.warning(f"По запросу '{search_query}' ничего не найдено. Убедись, что файл залит на Диск.")
