import streamlit as st
import pandas as pd
import re

# ==================== НАСТРОЙКИ СВЯЗИ С GOOGLE SHEETS ====================
# Твоя рабочая ссылка на экспорт реестра
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/122GipihFaGUp2AFyhy39_EKRVY5Rbuzg-TGGK8s5wro/export?format=csv&gid=0"
# =========================================================================

st.set_page_config(page_title="Haier WarRoom Navigator", page_icon="🧭", layout="centered")

# Загрузка базы из Google Sheets
@st.cache_data(ttl=300)  # Кэш на 5 минут, чтобы сайт обновлялся быстро
def load_google_files_registry():
    try:
        df = pd.read_csv(GOOGLE_SHEET_CSV_URL)
        df.columns = [c.strip() for c in df.columns]
        
        # Колонки из твоего скрипта: 'Имя файла' (1-я) и 'Ссылка' (6-я)
        name_col = 'Имя файла' if 'Имя файла' in df.columns else df.columns[1]
        link_col = 'Ссылка' if 'Ссылка' in df.columns else df.columns[6]
        
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
    """Очищает многострочную вставку из Excel от тегов контента"""
    lines = cell_text.strip().split('\n')
    return [re.sub(r'^\[.*?\]\s*', '', line).strip() for line in lines if line.strip()]

# Инициализируем базу данных
files_registry = load_google_files_registry()

st.title("🧭 Поиск файлов в Google Drive")
st.markdown("Вставь ячейку из Excel или просто напиши номер модели / цифры (например, `14979` или `2959`).")

# Одно универсальное поле ввода — как в самом начале
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
        
        # СЦЕНАРИЙ 1: Менеджер вставил ячейку из Excel (проверяем по квадратным скобкам)
        if '[' in search_query and ']' in search_query:
            clean_file_names = parse_excel_file_cell(search_query)
            
            for name in clean_file_names:
                found_link = None
                for file_item in files_registry:
                    if file_item['name'].lower() == name.lower():
                        found_link = file_item['link']
                        break
                
                if found_link:
                    st.success(f"🔗 **[{name}]({found_link})**")
                else:
                    # Если точного совпадения нет, ищем этот файл по части имени
                    partial_links = [item for item in files_registry if name.lower() in item['name'].lower()]
                    if partial_links:
                        for p_item in partial_links:
                            st.success(f"🔗 **[{p_item['name']}]({p_item['link']})**")
                    else:
                        st.error(f"❌ **{name}** — *Файл не найден в реестре*")
                        
        # СЦЕНАРИЙ 2: Тот самый первый поиск по любым цифрам, буквам или куску модели
        else:
            found_any = False
            for file_item in files_registry:
                # Если то, что ввели (например, 14979), есть в имени файла — просто выводим ссылку
                if query_clean in file_item['name'].lower():
                    st.success(f"🔗 **[{file_item['name']}]({file_item['link']})**")
                    found_any = True
            
            if not found_any:
                st.warning(f"По запросу '{search_query}' ничего не найдено. Убедись, что файл залит на Диск.")
