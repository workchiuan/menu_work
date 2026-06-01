import streamlit as st
import pandas as pd
from datetime import datetime
import uuid
import io
import re
import base64
from db import (
    db_save_vendor, db_load_vendors, db_delete_vendor,
    db_save_group, db_load_groups,
    db_save_order,
)

# 設定頁面配置
st.set_page_config(page_title="多功能團購系統", layout="wide", page_icon="🍱")

MENU_COLUMNS = ["品名", "價格"]
CATEGORY_OPTIONS = ["餐點", "飲料", "其他"]


def create_empty_menu_df():
    return pd.DataFrame(columns=MENU_COLUMNS)


def is_group_active(group):
    return group['deadline'] > datetime.now()


def normalize_text(value):
    if value is None:
        return ""
    return str(value).strip()


def normalize_vendor_name(name):
    return normalize_text(name).casefold()


def format_price(value):
    price = float(value)
    return str(int(price)) if price.is_integer() else f"{price:g}"


@st.cache_data
def build_menu_template_excel():
    output = io.BytesIO()

    template_df = pd.DataFrame(
        [
            {"品名": "範例:珍珠奶茶", "價格": 50},
            {"品名": "範例:招牌便當", "價格": 100},
        ]
    )
    note_df = pd.DataFrame(
        {
            "欄位": ["品名", "價格"],
            "說明": ["請填寫餐點或飲料名稱", "請填寫數字價格，不要加 $ 符號"],
        }
    )

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        template_df.to_excel(writer, index=False, sheet_name="菜單範本")
        note_df.to_excel(writer, index=False, sheet_name="填寫說明")

    output.seek(0)
    return output.getvalue()


def sanitize_menu_dataframe(menu_data):
    df = pd.DataFrame(menu_data).copy()

    for column in MENU_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA

    df = df[MENU_COLUMNS]
    df["品名"] = df["品名"].astype("string").fillna("").str.strip()
    df["價格"] = pd.to_numeric(df["價格"], errors="coerce")
    df = df[(df["品名"] != "") & df["價格"].notna()].copy()

    if df.empty:
        return create_empty_menu_df()

    df["價格"] = df["價格"].apply(lambda price: int(price) if float(price).is_integer() else float(price))
    return df.reset_index(drop=True)


def vendor_matches_query(vendor, query):
    keywords = [part.casefold() for part in normalize_text(query).split() if part.strip()]
    if not keywords:
        return True

    menu_items = []
    if "品名" in vendor["menu"].columns:
        menu_items = vendor["menu"]["品名"].astype(str).tolist()

    haystack_parts = [
        vendor.get("vendor_name", ""),
        vendor.get("category", ""),
        vendor.get("description", ""),
        *menu_items,
    ]
    haystack = " ".join(normalize_text(part) for part in haystack_parts).casefold()
    return all(keyword in haystack for keyword in keywords)

# --- 資料持久化函式（Supabase 雲端） ---
def save_vendor_to_cloud(vendor):
    """儲存單一店家到雲端資料庫"""
    return db_save_vendor(vendor)


def save_group_to_cloud(group):
    """儲存單一團購到雲端資料庫"""
    return db_save_group(group)


def save_order_to_cloud(group_id, order):
    """儲存單一訂單到雲端資料庫"""
    return db_save_order(group_id, order)


def load_data():
    """從 Supabase 雲端資料庫載入所有資料"""
    try:
        # 載入店家
        vendors_raw = db_load_vendors()
        st.session_state.vendors = []
        for v in vendors_raw:
            v['vendor_name'] = normalize_text(v.get('vendor_name'))
            v['category'] = normalize_text(v.get('category')) or CATEGORY_OPTIONS[0]
            v['description'] = normalize_text(v.get('description'))
            v['menu'] = sanitize_menu_dataframe(v.get('menu', []))
            st.session_state.vendors.append(v)

        # 載入團購（含訂單）
        groups_raw = db_load_groups()
        st.session_state.groups = []
        for g in groups_raw:
            g['vendor_name'] = normalize_text(g.get('vendor_name'))
            g['category'] = normalize_text(g.get('category')) or CATEGORY_OPTIONS[0]
            g['description'] = normalize_text(g.get('description'))
            g['menu'] = sanitize_menu_dataframe(g.get('menu', []))
            st.session_state.groups.append(g)

        return True
    except Exception as e:
        st.warning(f"載入雲端資料時發生錯誤: {e}")
        return False

