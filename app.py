import streamlit as st
import pandas as pd
import requests
import io
import re
import urllib.parse

st.set_page_config(
    page_title="Haier Material Hub",
    layout="wide",
    page_icon="☁️",
)

# ─── SECRETS ───────────────────────────────────────────────
try:
    API_KEY   = st.secrets["GOOGLE_API_KEY"]
    SHEET_ID  = st.secrets["SHEET_ID"]
    FOLDER_ID = st.secrets["DRIVE_FOLDER_ID"]
except Exception:
    API_KEY   = ""
    SHEET_ID  = "122GipihFaGUp2AFyhy39_EKRVY5Rbuzg-TGGK8s5wro"
    FOLDER_ID = "1QxSQfKd2UJVIpiinTGo5P2ahf30RJkis"

# GID нового листа «Реестр файлов» из URL
REGISTRY_GID  = "1937244690"
MIN_QUERY     = 2
MAX_DISPLAY   = 60

# ─── STYLES ────────────────────────────────────────────────
st.markdown("""
<style>
.card {
    border: 1px solid #E2E8F0;
    border-left: 4px solid #1565C0;
    border-radius: 6px;
    padding: 10px 14px;
    margin-bottom: 7px;
    background: #F8FAFC;
}
.card.photo  { border-left-color: #2E7D32; background: #F1F8E9; }
.card.video  { border-left-color: #6A1B9A; background: #F3E5F5; }
.card.pptx   { border-left-color: #E65100; background: #FFF3E0; }
.card.zip    { border-left-color: #546E7A; background: #ECEFF1; }
.card.drive  { border-left-color: #F57F17; background: #FFFDE7; }
.fname  { font-weight: 600; font-size: 0.92rem; color: #1A237E; word-break: break-word; }
.fpath  { font-size: 0.76rem; color: #78909C; margin-top: 3px; }
.flinks { margin-top: 7px; font-size: 0.82rem; }
.flinks a { color: #1565C0; margin-right: 12px; text-decoration: none; }
.flinks a:hover { text-decoration: underline; }
.tag { display:inline-block; padding:1px 6px; border-radius:10px; font-size:0.70rem;
       font-weight:600; margin-right:5px; margin-bottom:4px; }
.tag-pdf  { background:#E3F2FD; color:#0D47A1; }
.tag-pptx { background:#FFF3E0; color:#E65100; }
.tag-photo{ background:#E8F5E9; color:#1B5E20; }
.tag-video{ background:#F3E5F5; color:#4A148C; }
.tag-xlsx { background:#E0F2F1; color:#004D40; }
.tag-zip  { background:#ECEFF1; color:#37474F; }
.tag-ru   { background:#E8F5E9; color:#2E7D32; }
.tag-en   { background:#FBE9E7; color:#BF360C; }
.tag-src  { background:#FFF9C4; color:#F57F17; }
.divider-sec { font-size:0.78rem; font-weight:600; color:#546E7A; letter-spacing:0.05em;
               border-bottom:2px solid #E0E0E0; padding-bottom:4px; margin:18px 0 10px; }
</style>
""", unsafe_allow_html=True)

# ─── LOAD REGISTRY ─────────────────────────────────────────
@st.cache_data(ttl=300)
def load_registry() -> pd.DataFrame | None:
    """Читает лист 'Реестр файлов' (gid=1937244690) из Sheets."""
    url = (f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
           f"/export?format=csv&gid={REGISTRY_GID}")
    try:
        resp = requests.get(url, timeout=12)
        if resp.status_code == 200:
            df = pd.read_csv(io.StringIO(resp.text), header=0)
            df.columns = [c.strip() for c in df.columns]
            return df
    except Exception as e:
        st.warning(f"Реестр недоступен: {e}")
    return None

