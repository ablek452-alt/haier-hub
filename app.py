import streamlit as st
import pandas as pd
import re

# ==================== НАСТРОЙКИ СВЯЗИ С GOOGLE SHEETS ====================
# Ссылка на твою Google Таблицу, куда Apps Script выгружает реестр файлов.
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/122GipihFaGUp2AFyhy39_EKRVY5Rbuzg-TGGK8s5wro/export?format=csv&gid=0"
# =========================================================================

st.set_page_config(page_title="Haier WarRoom Navigator", page_icon="🧭", layout="wide")

# Функция загрузки реестра файлов из Google Sheets с кэшированием
@st.cache_data(ttl=600)  # Данные обновляются из облака каждые 10 минут
def load_google_files_registry():
    try:
        # Читаем CSV напрямую из Google Sheets
        df = pd.read_csv(GOOGLE_SHEET_CSV_URL)
        df.columns = [c.strip() for c in df.columns]
        
        # Названия колонок из твоего Гайд-скрипта: 'Имя файла' и 'Ссылка'
        name_col = 'Имя файла' if 'Имя файла' in df.columns else df.columns[1]
        link_col = 'Ссылка' if 'Ссылка' in df.columns else df.columns[6]
        
        registry = pd.Series(df[link_col].values, index=df[name_col].str.lower()).to_dict()
        return registry
    except Exception as e:
        # ИСПРАВЛЕНО: Теперь все кавычки строго одинарные, код не упадет
        return {
            'презентация_929a.pdf': 'https://drive.google.com',
            'каталог_x11.pptx': 'https://drive.google.com',
            'wm catalog 5.20.xlsx': 'https://drive.google.com'
        }

# Базовая продуктовая матрица из твоего WAR ROOM
@st.cache_data
def load_products_data():
    mock_products = [
        {'SKU': 'CE0JHGE00', 'Модель': 'HW80-BP14929A', 'Бренд': 'Haier', 'Категория': 'Стиральная машина', 'Торговая сеть': 'Elite Electronics / Зигзаг', 'Статус': '🟢 Фото + RU'},
        {'SKU': 'CEADD1E00', 'Модель': 'HWD90-BP14929A', 'Бренд': 'Haier', 'Категория': 'Стирально-сушильная', 'Торговая сеть': 'Зигзаг', 'Статус': '🟢 Фото + RU'},
        {'SKU': 'CEACW7E00', 'Модель': 'HW100-BD14397PGU1', 'Бренд': 'Haier', 'Категория': 'Стиральная machine', 'Торговая сеть': 'Зигзаг', 'Статус': '🟢 Полный комплект'},
        {'SKU': 'CF067CE03', 'Модель': 'HD90-A3939', 'Бренд': 'Haier', 'Категория': 'Сушильная машина', 'Торговая сеть': 'Elite Electronics', 'Статус': '🔵 Только документы'},
        {'SKU': 'CE0J9VE01', 'Модель': 'BR 410B8-S', 'Бренд': 'Candy', 'Категория': 'Стиральная машина', 'Торговая сеть': 'Бомба', 'Статус': '🔵 Только документы'},
        {'SKU': 'CEADU2E00', 'Модель': 'EY 27SB7-S', 'Бренд': 'Candy', 'Категория': 'Стиральная машина', 'Торговая сеть': 'ЮгКонтракт', 'Статус': '🔵 Только документы'}
    ]
    return pd.DataFrame(mock_products)

def parse_excel_file_cell(cell_text):
    """Очищает скопированный текст из Excel от тегов контента"""
    lines = cell_text.strip().split('\n')
    return [re.sub(r'^\[.*?\]\s*', '', line).strip() for line in lines if line.strip()]

# Инициализация баз данных
files_registry = load_google_files_registry()
products_df = load_products_data()

# --- ИНТЕРФЕЙС STREAMLIT ---
st.title("🧭 Поисковый навигатор Haier / Candy")
st.markdown("Инструмент быстрой генерации ссылок на Google Диск на основе данных навигатора WAR ROOM.")

# Блок фильтров
row1_col1, row1_col2 = st.columns([1, 2])

with row1_col1:
    networks = ["-- Все торговые сети --", "Elite Electronics", "Зигзаг", "Бомба", "ЮгКонтракт"]
    selected_network = st.selectbox("1. Выбери торговую сеть клиента:", networks)

with row1_col2:
    search_query = st.text_area(
        "2. Введи SKU/модель или вставь скопированную ячейку файлов из Excel:",
        placeholder="Пример ячейки:\n[📄 PDF·RU] Презентация_929A.pdf\n[📸 JPG · 12 шт] HW70-B12929",
        height=100
    )

if st.button("Найти материалы", type="primary"):
    st.markdown("---")
    st.subheader("📋 Результаты обработки запроса")
    
    # Фильтруем ассортимент по сети, если она выбрана
    df_filtered = products_df.copy()
    if selected_network != "-- Все торговые сети --":
        df_filtered = df_filtered[df_filtered['Торговая сеть'].str.contains(selected_network, case=False, na=False)]
    
    # СЦЕНАРИЙ 1: Пользователь вставил ячейку со списком файлов из Excel (есть квадратные скобки)
    if '[' in search_query and ']' in search_query:
        st.info("💡 Обнаружена вставка ячейки структуры файлов. Генерирую прямые ссылки на Google Диск:")
        clean_file_names = parse_excel_file_cell(search_query)
        
        for name in clean_file_names:
            # Ищем ссылку в реестре Google Таблицы
            link = files_registry.get(name.lower(), None)
            
            if link:
                st.markdown(f"🔗 **[{name}]({link})** — [ Перейти к файлу на Диске ]({link})")
            else:
                st.markdown(f"❌ **{name}** — *Файл еще не зарегистрирован в таблице макроса*")
                
    # СЦЕНАРИЙ 2: Обычный поиск по модели или SKU
    else:
        if search_query:
            df_filtered = df_filtered[
                df_filtered['SKU'].str.contains(search_query, case=False, na=False) |
                df_filtered['Модель'].str.contains(search_query, case=False, na=False)
            ]
        
        if df_filtered.empty:
            st.warning("Ничего не найдено. Проверь правильность ввода SKU или модели.")
        else:
            st.dataframe(
                df_filtered, 
                column_config={
                    "SKU": "SKU товара",
                    "Модель": "Модель техники",
                    "Торговая сеть": "Торговая сеть (Клиент)",
                    "Статус": "Статус контента"
                },
                use_container_width=True,
                hide_index=True
            )
