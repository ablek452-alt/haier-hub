import streamlit as st
import pandas as pd
import re

# ==================== НАСТРОЙКИ СВЯЗИ С GOOGLE SHEETS ====================
# Твоя ссылка на CSV-экспорт реестра (из твоего Apps Script)
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/122GipihFaGUp2AFyhy39_EKRVY5Rbuzg-TGGK8s5wro/export?format=csv&gid=0"
# =========================================================================

st.set_page_config(page_title="Haier WarRoom Navigator", page_icon="🧭", layout="centered")

# Функция загрузки реестра файлов из Google Sheets с кэшированием
@st.cache_data(ttl=600)
def load_google_files_registry():
    try:
        df = pd.read_csv(GOOGLE_SHEET_CSV_URL)
        df.columns = [c.strip() for c in df.columns]
        
        # Берем колонки 'Имя файла' и 'Ссылка' из твоей таблицы
        name_col = 'Имя файла' if 'Имя файла' in df.columns else df.columns[1]
        link_col = 'Ссылка' if 'Ссылка' in df.columns else df.columns[6]
        
        registry = pd.Series(df[link_col].values, index=df[name_col].str.lower()).to_dict()
        return registry
    except Exception:
        # Резервные заглушки на случай сбоя сети
        return {
            'презентация_929a.pdf': 'https://drive.google.com',
            'каталог_x11.pptx': 'https://drive.google.com'
        }

def parse_excel_file_cell(cell_text):
    """Чистит строки из Excel от тегов вроде [📄 PDF·RU]"""
    lines = cell_text.strip().split('\n')
    return [re.sub(r'^\[.*?\]\s*', '', line).strip() for line in lines if line.strip()]

# Загружаем базу ссылок с диска
files_registry = load_google_files_registry()

# --- ИНТЕРФЕЙС БЕЗ СЕТЕЙ И ЛИШНЕГО МУСОРА ---
st.title("🧭 Поиск файлов в Google Drive")
st.markdown("Вставь сюда скопированную из Excel ячейку **«Файлы на Google Drive»** или просто введи номер модели / SKU руками.")

# Только ОДНО поле для ввода
search_query = st.text_area(
    "Запрос для поиска или буфер обмена:",
    placeholder="Вставь скопированное из Excel или напиши номер модели (например, 14979)...",
    height=120,
    label_visibility="collapsed"
)

if st.button("Найти файлы на Диске", type="primary", use_container_width=True):
    if not search_query.strip():
        st.warning("Поле пустое. Введите запрос.")
    else:
        st.markdown("---")
        
        # СЦЕНАРИЙ 1: Пользователь вставил ячейку со списком файлов (есть квадратные скобки)
        if '[' in search_query and ']' in search_query:
            clean_file_names = parse_excel_file_cell(search_query)
            
            for name in clean_file_names:
                link = files_registry.get(name.lower(), None)
                if link:
                    st.success(f"🔗 **[{name}]({link})**")
                else:
                    st.error(f"❌ **{name}** — *Файл не найден в реестре Google Диска*")
                    
        # СЦЕНАРИЙ 2: ПРАВИЛЬНЫЙ ТЕКСТОВЫЙ ПОИСК (по части слова/цифрам модели)
        else:
            query_clean = search_query.strip().lower()
            found_any = False
            
            # Бежим по всему реестру и ищем совпадения по части названия
            for file_name, link in files_registry.items():
                if query_clean in file_name:
                    # Показываем красивую ссылку с оригинальным именем файла
                    # Ищем оригинальное имя файла (без нижнего регистра)
                    st.success(f"🔗 **[{file_name}]({link})**")
                    found_any = True
            
            if not found_any:
                st.warning(f"По запросу '{search_query}' ничего не найдено. Проверьте правильность ввода.")