# ─── HELPERS ───────────────────────────────────────────────
EXT_META = {
    "pdf":  ("📄", "pdf",   "PDF документ"),
    "pptx": ("📊", "pptx",  "Презентация PPTX"),
    "ppt":  ("📊", "pptx",  "Презентация PPT"),
    "xlsx": ("📊", "xlsx",  "Таблица Excel"),
    "xls":  ("📊", "xlsx",  "Таблица Excel"),
    "jpg":  ("🖼️", "photo", "Фото JPG"),
    "jpeg": ("🖼️", "photo", "Фото JPEG"),
    "png":  ("🖼️", "photo", "Фото PNG"),
    "mp4":  ("🎬", "video", "Видео MP4"),
    "mov":  ("🎬", "video", "Видео MOV"),
    "zip":  ("📦", "zip",   "Архив ZIP"),
    "rar":  ("📦", "zip",   "Архив RAR"),
    "ai":   ("🎨", "zip",   "Исходник AI"),
}

TAG_CSS = {
    "pdf": "tag-pdf", "pptx": "tag-pptx", "photo": "tag-photo",
    "video": "tag-video", "xlsx": "tag-xlsx", "zip": "tag-zip",
}

def ext_info(ext: str):
    return EXT_META.get(ext.lower().strip("."), ("📁", "doc", ext.upper()))

def is_ru(name: str, path: str = "") -> bool:
    t = (name + path).upper()
    return any(x in t for x in ["RU", "·RU", "РUSS", "РУССК", "ПРЕЗЕНТАЦ",
                                  "ONEPAGE", "ОДИН ЛИСТ", "СЕРИЯ", "КБТ"])

def drive_search_url(query: str) -> str:
    return f"https://drive.google.com/drive/search?q={urllib.parse.quote(query)}"

def normalize(q: str) -> str:
    # Убираем иконки и теги из скопированного текста ячейки Excel
    q = re.sub(r'[📄📸🎬📊📦🎨·]', '', q)
    q = re.sub(r'\b(RU|EN|PDF|PPTX|XLSX|фото товара)\b', '', q, flags=re.I)
    q = re.sub(r'^\s*[-—*·]+\s*', '', q)  # убираем leading дефисы
    q = re.sub(r'\s+', ' ', q).strip()
    return q

