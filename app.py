import streamlit as st
import pandas as pd
import re
import requests
from io import StringIO

# ==================== НАСТРОЙКИ СВЯЗИ С GOOGLE SHEETS ====================
# Твоя ссылка на CSV-экспорт таблицы реестра (куда макрос складывает данные)
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/122GipihFaGUp2AFyhy39_EKRVY5Rbuzg-TGGK8s5wro/export?format=csv&gid=0"
# =========================================================================

st.set_page_config(page_title="Haier WarRoom Navigator", page_icon="🧭", layout="centered")

@st.cache_data(ttl=10)  # Данные обновляются из облака каждые 10 секунд
def load_live_google_data():
    try:
        # Скачиваем таблицу напрямую из Google Sheets с жесткой кодировкой UTF-8
        res = requests.get(GOOGLE_SHEET_CSV_URL)
        res.encoding = 'utf-8'
        
        # Читаем текст как CSV-таблицу
        df = pd.read_csv(StringIO(res.text))
        if df.empty:
            return []
            
        df.columns = [str(c).strip() for c in df.columns]
        
        # Динамически определяем колонки: Имя файла (File Name) и Ссылка (Url/Link)
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
        
        # Собираем данные в простой список словарей для сквозного поиска
        registry_data = []
        for _, row in df.iterrows():
            f_name = str(row[name_col]).strip()
            f_link = str(row[link_col]).strip()
            if f_name and f_link and f_link.startswith('http'):
                registry_data.append({'name': f_name, 'link': f_link})
        return registry_data
    except Exception:
        return []

def parse_excel_file_cell(cell_text):
    """Очищает многострочную вставку из Excel от тегов контента типа [📄 PDF·RU]"""
    lines = cell_text.strip().split('\n')
    return [re.sub(r'^\[.*?\]\s*', '', line).strip() for line in lines if line.strip()]

# Загружаем актуальную базу напрямую из Google
files_registry = load_live_google_data()

st.title("🧭 Поиск файлов в Google Drive")
st.markdown("Вставь скопированную ячейку из Excel или просто напиши номер модели / любые цифры.")

# Одно универсальное поле ввода
search_query = st.text_area(
    "Запрос:",
    placeholder="Вставь данные или введи цифры модели (например, 2959 или 14979)...",
    height=120,
    label_visibility="collapsed"
)

if st.button("Найти файлы на Диске", type="primary", use_container_width=True):
    if not search_query.strip():
        st.warning("Поле ввода пустое.")
    elif not files_registry:
        st.error("Ошибка: База данных пуста или нет связи с Google Таблицей. Проверь ссылку.")
    else:
        st.markdown("---")
        query_clean = search_query.strip().lower()
        
        # СЦЕНАРИЙ 1: Пользователь вставил ячейку со структурой из Excel (есть квадратные скобки)
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
                    # Если точного совпадения нет, ищем по части названия
                    found_part = False
                    for file_item in files_registry:
                        if name.lower() in file_item['name'].lower():
                            st.success(f"🔗 **[{file_item['name']}]({file_item['link']})**")
                            found_part = True
                    if not found_part:
                        st.error(f"❌ **{name}** — *Файл не найден в облачном реестре*")
                        
        # СЦЕНАРИЙ 2: Тот самый первый, быстрый поиск по любым цифрам модели или куску текста
        else:
            found_any = False
            for file_item in files_registry:
                if query_clean in file_item['name'].lower():
                    st.success(f"🔗 **[{file_item['name']}]({file_item['link']})**")
                    found_any = True
            
            if not found_any:
                st.warning(f"По запросу '{search_query}' ничего не найдено. Проверь, залит ли файл на Google Диск.")
