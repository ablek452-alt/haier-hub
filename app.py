import streamlit as st
import pandas as pd
import requests
import io
import re
import urllib.parse

st.set_page_config(page_title="Haier Material Hub", layout="wide", page_icon="☁️")

# ─── SECRETS ───────────────────────────────────────────────
try:
    API_KEY   = st.secrets["GOOGLE_API_KEY"]
    SHEET_ID  = st.secrets["SHEET_ID"]
    FOLDER_ID = st.secrets["DRIVE_FOLDER_ID"]
except Exception:
    API_KEY   = ""
    SHEET_ID  = "122GipihFaGUp2AFyhy39_EKRVY5Rbuzg-TGGK8s5wro"
    FOLDER_ID = "1QxSQfKd2UJVIpiinTGo5P2ahf30RJkis"

REGISTRY_GID = "1937244690"
SHEET_NAME   = "Реестр файлов"
MIN_QUERY    = 2
MAX_DISPLAY  = 60

# ─── STYLES ────────────────────────────────────────────────
st.markdown("""
<style>
.card {
    border:1px solid #E2E8F0; border-left:4px solid #1565C0;
    border-radius:6px; padding:10px 14px; margin-bottom:7px; background:#F8FAFC;
}
.card.photo { border-left-color:#2E7D32; background:#F1F8E9; }
.card.video { border-left-color:#6A1B9A; background:#F3E5F5; }
.card.pptx  { border-left-color:#E65100; background:#FFF3E0; }
.card.zip   { border-left-color:#546E7A; background:#ECEFF1; }
.fname { font-weight:600; font-size:0.92rem; color:#1A237E; word-break:break-word; }
.fpath { font-size:0.76rem; color:#78909C; margin-top:3px; }
.flinks { margin-top:7px; font-size:0.82rem; }
.flinks a { color:#1565C0; margin-right:12px; text-decoration:none; }
.tag { display:inline-block; padding:1px 6px; border-radius:10px;
       font-size:0.70rem; font-weight:600; margin-right:5px; margin-bottom:4px; }
.tag-pdf  { background:#E3F2FD; color:#0D47A1; }
.tag-pptx { background:#FFF3E0; color:#E65100; }
.tag-photo{ background:#E8F5E9; color:#1B5E20; }
.tag-video{ background:#F3E5F5; color:#4A148C; }
.tag-xlsx { background:#E0F2F1; color:#004D40; }
.tag-zip  { background:#ECEFF1; color:#37474F; }
.tag-ru   { background:#E8F5E9; color:#2E7D32; }
.tag-en   { background:#FBE9E7; color:#BF360C; }
.divider-sec { font-size:0.78rem; font-weight:600; color:#546E7A;
               border-bottom:2px solid #E0E0E0; padding-bottom:4px; margin:18px 0 10px; }
</style>
""", unsafe_allow_html=True)

# ─── LOAD REGISTRY ─────────────────────────────────────────
@st.cache_data(ttl=300)
def load_registry() -> pd.DataFrame | None:
    """
    Пробует 3 способа загрузить реестр по убыванию надёжности.
    """
    errors = []

    # Способ 1: export по GID (работает если таблица публичная)
    url1 = (f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
            f"/export?format=csv&gid={REGISTRY_GID}")
    try:
        r = requests.get(url1, timeout=15, allow_redirects=True)
        if r.status_code == 200 and len(r.text) > 100:
            df = pd.read_csv(io.StringIO(r.text), header=0)
            if len(df) > 10:
                return df
        errors.append(f"Way1 GID export: {r.status_code}")
    except Exception as e:
        errors.append(f"Way1 exception: {e}")

    # Способ 2: gviz/tq по имени листа
    sheet_enc = urllib.parse.quote(SHEET_NAME)
    url2 = (f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
            f"/gviz/tq?tqx=out:csv&sheet={sheet_enc}")
    try:
        r = requests.get(url2, timeout=15)
        if r.status_code == 200 and len(r.text) > 100:
            df = pd.read_csv(io.StringIO(r.text), header=0)
            if len(df) > 10:
                return df
        errors.append(f"Way2 gviz: {r.status_code}")
    except Exception as e:
        errors.append(f"Way2 exception: {e}")

    # Способ 3: gviz с API key
    if API_KEY:
        url3 = (f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
                f"/gviz/tq?tqx=out:csv&sheet={sheet_enc}&key={API_KEY}")
        try:
            r = requests.get(url3, timeout=15)
            if r.status_code == 200 and len(r.text) > 100:
                df = pd.read_csv(io.StringIO(r.text), header=0)
                if len(df) > 10:
                    return df
            errors.append(f"Way3 gviz+key: {r.status_code}")
        except Exception as e:
            errors.append(f"Way3 exception: {e}")

    st.error(f"Не удалось загрузить реестр. Попытки: {' | '.join(errors)}")
    return None