# ─── SEARCH ────────────────────────────────────────────────
def search_registry(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """Поиск по имени файла и пути (оба столбца)."""
    name_col = next((c for c in df.columns if 'имя' in c.lower() or 'name' in c.lower()), None)
    path_col = next((c for c in df.columns if 'путь' in c.lower() or 'path' in c.lower()), None)

    masks = []
    if name_col:
        masks.append(df[name_col].astype(str).str.contains(re.escape(query), case=False, na=False))
    if path_col:
        masks.append(df[path_col].astype(str).str.contains(re.escape(query), case=False, na=False))

    if not masks:
        return pd.DataFrame()

    combined = masks[0]
    for m in masks[1:]:
        combined = combined | m
    return df[combined].copy()

@st.cache_data(ttl=120)
def search_drive_api(query: str) -> list[dict]:
    if not API_KEY or not FOLDER_ID:
        return []
    safe_q = query.replace("'", "\\'")
    params = {
        "q": f"name contains '{safe_q}' and trashed = false",
        "key": API_KEY,
        "fields": "files(id,name,mimeType,webViewLink)",
        "pageSize": 20,
        "supportsAllDrives": True,
        "includeItemsFromAllDrives": True,
    }
    try:
        r = requests.get("https://www.googleapis.com/drive/v3/files",
                         params=params, timeout=10)
        if r.status_code == 200:
            return r.json().get("files", [])
    except Exception:
        pass
    return []

# ─── RENDER ────────────────────────────────────────────────
def render_row(row: pd.Series, query: str, source_label: str = "Реестр"):
    cols = {c.lower(): c for c in row.index}
    name  = str(row.get(cols.get('имя файла',''), row.get(cols.get('name',''), ''))).strip()
    ext   = str(row.get(cols.get('расширение',''), row.get(cols.get('ext',''), ''))).strip().lstrip('.')
    path  = str(row.get(cols.get('путь (относительный)',''),
                        row.get(cols.get('путь',''), ''))).strip()
    parent= str(row.get(cols.get('родительская папка',''), '')).strip()
    size  = row.get(cols.get('размер (мб)',''), None)

    if name in ('', 'nan', 'None'): return

    icon, css, label = ext_info(ext)
    tag_cls = TAG_CSS.get(css, "tag-pdf")
    lang    = "RU" if is_ru(name, path) else "EN"
    lang_cls= "tag-ru" if lang == "RU" else "tag-en"
    src_cls = "tag-src"

    size_str = f"{float(size):.1f} МБ" if size and str(size) not in ('nan','None') else ""

    # Ссылка: поиск на Drive по имени файла — самый надёжный способ
    drive_url = drive_search_url(name)

    path_display = parent if parent and parent not in ('nan','None') else path
    if path_display in ('nan', 'None'): path_display = "—"

    st.markdown(f"""
    <div class="card {css}">
      <div>
        <span class="tag {tag_cls}">{icon} {label}</span>
        <span class="tag {lang_cls}">{lang}</span>
        <span class="tag {src_cls}">{source_label}</span>
        {"<span style='font-size:0.72rem;color:#90A4AE;'>" + size_str + "</span>" if size_str else ""}
      </div>
      <div class="fname">{name}</div>
      <div class="fpath">📂 {path_display}</div>
      <div class="flinks">
        <a href="{drive_url}" target="_blank">🔍 Найти на Drive</a>
      </div>
    </div>
    """, unsafe_allow_html=True)

def render_drive_file(f: dict):
    name    = f.get("name", "—")
    file_id = f.get("id", "")
    mime    = f.get("mimeType", "")
    web     = f.get("webViewLink", "")

    ext = ""
    if "presentation" in mime: ext = "pptx"
    elif "pdf" in mime:        ext = "pdf"
    elif "video" in mime:      ext = "mp4"
    elif "image" in mime:      ext = "jpg"
    elif "spreadsheet" in mime:ext = "xlsx"

    icon, css, label = ext_info(ext) if ext else ("📁", "doc", "Файл")
    view_url = web or (f"https://drive.google.com/file/d/{file_id}/view" if file_id else "")
    dl_url   = f"https://drive.google.com/uc?export=download&id={file_id}" if file_id and "google-apps" not in mime else ""

    links = f'<a href="{view_url}" target="_blank">👁 Открыть</a>' if view_url else ""
    if dl_url:
        links += f' <a href="{dl_url}" target="_blank">📥 Скачать</a>'

    st.markdown(f"""
    <div class="card drive">
      <span class="tag {TAG_CSS.get(css,'tag-pdf')}">{icon} {label}</span>
      <span class="tag tag-src">Drive API</span>
      <div class="fname">{name}</div>
      <div class="fpath">📂 Google Drive (прямой поиск)</div>
      <div class="flinks">{links}</div>
    </div>
    """, unsafe_allow_html=True)

# ─── UI ────────────────────────────────────────────────────
st.title("☁️ Haier Material Hub")
st.caption("Вставь название модели, серии или имя файла из ячейки Excel — Hub найдёт материал на Drive")
st.markdown("---")

df = load_registry()
reg_ok = df is not None and not df.empty

raw_input = st.text_input(
    "🔍 Поиск",
    placeholder="HW90-BP14929A  /  X11  /  929  /  BD14397  /  WM Catalog  /  Horizon ...",
    help="Можно вставить содержимое ячейки «Материалы» из Excel — иконки и теги уберутся автоматически"
).strip()

with st.expander("⚙️ Опции"):
    use_drive_api = st.checkbox("Также искать через Drive API", value=True,
                                help="Медленнее, но ловит файлы которых нет в реестре")
    show_photos   = st.checkbox("Показывать фото (JPG/PNG)", value=False,
                                help="Фото обычно не нужны при поиске документов")

st.markdown("---")

if not raw_input:
    if reg_ok:
        total = len(df)
        ext_counts = df['Расширение'].value_counts() if 'Расширение' in df.columns else {}
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Файлов в реестре", f"{total:,}".replace(',',' '))
        c2.metric("Презентаций PDF/PPTX", int(ext_counts.get('pdf',0)) + int(ext_counts.get('pptx',0)))
        c3.metric("Фото JPG/PNG", int(ext_counts.get('jpg',0)) + int(ext_counts.get('png',0)))
        c4.metric("Видео", int(ext_counts.get('mp4',0)) + int(ext_counts.get('mov',0)))
    st.info("👆 Введи запрос выше. Примеры: **HW90-BP14929A**, **X11**, **929**, **Horizon**, **WM Catalog**")
    st.stop()

if len(raw_input) < MIN_QUERY:
    st.warning(f"Введи минимум {MIN_QUERY} символа")
    st.stop()

# Нормализуем — убираем иконки и теги если скопировано из Excel
query = normalize(raw_input)
if not query:
    st.warning("Не удалось извлечь запрос из введённого текста")
    st.stop()

if query != raw_input:
    st.caption(f"Поиск по: **{query}**")

# ─── ВЫПОЛНЯЕМ ПОИСК ───────────────────────────────────────
reg_results  = pd.DataFrame()
drive_results= []

with st.spinner(f"Ищем «{query}»..."):
    if reg_ok:
        reg_results = search_registry(df, query)
        # Фото убираем если не нужны
        if not show_photos and 'Расширение' in reg_results.columns:
            reg_results = reg_results[~reg_results['Расширение'].str.lower().isin(['jpg','jpeg','png','gif'])]

    if use_drive_api and API_KEY:
        drive_results = search_drive_api(query)
        if not show_photos:
            drive_results = [f for f in drive_results
                            if not any(x in f.get('mimeType','') for x in ['image','jpeg','png'])]

total_found = len(reg_results) + len(drive_results)

# ─── ВЫВОД ─────────────────────────────────────────────────
if total_found == 0:
    st.error(f"❌ Ничего не найдено по «{query}»")
    drive_url = drive_search_url(query)
    st.markdown(f"💡 Попробуй [поиск напрямую на Google Drive]({drive_url})")
    st.markdown("""
**Советы:**
- Числовой код модели: `14929`, `14397`, `12929`
- Серия: `X11`, `929A`, `929`, `Horizon`
- Тип файла: `Catalog`, `OnePage`, `Training`, `Презентация`
""")
    st.stop()

st.success(f"Найдено: **{total_found}** файлов"
           + (f" (реестр: {len(reg_results)}" if len(reg_results) else "")
           + (f", Drive API: {len(drive_results)}" if drive_results else "")
           + (")" if len(reg_results) or drive_results else ""))

# Блок 1: реестр
if not reg_results.empty:
    # Группируем по типу: сначала документы, потом видео, потом фото
    def sort_key(ext):
        e = str(ext).lower()
        if e in ('pdf','pptx','ppt'): return 0
        if e in ('xlsx','xls'):       return 1
        if e in ('mp4','mov'):        return 2
        return 3

    if 'Расширение' in reg_results.columns:
        reg_results = reg_results.copy()
        reg_results['_sort'] = reg_results['Расширение'].apply(sort_key)
        reg_results = reg_results.sort_values('_sort').drop(columns=['_sort'])

    st.markdown(f'<div class="divider-sec">📋 ИЗ РЕЕСТРА — {len(reg_results)} файлов</div>',
                unsafe_allow_html=True)

    shown = 0
    for _, row in reg_results.iterrows():
        if shown >= MAX_DISPLAY:
            st.caption(f"... ещё {len(reg_results)-shown} файлов. Уточни запрос.")
            break
        render_row(row, query)
        shown += 1

# Блок 2: Drive API (дедупликация по имени)
if drive_results:
    reg_names = set()
    if not reg_results.empty:
        name_col = next((c for c in reg_results.columns
                         if 'имя' in c.lower() or 'name' in c.lower()), None)
        if name_col:
            reg_names = set(reg_results[name_col].astype(str).str.lower())

    new_files = [f for f in drive_results
                 if f.get('name','').lower() not in reg_names]

    if new_files:
        st.markdown(f'<div class="divider-sec">☁️ DRIVE API — {len(new_files)} дополнительно</div>',
                    unsafe_allow_html=True)
        for f in new_files[:20]:
            render_drive_file(f)
    else:
        st.caption("Drive API не нашёл ничего сверх реестра.")

# Всегда показываем ссылку на Drive поиск
st.markdown("---")
st.markdown(f"🔗 [Открыть поиск в Google Drive →]({drive_search_url(query)})",
            unsafe_allow_html=False)