# --- 初始化 Session State ---
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.current_menu_editor = pd.DataFrame({
        "品名": ["範例:珍珠奶茶", "範例:招牌便當"],
        "價格": [50, 100]
    })
    st.session_state.vendors = []
    st.session_state.groups = []
    load_data()

# --- 輔助函式 ---
def get_group_options():
    options = {}
    sorted_groups = sorted(
        st.session_state.groups,
        key=lambda group: (not is_group_active(group), group['deadline'])
    )

    for group in sorted_groups:
        status = "🟢進行中" if is_group_active(group) else "🔴已截止"
        deadline_label = group['deadline'].strftime('%Y-%m-%d %H:%M')
        base_label = f"{status} | {group['vendor_name']} ({group['category']}) | 收單 {deadline_label}"
        label = base_label
        duplicate_index = 2
        while label in options:
            label = f"{base_label} #{duplicate_index}"
            duplicate_index += 1
        options[label] = group['id']
    return options

def get_group_by_id(group_id):
    for group in st.session_state.groups:
        if group['id'] == group_id:
            return group
    return None

def find_vendor_by_name(name):
    target = normalize_vendor_name(name)
    for v in st.session_state.vendors:
        if normalize_vendor_name(v['vendor_name']) == target:
            return v
    return None

def load_vendor_into_group_form(vendor):
    """將店家資料帶入開團表單的 session_state"""
    st.session_state.current_menu_editor = vendor['menu'].copy()
    st.session_state['_grp_vendor_name'] = vendor['vendor_name']
    st.session_state['_grp_category'] = vendor['category']
    st.session_state['_grp_description'] = vendor['description']
    st.session_state['_grp_loaded_vendor_id'] = vendor['id']
    st.session_state['_grp_menu_image_bytes'] = vendor.get('menu_image_bytes')

# --- 側邊欄 ---
st.sidebar.title("🍱 團購導航")
page_options = ["店家管理", "我要開團 (團主)", "我要點餐 (團員)", "訂單管理 (統計/結算)"]

if 'current_page' not in st.session_state or st.session_state.current_page not in page_options:
    st.session_state.current_page = page_options[0]

# 支援從店家管理直接跳到開團頁，並在 rerun 後保留目前頁面
_goto = st.session_state.pop('_goto_page', None)
if _goto in page_options:
    st.session_state.current_page = _goto

page = st.sidebar.radio("選擇功能", page_options, key="current_page")

st.sidebar.divider()
st.sidebar.caption(f"🏪 已儲存店家：{len(st.session_state.vendors)} 間")
active_group_count = sum(1 for group in st.session_state.groups if is_group_active(group))
if active_group_count:
    st.sidebar.success(f"✅ 目前有 {active_group_count} 個進行中的團購")
else:
    st.sidebar.info("目前沒有進行中的團購")