# ─── HELPERS ───────────────────────────────────────────────
EXT_META = {
    "pdf":  ("📄", "pdf",   "PDF"),
    "pptx": ("📊", "pptx",  "PPTX"),
    "ppt":  ("📊", "pptx",  "PPT"),
    "xlsx": ("📊", "xlsx",  "Excel"),
    "xls":  ("📊", "xlsx",  "Excel"),
    "jpg":  ("🖼️", "photo", "Фото"),
    "jpeg": ("🖼️", "photo", "Фото"),
    "png":  ("🖼️", "photo", "PNG"),
    "mp4":  ("🎬", "video", "Видео"),
    "mov":  ("🎬", "video", "Видео"),
    "zip":  ("📦", "zip",   "Архив"),
    "rar":  ("📦", "zip",   "Архив"),
    "ai":   ("🎨", "zip",   "AI-исходник"),
}
TAG_CSS = {
    "pdf":"tag-pdf","pptx":"tag-pptx","photo":"tag-photo",
    "video":"tag-video","xlsx":"tag-xlsx","zip":"tag-zip",
}

def ext_info(ext):
    return EXT_META.get(str(ext).lower().strip("."), ("📁", "pdf", str(ext).upper()))

def is_ru(name, path=""):
    t = (str(name) + str(path)).upper()
    return any(x in t for x in ["·RU", "РУССК", "ПРЕЗЕНТАЦ", "ONEPAGE",
                                  "ОДИН ЛИСТ", "КБТ", "СЕРИЯ"])

def normalize_query(q):
    # Убираем иконки и типы которые могут быть в скопированной ячейке Excel
    q = re.sub(r'[📄📸🎬📊📦🎨·🖼️]', '', q)
    q = re.sub(r'\b(RU|EN|PDF|PPTX|XLSX|фото\s+товара|Фото\s+товара)\b', '', q, flags=re.I)
    q = re.sub(r'^\s*[-—*·\s]+', '', q)
    q = re.sub(r'\s+', ' ', q).strip()
    return q

def search_df(df, query):
    """Поиск по имени файла И по пути — оба столбца."""
    cols_to_search = []
    for col in df.columns:
        cl = col.lower()
        if any(x in cl for x in ['имя', 'name', 'путь', 'path', 'папка', 'folder']):
            cols_to_search.append(col)

    if not cols_to_search:
        cols_to_search = list(df.columns)

    pattern = re.escape(query)
    mask = pd.Series([False] * len(df), index=df.index)
    for col in cols_to_search:
        mask |= df[col].astype(str).str.contains(pattern, case=False, na=False)
    return df[mask].copy()

# ─── RENDER ────────────────────────────────────────────────
def render_card(row):
    cols = {c.lower(): c for c in row.index}

    name   = str(row.get(cols.get('имя файла',
             cols.get('name', list(cols.values())[1] if len(cols)>1 else '')), '')).strip()
    ext    = str(row.get(cols.get('расширение', cols.get('ext','')), '')).strip().lstrip('.')
    path   = str(row.get(cols.get('путь (относительный)', cols.get('path','')), '')).strip()
    parent = str(row.get(cols.get('родительская папка', cols.get('folder','')), '')).strip()
    size   = row.get(cols.get('размер (мб)', cols.get('size','')), None)

    if not name or name in ('nan','None',''): return

    icon, css, label = ext_info(ext)
    tag_cls  = TAG_CSS.get(css, 'tag-pdf')
    lang     = "RU" if is_ru(name, path) else "EN"
    lang_cls = "tag-ru" if lang == "RU" else "tag-en"

    # Размер
    try:
        # Sheets иногда пишет "2,83" с запятой
        sz = float(str(size).replace(',','.'))
        size_str = f"{sz:.1f} МБ"
    except Exception:
        size_str = ""

    # Путь для отображения — берём родительскую папку или относительный путь
    display_path = parent if parent and parent not in ('nan','None','') else path
    if display_path in ('nan','None',''): display_path = "—"

    # Ссылка: Drive поиск по точному имени файла (в кавычках — точное совпадение)
    drive_search = f"https://drive.google.com/drive/search?q=%22{urllib.parse.quote(name)}%22"

    size_html = f"<span style='font-size:0.72rem;color:#90A4AE;margin-left:6px'>{size_str}</span>" if size_str else ""

    st.markdown(f"""
    <div class="card {css}">
      <div>
        <span class="tag {tag_cls}">{icon} {label}</span>
        <span class="tag {lang_cls}">{lang}</span>
        {size_html}
      </div>
      <div class="fname">{name}</div>
      <div class="fpath">📂 {display_path}</div>
    </div>
    """, unsafe_allow_html=True)

