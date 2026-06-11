import streamlit as st
import pandas as pd
import re

# ==================== НАСТРОЙКИ СВЯЗИ С GOOGLE SHEETS ====================
# Ссылка на твою Google Таблицу (CSV-экспорт)
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/122GipihFaGUp2AFyhy39_EKRVY5Rbuzg-TGGK8s5wro/export?format=csv&gid=0"
# =========================================================================

st.set_page_config(page_title="Haier WarRoom Navigator", page_icon="🧭", layout="centered")

# Загрузка базы из Google Sheets
@st.cache_data(ttl=300)  # Кэш на 5 минут, чтобы данные обновлялись быстрее
def load_google_files_registry():
    try:
        df = pd.read_csv(GOOGLE_SHEET_CSV_URL)
        df.columns = [c.strip() for c in df.columns]
        
        # Названия колонок из твоего Apps Script
        name_col = 'Имя файла' if 'Имя файла' in df.columns else df.columns[1]
        link_col = 'Ссылка' if 'Ссылка' in df.columns else df.columns[6]
        
        # Переводим в список словарей для простого сквозного поиска
        registry_data = []
        for _, row in df.iterrows():
            f_name = str(row[name_col]).strip()
            f_link = str(row[link_col]).strip()
            if f_name and f_link:
                registry_data.append({'name': f_name, 'link': f_link})
        return registry_data
    except Exception:
        return []

def parse_excel_file_cell(cell_text):
    """Очищает вставку из Excel от тегов контента"""
    lines = cell_text.strip().split('\n')
    return [re.sub(r'^\[.*?\]\s*', '', line).strip() for line in lines if line.strip()]

# Инициализируем базу данных
files_registry = load_google_files_registry()

st.title("🧭 Поиск файлов в Google Drive")
st.markdown("Вставь ячейку из Excel или просто напиши номер модели / цифры (например, `2959` или `14979`).")

# Одно универсальное поле ввода
search_query = st.text_area(
    "Запрос:",
    placeholder="Вставь данные или введи часть названия/модели...",
    height=120,
    label_visibility="collapsed"
)

if st.button("Найти файлы на Диске", type="primary", use_container_width=True):
    if not search_query.strip():
        st.warning("Поле ввода пустое.")
    else:
        st.markdown("---")
        query_clean = search_query.strip().lower()
        
        # СЦЕНАРИЙ 1: Вставили многострочную структуру из Excel (проверяем по скобкам)
        if '[' in search_query and ']' in search_query:
            clean_file_names = parse_excel_file_cell(search_query)
            
            for name in clean_file_names:
                # Ищем точное совпадение для очищенного имени файла
                found_link = None
                for file_item in files_registry:
                    if file_item['name'].lower() == name.lower():
                        found_link = file_item['link']
                        break
                
                if found_link:
                    st.success(f"🔗 **[{name}]({found_link})**")
                else:
                    # Если точного совпадения нет, пробуем найти этот файл хотя бы по части имени
                    partial_links = [item for item in files_registry if name.lower() in item['name'].lower()]
                    if partial_links:
                        for p_item in partial_links:
                            st.success(f"🔗 **[{p_item['name']}]({p_item['link']})**")
                    else:
                        st.error(f"❌ **{name}** — *Файл не найден в реестре*")
                        
        # СЦЕНАРИЙ 2: Тот самый первый, быстрый поиск по цифрам, модели или части слова
        else:
            found_any = False
            for file_item in files_registry:
                # Если поисковый запрос (цифры или буквы) есть внутри имени файла — выводим его!
                if query_clean in file_item['name'].lower():
                    st.success(f"🔗 **[{file_item['name']}]({file_item['link']})**")
                    found_any = True
            
            if not found_any:
                st.warning(f"По запросу '{search_query}' ничего не найдено. Убедись, что файл залит на Диск.")