# ================= 頁面 0: 店家管理 =================
if page == "店家管理":
    st.title("🏪 店家管理")
    st.markdown("在這裡新增、維護店家資料，開團時直接選用。")
    st.markdown("---")

    # --- 新增店家區塊 ---
    with st.expander("➕ 新增店家", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            new_vendor_name = st.text_input("店家名稱 (必填)", placeholder="例如:50嵐、八方雲集", key="new_vendor_name")
            new_category = st.selectbox("團購分類", CATEGORY_OPTIONS, key="new_category")
        with col2:
            new_description = st.text_area("說明備註", placeholder="例如:這家很快,要在11點前送單,請大家配合。", key="new_description")
            new_uploaded_image = st.file_uploader("上傳原始菜單圖片 (供點餐者參考)", type=["png", "jpg", "jpeg"], key="new_menu_image")

        st.markdown("**菜單設定 (手動輸入 或 Excel 匯入)**")

        template_bytes = build_menu_template_excel()
        st.download_button(
            label="下載匯入範本",
            data=template_bytes,
            file_name="menu_import_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="vendor_template_download",
            type="tertiary",
        )

        with st.expander("⬆️ 點此上傳 Excel 菜單 (上傳會覆蓋下方表格內容)", expanded=False):
            uploaded_file = st.file_uploader("選擇菜單檔案", type=["xlsx", "xls"], key="vendor_excel_uploader")
            if uploaded_file is not None:
                try:
                    df_import = pd.read_excel(uploaded_file)
                    if "品名" in df_import.columns and "價格" in df_import.columns:
                        st.session_state.current_menu_editor = df_import[["品名", "價格"]].copy()
                        st.success(f"讀取成功！共 {len(st.session_state.current_menu_editor)} 筆商品，已載入到下方表格。")
                    else:
                        st.error("Excel 格式錯誤！找不到「品名」或「價格」欄位。")
                except Exception as e:
                    st.error(f"檔案讀取失敗：{e}")

        st.info("您可以直接在下方表格新增、刪除或修改菜單內容。")
        edited_df = st.data_editor(
            st.session_state.current_menu_editor,
            num_rows="dynamic",
            use_container_width=True,
            key="vendor_menu_editor"
        )
        st.session_state.current_menu_editor = edited_df

        if st.button("💾 儲存店家", type="primary"):
            normalized_name = normalize_text(new_vendor_name)
            final_menu_df = sanitize_menu_dataframe(st.session_state.current_menu_editor)
            if not normalized_name:
                st.error("❌ 請輸入店家名稱！")
            elif final_menu_df.empty:
                st.error("❌ 菜單為空！請輸入至少一個品項。")
            elif find_vendor_by_name(normalized_name):
                st.error("❌ 已有相同名稱的店家，請直接使用既有資料或先刪除舊資料。")
            else:
                image_bytes = new_uploaded_image.getvalue() if new_uploaded_image else None
                new_vendor = {
                    "id": str(uuid.uuid4()),
                    "vendor_name": normalized_name,
                    "category": new_category,
                    "description": normalize_text(new_description),
                    "menu": final_menu_df,
                    "menu_image_bytes": image_bytes,
                }
                st.session_state.vendors.append(new_vendor)
                if save_vendor_to_cloud(new_vendor):
                    st.success(f"✅ 店家「{normalized_name}」已儲存到雲端！")
                    st.session_state.current_menu_editor = create_empty_menu_df()
                    st.rerun()
                else:
                    st.warning("⚠️ 店家已新增到本地，但雲端儲存時發生問題")

    st.markdown("---")
    st.subheader("📋 已儲存的店家")
    vendor_query = st.text_input(
        "搜尋店家",
        placeholder="可搜尋店名、分類、備註或菜單品項",
        key="vendor_search_query",
    )

    if not st.session_state.vendors:
        st.info("尚無店家資料，請先在上方新增店家。")
    else:
        filtered_vendors = [
            (i, vendor) for i, vendor in enumerate(st.session_state.vendors)
            if vendor_matches_query(vendor, vendor_query)
        ]
        st.caption(f"符合搜尋結果：{len(filtered_vendors)} / {len(st.session_state.vendors)} 間")

        if not filtered_vendors:
            st.warning("找不到符合條件的店家，請換個關鍵字試試看。")

        for i, vendor in filtered_vendors:
            with st.expander(f"🏪 {vendor['vendor_name']}  ·  {vendor['category']}", expanded=False):
                st.caption(f"說明：{vendor['description'] or '（無）'}")
                st.dataframe(vendor['menu'], use_container_width=True)
                if vendor.get('menu_image_bytes'):
                    st.image(io.BytesIO(vendor['menu_image_bytes']), caption="菜單圖片", use_container_width=True)
                btn_c1, btn_c2 = st.columns(2)
                with btn_c1:
                    if st.button(f"🚀 直接開團", key=f"quick_group_{vendor['id']}"):
                        load_vendor_into_group_form(vendor)
                        st.session_state['_goto_page'] = "我要開團 (團主)"
                        st.rerun()
                with btn_c2:
                    if st.button(f"🗑️ 刪除", key=f"del_vendor_{vendor['id']}"):
                        st.session_state.vendors.pop(i)
                        db_delete_vendor(vendor['id'])
                        st.rerun()

# ================= 頁面 1: 團主開團 =================
elif page == "我要開團 (團主)":
    st.title("我是團主:發起新團購")
    st.markdown("---")

    # 處理「詢問儲存/更新店家」的提示（開團後出現）
    if st.session_state.get('_ask_save_vendor'):
        ask = st.session_state['_ask_save_vendor']
        st.balloons()
        st.success(f"✅ 成功開團！店家：{ask['name']}，收單時間：{ask['deadline_str']}")
        st.info("💾 資料已自動儲存，重新整理也不會遺失！")
        st.divider()
        st.warning(f"📌 「{ask['name']}」不在店家清單中，是否儲存此店家資料以便下次快速開團？")
        cy, cn = st.columns(2)
        with cy:
            if st.button("✅ 是，儲存店家", key="confirm_save_vendor"):
                st.session_state.pop('_ask_save_vendor')
                if find_vendor_by_name(ask['name']):
                    st.info("ℹ️ 店家清單中已存在同名店家，已略過儲存。")
                else:
                    new_v = {
                        "id": str(uuid.uuid4()),
                        "vendor_name": normalize_text(ask['name']),
                        "category": ask['category'],
                        "description": normalize_text(ask['description']),
                        "menu": sanitize_menu_dataframe(ask['menu']),
                        "menu_image_bytes": ask['image_bytes'],
                    }
                    st.session_state.vendors.append(new_v)
                    save_vendor_to_cloud(new_v)
                    st.success("✅ 店家已儲存到雲端！")
                st.rerun()
        with cn:
            if st.button("❌ 不用，謝謝", key="skip_save_vendor"):
                st.session_state.pop('_ask_save_vendor')
                st.rerun()
        st.stop()

    elif st.session_state.get('_ask_update_vendor'):
        ask = st.session_state['_ask_update_vendor']
        st.balloons()
        st.success(f"✅ 成功開團！店家：{ask['name']}，收單時間：{ask['deadline_str']}")
        st.info("💾 資料已自動儲存，重新整理也不會遺失！")
        st.divider()
        st.warning(f"📝 您修改了「{ask['name']}」的資料，是否同步更新店家清單？")
        cy, cn = st.columns(2)
        with cy:
            if st.button("✅ 是，更新店家", key="confirm_update_vendor"):
                duplicated_vendor = next(
                    (
                        vendor for vendor in st.session_state.vendors
                        if vendor['id'] != ask['vendor_id']
                        and normalize_vendor_name(vendor['vendor_name']) == normalize_vendor_name(ask['name'])
                    ),
                    None,
                )
                if duplicated_vendor:
                    st.error("❌ 已有另一間同名店家，請先調整名稱後再同步更新。")
                else:
                    for v in st.session_state.vendors:
                        if v['id'] == ask['vendor_id']:
                            v['vendor_name'] = normalize_text(ask['name'])
                            v['category'] = ask['category']
                            v['description'] = normalize_text(ask['description'])
                            v['menu'] = sanitize_menu_dataframe(ask['menu'])
                            v['menu_image_bytes'] = ask['image_bytes']
                            save_vendor_to_cloud(v)
                            break
                    st.session_state.pop('_ask_update_vendor')
                    st.success("✅ 店家資料已更新！")
                    st.rerun()
        with cn:
            if st.button("❌ 不用，謝謝", key="skip_update_vendor"):
                st.session_state.pop('_ask_update_vendor')
                st.rerun()
        st.stop()



    # 讀取預填值（用 session_state key 讀取，帶入後持續保留）
    cat_options = CATEGORY_OPTIONS
    grp_cat = st.session_state.get('_grp_category', '餐點')
    cat_index = cat_options.index(grp_cat) if grp_cat in cat_options else 0

    col1, col2 = st.columns(2)
    with col1:
        vendor_name = st.text_input(
            "店家名稱 (必填)",
            value=st.session_state.get('_grp_vendor_name', ''),
            placeholder="例如:50嵐、八方雲集"
        )
        category = st.selectbox("團購分類", cat_options, index=cat_index)
    with col2:
        description = st.text_area(
            "說明備註",
            value=st.session_state.get('_grp_description', ''),
            placeholder="例如:這家很快,要在11點前送單,請大家配合。"
        )
        uploaded_image = st.file_uploader("上傳原始菜單圖片 (供點餐者參考)", type=["png", "jpg", "jpeg"], key="menu_image_uploader")
        existing_group_image = st.session_state.get('_grp_menu_image_bytes')
        if existing_group_image and uploaded_image is None:
            st.caption("目前沿用已儲存店家的菜單圖片。")
            st.image(io.BytesIO(existing_group_image), caption="目前使用中的菜單圖片", use_container_width=True)

    st.subheader("設定收單時間")
    c1, c2 = st.columns(2)
    with c1:
        d = st.date_input("收單日期", datetime.now())
    with c2:
        now = datetime.now()
        default_time = (now.replace(second=0, microsecond=0) + pd.Timedelta(hours=1)).strftime('%H:%M')
        t_str = st.text_input("收單時間 (HH:MM)", value=default_time, help="請輸入24小時制時間，例如 14:30")
        time_valid = re.match(r"^(?:[01]?\d|2[0-3]):[0-5]\d$", t_str)
        if not time_valid:
            st.warning("請輸入正確的時間格式 (HH:MM)")
        else:
            t = datetime.strptime(t_str, "%H:%M").time()
            deadline_dt = datetime.combine(d, t)

    st.subheader("菜單設定 (手動輸入 或 Excel 匯入)")

    template_bytes = build_menu_template_excel()
    st.download_button(
        label="下載匯入範本",
        data=template_bytes,
        file_name="menu_import_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="group_template_download",
        type="tertiary",
    )

    with st.expander("⬆️ 點此上傳 Excel 菜單 (上傳會覆蓋下方表格內容)", expanded=False):
        uploaded_file = st.file_uploader("選擇菜單檔案", type=["xlsx", "xls"], key="excel_uploader")
        if uploaded_file is not None:
            try:
                df_import = pd.read_excel(uploaded_file)
                if "品名" in df_import.columns and "價格" in df_import.columns:
                    st.session_state.current_menu_editor = df_import[["品名", "價格"]].copy()
                    st.success(f"讀取成功!共 {len(st.session_state.current_menu_editor)} 筆商品,已載入到下方表格。")
                else:
                    st.error("Excel 格式錯誤!找不到「品名」或「價格」欄位。")
            except Exception as e:
                st.error(f"檔案讀取失敗:{e}")

    st.info("您可以直接在下方表格新增、刪除或修改菜單內容。")
    edited_df = st.data_editor(
        st.session_state.current_menu_editor,
        num_rows="dynamic",
        use_container_width=True
    )
    st.session_state.current_menu_editor = edited_df

    st.markdown("---")
    if st.button("🚀 確認發起團購", type="primary"):
        normalized_vendor_name = normalize_text(vendor_name)
        final_menu_df = sanitize_menu_dataframe(st.session_state.current_menu_editor)
        if not normalized_vendor_name:
            st.error("❌ 請輸入店家名稱!")
        elif final_menu_df.empty:
            st.error("❌ 菜單為空!請輸入至少一個品項。")
        elif not time_valid:
            st.error("❌ 請先修正收單時間格式！")
        elif deadline_dt <= datetime.now():
            st.error(f"⛔ 收單時間 ({deadline_dt.strftime('%Y-%m-%d %H:%M')}) 不能早於目前時間!")
        else:
            image_bytes = uploaded_image.getvalue() if uploaded_image else st.session_state.get('_grp_menu_image_bytes')
            new_group = {
                "id": str(uuid.uuid4()), "vendor_name": normalized_vendor_name,
                "category": category, "description": normalize_text(description),
                "deadline": deadline_dt, "menu": final_menu_df,
                "orders": [], "created_at": datetime.now(),
                "menu_image_bytes": image_bytes,
            }
            st.session_state.groups.append(new_group)
            save_group_to_cloud(new_group)

            loaded_vid = st.session_state.get('_grp_loaded_vendor_id')
            deadline_str = deadline_dt.strftime('%Y-%m-%d %H:%M')

            # 清除預填 session_state
            for k in ['_grp_vendor_name', '_grp_category', '_grp_description', '_grp_loaded_vendor_id', '_grp_menu_image_bytes']:
                st.session_state.pop(k, None)
            st.session_state.current_menu_editor = create_empty_menu_df()

            ask_payload = {
                'name': normalized_vendor_name, 'category': category,
                'description': normalize_text(description), 'menu': final_menu_df,
                'image_bytes': image_bytes, 'deadline_str': deadline_str,
            }

            if loaded_vid:
                # 從已有店家帶入 → 檢查是否有異動
                src = next((v for v in st.session_state.vendors if v['id'] == loaded_vid), None)
                if src:
                    menu_changed = not final_menu_df.reset_index(drop=True).equals(
                        src['menu'].reset_index(drop=True))
                    info_changed = (
                        normalized_vendor_name != src['vendor_name']
                        or category != src['category']
                        or normalize_text(description) != src['description']
                    )
                    image_changed = image_bytes != src.get('menu_image_bytes')
                    if menu_changed or info_changed or image_changed:
                        ask_payload['vendor_id'] = loaded_vid
                        st.session_state['_ask_update_vendor'] = ask_payload
                        st.rerun()
                    else:
                        st.balloons()
                        st.success(f"✅ 成功開團！店家：{normalized_vendor_name}，收單時間：{deadline_str}")
                        st.info("💾 資料已自動儲存！")
                else:
                    st.balloons()
                    st.success(f"✅ 成功開團！店家：{normalized_vendor_name}，收單時間：{deadline_str}")
            elif not find_vendor_by_name(normalized_vendor_name):
                # 新店家（手動輸入） → 詢問是否儲存
                st.session_state['_ask_save_vendor'] = ask_payload
                st.rerun()
            else:
                st.balloons()
                st.success(f"✅ 成功開團！店家：{normalized_vendor_name}，收單時間：{deadline_str}")
                st.info("💾 資料已自動儲存！")

# ================= 頁面 2: 團員點餐 =================
elif page == "我要點餐 (團員)":
    st.title("👋 我要點餐")

    group_options = get_group_options()

    if not group_options:
        st.warning("目前沒有任何團購活動。")
    else:
        selected_label = st.selectbox("請選擇要參加的團購", list(group_options.keys()))
        selected_group_id = group_options[selected_label]
        group = get_group_by_id(selected_group_id)

        if group:
            st.markdown(f"### 🏪 {group['vendor_name']}")
            st.caption(f"📅 截止時間：{group['deadline'].strftime('%Y-%m-%d %H:%M')} | 類別：{group['category']}")
            if group['description']:
                st.info(f"📢 團主備註：{group['description']}")

            if group.get('menu_image_bytes'):
                with st.expander("🖼️ 點此查看原始菜單圖片 (參考用)", expanded=False):
                    image_buffer = io.BytesIO(group['menu_image_bytes'])
                    st.image(image_buffer, caption=f"{group['vendor_name']} 原始菜單", use_container_width=True)

            time_left = group['deadline'] - datetime.now()
            if time_left.total_seconds() <= 0:
                st.error("⛔ 這團已經截止收單囉！")
            else:
                time_str = str(time_left).split('.')[0]
                st.success(f"🟢 開放點餐中 (剩餘 {time_str})")

                with st.form(key=f"form_{group['id']}"):
                    user_name = st.text_input("您的姓名 (必填)")

                    menu_records = group['menu'].to_dict('records')
                    selected_item_index = st.selectbox(
                        "選擇餐點 (可輸入關鍵字搜尋)",
                        options=[-1] + list(range(len(menu_records))),
                        format_func=lambda idx: (
                            "(請選擇)"
                            if idx == -1
                            else f"{menu_records[idx]['品名']} (${format_price(menu_records[idx]['價格'])})"
                        ),
                        key=f"menu_select_{group['id']}"
                    )

                    sugar_choice = "(請選擇)"
                    ice_choice = "(請選擇)"

                    if group['category'] == "飲料":
                        st.markdown("**🍹 飲料客製化選項 (必填)**")
                        c_bev1, c_bev2 = st.columns(2)
                        with c_bev1:
                            sugar_opts = ["(請選擇)", "正常糖", "少糖 (7分)", "半糖 (5分)", "微糖 (3分)", "一分糖", "無糖"]
                            sugar_choice = st.selectbox("甜度", sugar_opts, key=f"sugar_{group['id']}")
                        with c_bev2:
                            ice_opts = ["(請選擇)", "正常冰", "少冰", "微冰", "去冰", "完全去冰", "溫", "熱"]
                            ice_choice = st.selectbox("冰塊", ice_opts, key=f"ice_{group['id']}")

                    col_q1, col_q2 = st.columns(2)
                    with col_q1:
                        quantity = st.number_input("數量", min_value=1, value=1, key=f"qty_{group['id']}")
                    with col_q2:
                        note = st.text_input("其他備註 (例如：加珍珠)", key=f"note_{group['id']}")

                    submit = st.form_submit_button("送出訂單")

                    if submit:
                        if not normalize_text(user_name):
                            st.error("❌ 請輸入姓名！")
                        elif selected_item_index == -1:
                            st.error("❌ 請選擇一項餐點！")
                        elif group['category'] == "飲料" and (sugar_choice == "(請選擇)" or ice_choice == "(請選擇)"):
                            st.error("❌ 飲料類別請務必選擇「甜度」與「冰塊」！")
                        else:
                            try:
                                selected_item = menu_records[selected_item_index]
                                item_name = selected_item["品名"]
                                item_price = float(selected_item["價格"])
                                item_price = int(item_price) if item_price.is_integer() else item_price
                                quantity_value = int(quantity)

                                final_note = note
                                if group['category'] == "飲料":
                                    bev_note = f"{sugar_choice}/{ice_choice}"
                                    final_note = f"{bev_note}, {note}" if note else bev_note

                                order_entry = {
                                    "姓名": normalize_text(user_name),
                                    "品項": item_name,
                                    "單價": item_price,
                                    "數量": quantity_value,
                                    "總價": item_price * quantity_value,
                                    "備註": normalize_text(final_note),
                                    "下單時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                }

                                group['orders'].append(order_entry)

                                if save_order_to_cloud(group['id'], order_entry):
                                    st.success(f"✅ {user_name}，您的「{item_name}」已訂購成功！")
                                    st.info("💾 訂單已儲存到雲端資料庫")
                                else:
                                    st.warning("⚠️ 訂單已加入本地，但雲端儲存時發生問題")
                            except Exception as e:
                                st.error(f"系統錯誤：{e}")

# ================= 頁面 3: 訂單管理 =================
elif page == "訂單管理 (統計/結算)":
    st.title("📊 訂單管理與統計")

    group_options = get_group_options()
    if not group_options:
        st.info("目前沒有資料。")
    else:
        st.markdown("### 選擇要檢視的團購")
        selected_label_admin = st.selectbox("選擇團購", list(group_options.keys()), key="admin_select")
        selected_group_id_admin = group_options[selected_label_admin]
        group = get_group_by_id(selected_group_id_admin)

        if group:
            st.divider()
            st.subheader(f"店家：{group['vendor_name']}")

            if not group['orders']:
                st.warning("尚無訂單。")
            else:
                df_orders = pd.DataFrame(group['orders'])

                with st.expander("展開詳細訂單列表", expanded=True):
                    st.dataframe(df_orders, use_container_width=True)

                total_money = df_orders["總價"].sum()
                total_qty = df_orders["數量"].sum()
                st.metric("本團總金額", f"${total_money}", delta=f"共 {total_qty} 份餐點")

                st.subheader("📝 廠商叫貨單 (合併相同品項與需求)")
                summary = df_orders.groupby(["品項", "備註"])["數量"].sum().reset_index()
                st.dataframe(summary, use_container_width=True)

                csv = df_orders.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label=f"📥 下載 [{group['vendor_name']}] 訂單 CSV",
                    data=csv,
                    file_name=f"orders_{group['vendor_name']}.csv",
                    mime='text/csv',
                )

# --- 側邊欄：系統資訊 ---
with st.sidebar.expander("🔧 系統資訊", expanded=False):
    st.caption("☁️ 資料儲存方式：Supabase 雲端 PostgreSQL")
    st.caption(f"🏪 店家數量：{len(st.session_state.vendors)} 間")
    st.caption(f"📦 團購數量：{len(st.session_state.groups)} 個")
    total_orders = sum(len(g.get('orders', [])) for g in st.session_state.groups)
    st.caption(f"📝 總訂單數：{total_orders} 筆")
    if st.button("🔄 重新載入雲端資料", key="reload_cloud"):
        load_data()
        st.rerun()