# ─── MAIN UI ───────────────────────────────────────────────
st.title("☁️ Haier Material Hub")
st.caption("Поиск по реестру материалов — вставляй название из ячейки Excel или вводи модель/серию")
st.markdown("---")

# Загрузка
df = load_registry()

# Диагностика если не загрузилось
if df is None or df.empty:
    st.error("Реестр не загружен. Проверь доступ к таблице.")
    st.markdown(f"Попробуй открыть напрямую: https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={REGISTRY_GID}")
    st.stop()

# Показываем что загрузилось (для отладки — потом можно убрать)
with st.expander(f"✅ Реестр загружен: {len(df):,} файлов | Колонки: {', '.join(df.columns.tolist())}".replace(',',' ')):
    st.dataframe(df.head(5))

# Поиск
raw = st.text_input(
    "🔍 Поиск",
    placeholder="HW90-BP14929A  /  X11  /  929  /  BD14397  /  2959  /  WM Catalog  /  Horizon ...",
).strip()

show_photos = st.checkbox("Показывать фото (JPG/PNG)", value=False)
st.markdown("---")

if not raw:
    ext_counts = df['Расширение'].value_counts() if 'Расширение' in df.columns else {}
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Файлов", f"{len(df):,}".replace(',',' '))
    c2.metric("PDF + PPTX", int(ext_counts.get('pdf',0)) + int(ext_counts.get('pptx',0)))
    c3.metric("Фото", int(ext_counts.get('jpg',0)) + int(ext_counts.get('png',0)))
    c4.metric("Видео", int(ext_counts.get('mp4',0)) + int(ext_counts.get('mov',0)))
    st.info("Введи запрос выше")
    st.stop()

query = normalize_query(raw)
if not query or len(query) < MIN_QUERY:
    st.warning(f"Введи минимум {MIN_QUERY} символа")
    st.stop()

if query != raw:
    st.caption(f"Поиск по: **{query}**")

# ─── ПОИСК И ВЫВОД ─────────────────────────────────────────
with st.spinner(f"Ищем «{query}»..."):
    results = search_df(df, query)

    if not show_photos and 'Расширение' in results.columns:
        results = results[~results['Расширение'].astype(str).str.lower().isin(
            ['jpg','jpeg','png','gif'])]

    # Сортировка: документы сначала
    if 'Расширение' in results.columns:
        order = {'pdf':0,'pptx':1,'ppt':1,'xlsx':2,'xls':2,'mp4':3,'mov':3}
        results = results.copy()
        results['_s'] = results['Расширение'].str.lower().map(order).fillna(4)
        results = results.sort_values('_s').drop(columns=['_s'])

if results.empty:
    st.error(f"❌ Ничего не найдено по «{query}»")
    st.markdown("""
**Попробуй:**
- Числовой код: `14929`, `14397`, `12929`, `2959`
- Серию: `X11`, `929A`, `929`, `Horizon`, `COMBI`
- Тип: `Catalog`, `OnePage`, `Training`, `Презентация`
""")
else:
    st.success(f"Найдено: **{len(results)}** файлов")
    st.markdown(f'<div class="divider-sec">РЕЗУЛЬТАТЫ</div>', unsafe_allow_html=True)

    shown = 0
    for _, row in results.iterrows():
        if shown >= MAX_DISPLAY:
            st.caption(f"... ещё {len(results)-shown} файлов. Уточни запрос.")
            break
        render_card(row)
        shown += 1
