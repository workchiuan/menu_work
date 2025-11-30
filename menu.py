import streamlit as st
import pandas as pd
from datetime import datetime
import uuid
import io
import json
import os

# 設定頁面配置
st.set_page_config(page_title="多功能團購系統", layout="wide", page_icon="🍱")

# 資料儲存檔案路徑
DATA_FILE = "group_buy_data.json"

# --- 資料持久化函式 ---
def save_data():
    """儲存資料到本地 JSON 檔案"""
    try:
        data = {
            'groups': [],
            'current_menu': st.session_state.current_menu_editor.to_dict('records')
        }
        
        for group in st.session_state.groups:
            group_copy = group.copy()
            group_copy['deadline'] = group_copy['deadline'].isoformat()
            group_copy['created_at'] = group_copy['created_at'].isoformat()
            group_copy['menu'] = group_copy['menu'].to_dict('records')
            # 圖片轉換為 base64 字串 (如果有的話)
            if group_copy.get('menu_image_bytes'):
                import base64
                group_copy['menu_image_bytes'] = base64.b64encode(group_copy['menu_image_bytes']).decode('utf-8')
            data['groups'].append(group_copy)
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"儲存失敗: {e}")
        return False

def load_data():
    """從本地 JSON 檔案載入資料"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 載入團購資料
            st.session_state.groups = []
            for group_data in data.get('groups', []):
                group_data['deadline'] = datetime.fromisoformat(group_data['deadline'])
                group_data['created_at'] = datetime.fromisoformat(group_data['created_at'])
                group_data['menu'] = pd.DataFrame(group_data['menu'])
                # 圖片從 base64 還原
                if group_data.get('menu_image_bytes'):
                    import base64
                    group_data['menu_image_bytes'] = base64.b64decode(group_data['menu_image_bytes'])
                st.session_state.groups.append(group_data)
            
            # 載入當前編輯的菜單
            if data.get('current_menu'):
                st.session_state.current_menu_editor = pd.DataFrame(data['current_menu'])
            
            return True
    except Exception as e:
        st.warning(f"載入資料時發生錯誤 (可能是首次使用): {e}")
        return False

# --- 初始化 Session State ---
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.current_menu_editor = pd.DataFrame({
        "品名": ["範例:珍珠奶茶", "範例:招牌便當"],
        "價格": [50, 100]
    })
    st.session_state.groups = []
    # 程式啟動時載入資料
    load_data()

# --- 輔助函式 ---
def get_group_options():
    options = {}
    for group in st.session_state.groups:
        status = "🟢進行中" if group['deadline'] > datetime.now() else "🔴已截止"
        label = f"{status} | {group['vendor_name']} ({group['category']})"
        options[label] = group['id']
    return options

def get_group_by_id(group_id):
    for group in st.session_state.groups:
        if group['id'] == group_id:
            return group
    return None

# --- 側邊欄 ---
st.sidebar.title("🍱 團購導航")
page = st.sidebar.radio("選擇功能", ["我要開團 (團主)", "我要點餐 (團員)", "訂單管理 (統計/結算)"])

# 顯示當前資料狀態
st.sidebar.divider()
if st.session_state.groups:
    st.sidebar.success(f"✅ 目前有 {len(st.session_state.groups)} 個團購")
else:
    st.sidebar.info("尚無團購資料")

# ================= 頁面 1: 團主開團 =================
if page == "我要開團 (團主)":
    st.title("我是團主:發起新團購")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        vendor_name = st.text_input("店家名稱 (必填)", placeholder="例如:50嵐、八方雲集")
        category = st.selectbox("團購分類", ["餐點", "飲料", "其他"])
    with col2:
        description = st.text_area("說明備註", placeholder="例如:這家很快,要在11點前送單,請大家配合。")
        uploaded_image = st.file_uploader("上傳原始菜單圖片 (供點餐者參考)", type=["png", "jpg", "jpeg"], key="menu_image_uploader")

    st.subheader("設定收單時間")
    c1, c2 = st.columns(2)
    with c1:
        d = st.date_input("收單日期", datetime.now())
    with c2:
        t = st.time_input("收單時間", datetime.now())
    
    deadline_dt = datetime.combine(d, t)

    st.subheader("菜單設定 (手動輸入 或 Excel 匯入)")
    
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
        final_menu_df = st.session_state.current_menu_editor.dropna(subset=['品名', '價格']).reset_index(drop=True)
        
        if not vendor_name:
            st.error("❌ 請輸入店家名稱!")
        elif final_menu_df.empty:
            st.error("❌ 菜單為空!請輸入至少一個品項。")
        elif deadline_dt <= datetime.now():
            st.error(f"⛔ 收單時間 ({deadline_dt.strftime('%Y-%m-%d %H:%M')}) 不能早於目前時間!請重新設定。")
        else:
            image_bytes = uploaded_image.getvalue() if uploaded_image else None
            
            new_group = {
                "id": str(uuid.uuid4()),
                "vendor_name": vendor_name,
                "category": category,
                "description": description,
                "deadline": deadline_dt,
                "menu": final_menu_df,
                "orders": [],
                "created_at": datetime.now(),
                "menu_image_bytes": image_bytes
            }
            st.session_state.groups.append(new_group)
            
            # 儲存資料
            if save_data():
                st.balloons()
                st.success(f"✅ 成功開團!店家:{vendor_name},收單時間:{deadline_dt.strftime('%Y-%m-%d %H:%M')}")
                st.info("💾 資料已自動儲存,重新整理也不會遺失!")
                st.session_state.current_menu_editor = pd.DataFrame({"品名": [], "價格": []})
            else:
                st.warning("⚠️ 團購已建立,但儲存時發生問題")

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
            st.caption(f"📅 截止時間:{group['deadline'].strftime('%Y-%m-%d %H:%M')} | 類別:{group['category']}")
            if group['description']:
                st.info(f"📢 團主備註:{group['description']}")

            if group.get('menu_image_bytes'):
                with st.expander("🖼️ 點此查看原始菜單圖片 (參考用)", expanded=False):
                    image_buffer = io.BytesIO(group['menu_image_bytes'])
                    st.image(image_buffer, caption=f"{group['vendor_name']} 原始菜單", use_column_width='auto')

            time_left = group['deadline'] - datetime.now()
            if time_left.total_seconds() <= 0:
                st.error("⛔ 這團已經截止收單囉!")
            else:
                time_str = str(time_left).split('.')[0]
                st.success(f"🟢 開放點餐中 (剩餘 {time_str})")

                with st.form(key=f"form_{group['id']}"):
                    # 使用者姓名
                    user_name = st.text_input("您的姓名 (必填)")
                    
                    # 餐點選擇
                    menu_options = [f"{row['品名']} (${row['價格']})" for index, row in group['menu'].iterrows()]
                    
                    selected_item_str = st.selectbox(
                        "選擇餐點 (可輸入關鍵字搜尋)", 
                        ["(請選擇)"] + menu_options,
                        key=f"menu_select_{group['id']}"
                    )
                    if selected_item_str == "(請選擇)":
                        selected_item_str = None

                    # 飲料客製化選項
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

                    # 數量和備註
                    col_q1, col_q2 = st.columns(2)
                    with col_q1:
                        quantity = st.number_input("數量", min_value=1, value=1, key=f"qty_{group['id']}")
                    with col_q2:
                        note = st.text_input("其他備註 (例如:加珍珠)", key=f"note_{group['id']}")

                    submit = st.form_submit_button("送出訂單")

                    if submit:
                        if not user_name:
                            st.error("❌ 請輸入姓名!")
                        elif not selected_item_str:
                            st.error("❌ 請選擇一項餐點!")
                        elif group['category'] == "飲料" and (sugar_choice == "(請選擇)" or ice_choice == "(請選擇)"):
                            st.error("❌ 飲料類別請務必選擇「甜度」與「冰塊」!")
                        else:
                            try:
                                item_name = selected_item_str.rsplit(" ($", 1)[0]
                                item_price = int(selected_item_str.rsplit(" ($", 1)[1].replace(")", ""))
                                
                                final_note = note
                                if group['category'] == "飲料":
                                    bev_note = f"{sugar_choice}/{ice_choice}"
                                    final_note = f"{bev_note}, {note}" if note else bev_note

                                order_entry = {
                                    "姓名": user_name,
                                    "品項": item_name,
                                    "單價": item_price,
                                    "數量": quantity,
                                    "總價": item_price * quantity,
                                    "備註": final_note,
                                    "下單時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                }
                                
                                group['orders'].append(order_entry)
                                
                                # 儲存資料
                                if save_data():
                                    st.success(f"✅ {user_name},您的「{item_name}」已訂購成功!")
                                    st.info("💾 訂單已自動儲存")
                                else:
                                    st.warning("⚠️ 訂單已加入,但儲存時發生問題")
                            except Exception as e:
                                st.error(f"系統錯誤:{e}")

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
            st.subheader(f"店家:{group['vendor_name']}")
            
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

# 顯示儲存狀態 (開發用,可刪除)
with st.sidebar.expander("🔧 系統資訊", expanded=False):
    if os.path.exists(DATA_FILE):
        file_size = os.path.getsize(DATA_FILE)
        st.caption(f"資料檔案: {DATA_FILE}")
        st.caption(f"檔案大小: {file_size} bytes")
        st.caption(f"最後修改: {datetime.fromtimestamp(os.path.getmtime(DATA_FILE)).strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        st.caption("尚未建立資料檔案")
