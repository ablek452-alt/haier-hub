import streamlit as st
import json
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build

st.set_page_config(page_title="Haier WarRoom Navigator", page_icon="🧭", layout="centered")

# ==================== НАСТРОЙКИ GOOGLE ДИСКА ====================
# ID твоей папки на Google Диске
ROOT_FOLDER_ID = '1goxyDYuBE54147xUjCJjgPDJW-qJ3ad5'
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
# ================================================================

# Подключаем секреты напрямую через настройки Streamlit
def get_drive_service():
    try:
        # Берем данные ключа из секретов самого Streamlit
        creds_dict = json.loads(st.secrets["textkey"])
        creds = service_account.Credentials.from_service_account_file_dict(creds_dict, scopes=SCOPES)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"Ошибка авторизации Google: {e}")
        return None

# Функция быстрого поиска прямо на Google Диске без всяких таблиц
def search_files_on_drive(query_text):
    service = get_drive_service()
    if not service:
        return []
        
    files_found = []
    try:
        # Ищем файлы внутри папки, у которых в имени есть наш запрос (например, 14979 или 2959)
        # и которые не находятся в корзине
        q = f"name contains '{query_text}' and trashed = false"
        results = service.files().list(
            q=q,
            fields="files(name, webViewLink)",
            pageSize=50
        ).execute()
        items = results.get('files', [])
        
        for item in items:
            files_found.append({
                'name': item['name'],
                'link': item['webViewLink']
            })
    except Exception as e:
        st.error(f"Ошибка поиска на Диске: {e}")
        
    return files_found

def parse_excel_cell(cell_text):
    """Очищает вставку из Excel от тегов контента"""
    lines = cell_text.strip().split('\n')
    return [re.sub(r'^\[.*?\]\s*', '', line).strip() for line in lines if line.strip()]

st.title("🧭 Поиск файлов в Google Drive")
st.markdown("Вставь ячейку из Excel или просто напиши номер модели / любые цифры.")

# Одно универсальное поле ввода
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
        
        # СЦЕНАРИЙ 1: Вставили структуру со скобками из Excel
        if '[' in search_query and ']' in search_query:
            clean_names = parse_excel_cell(search_query)
            for name in clean_names:
                results = search_files_on_drive(name)
                if results:
                    st.success(f"🔗 **[{name}]({results[0]['link']})**")
                else:
                    st.error(f"❌ **{name}** — *Файл не найден на Google Диске*")
                    
        # СЦЕНАРИЙ 2: Тот самый первый сквозной поиск по цифрам модели (14979, 2959)
        else:
            with st.spinner("Ищу на Google Диске..."):
                results = search_files_on_drive(search_query.strip())
                
            if results:
                for file_item in results:
                    st.success(f"🔗 **[{file_item['name']}]({file_item['link']})**")
            else:
                st.warning(f"По запросу '{search_query}' на Google Диске ничего не найдено.")
