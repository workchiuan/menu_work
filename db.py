"""
Supabase 雲端資料庫存取層
封裝所有 CRUD 操作，讓 menu.py 不需直接操作資料庫
"""
import os
import base64
import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timezone, timedelta

# 台灣時區設定 (+08:00)
TAIWAN_TZ = timezone(timedelta(hours=8))

def to_tz_aware_iso(dt: datetime) -> str:
    """將 datetime 轉換為帶有台灣時區的 ISO 字串（以便存入資料庫）"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TAIWAN_TZ)
    return dt.isoformat()

def to_local_naive(dt_str: str) -> datetime:
    """將資料庫讀出的 ISO 字串轉換為台灣本地的 naive datetime"""
    if not dt_str:
        return datetime.now()
    if dt_str.endswith("Z"):
        dt_str = dt_str[:-1] + "+00:00"
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is not None:
        # 轉換為台灣時區，然後去掉時區資訊變回 naive datetime
        dt = dt.astimezone(TAIWAN_TZ).replace(tzinfo=None)
    return dt


def _get_supabase_client() -> Client:
    """取得 Supabase 客戶端（單例模式，透過 st.cache_resource 快取）"""
    if "supabase_client" in st.session_state:
        return st.session_state.supabase_client

    # 優先從 Streamlit secrets 讀取，其次從環境變數
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")

    if not url or not key:
        st.error(
            "❌ 尚未設定 Supabase 連線資訊！\n\n"
            "請在 `.streamlit/secrets.toml` 中設定：\n"
            "```\n"
            'SUPABASE_URL = "https://xxxxx.supabase.co"\n'
            'SUPABASE_KEY = "eyJhbGci..."\n'
            "```\n"
            "或設定環境變數 `SUPABASE_URL` 和 `SUPABASE_KEY`。"
        )
        st.stop()

    client = create_client(url, key)
    st.session_state.supabase_client = client
    return client


# ==================== 店家 (vendors) ====================

def db_save_vendor(vendor: dict) -> bool:
    """儲存或更新一筆店家資料"""
    try:
        client = _get_supabase_client()
        menu_records = vendor["menu"].to_dict("records") if hasattr(vendor["menu"], "to_dict") else vendor["menu"]

        # 圖片轉 base64 字串
        image_b64 = None
        if vendor.get("menu_image_bytes"):
            raw = vendor["menu_image_bytes"]
            if isinstance(raw, bytes):
                image_b64 = base64.b64encode(raw).decode("utf-8")
            else:
                image_b64 = str(raw)

        row = {
            "id": vendor["id"],
            "vendor_name": vendor.get("vendor_name", ""),
            "category": vendor.get("category", "餐點"),
            "description": vendor.get("description", ""),
            "menu": menu_records,
            "menu_image_b64": image_b64,
        }

        client.table("vendors").upsert(row, on_conflict="id").execute()
        return True
    except Exception as e:
        st.error(f"儲存店家失敗: {e}")
        return False


def db_load_vendors() -> list:
    """載入所有店家"""
    try:
        client = _get_supabase_client()
        resp = client.table("vendors").select("*").execute()
        vendors = []
        for row in resp.data:
            image_bytes = None
            if row.get("menu_image_b64"):
                image_bytes = base64.b64decode(row["menu_image_b64"])

            vendors.append({
                "id": row["id"],
                "vendor_name": row.get("vendor_name", ""),
                "category": row.get("category", "餐點"),
                "description": row.get("description", ""),
                "menu": row.get("menu", []),  # 會在 menu.py 中由 sanitize_menu_dataframe 處理
                "menu_image_bytes": image_bytes,
            })
        return vendors
    except Exception as e:
        st.warning(f"載入店家資料時發生錯誤: {e}")
        return []


def db_delete_vendor(vendor_id: str) -> bool:
    """刪除一筆店家"""
    try:
        client = _get_supabase_client()
        client.table("vendors").delete().eq("id", vendor_id).execute()
        return True
    except Exception as e:
        st.error(f"刪除店家失敗: {e}")
        return False


# ==================== 團購 (groups) ====================

def db_save_group(group: dict) -> bool:
    """儲存或更新一筆團購"""
    try:
        client = _get_supabase_client()
        menu_records = group["menu"].to_dict("records") if hasattr(group["menu"], "to_dict") else group["menu"]

        image_b64 = None
        if group.get("menu_image_bytes"):
            raw = group["menu_image_bytes"]
            if isinstance(raw, bytes):
                image_b64 = base64.b64encode(raw).decode("utf-8")
            else:
                image_b64 = str(raw)

        row = {
            "id": group["id"],
            "vendor_name": group.get("vendor_name", ""),
            "category": group.get("category", "餐點"),
            "description": group.get("description", ""),
            "deadline": to_tz_aware_iso(group["deadline"]) if isinstance(group["deadline"], datetime) else group["deadline"],
            "created_at": to_tz_aware_iso(group["created_at"]) if isinstance(group["created_at"], datetime) else group["created_at"],
            "menu": menu_records,
            "menu_image_b64": image_b64,
        }

        client.table("groups").upsert(row, on_conflict="id").execute()
        return True
    except Exception as e:
        st.error(f"儲存團購失敗: {e}")
        return False


def db_load_groups() -> list:
    """載入所有團購（含其訂單）"""
    try:
        client = _get_supabase_client()
        resp = client.table("groups").select("*").execute()
        groups = []
        for row in resp.data:
            image_bytes = None
            if row.get("menu_image_b64"):
                image_bytes = base64.b64decode(row["menu_image_b64"])

            # 載入此團購的所有訂單
            orders_resp = client.table("orders").select("*").eq("group_id", row["id"]).execute()
            orders = []
            for o in orders_resp.data:
                orders.append({
                    "姓名": o.get("user_name", ""),
                    "品項": o.get("item_name", ""),
                    "單價": o.get("unit_price", 0),
                    "數量": o.get("quantity", 1),
                    "總價": o.get("total_price", 0),
                    "備註": o.get("note", ""),
                    "下單時間": o.get("ordered_at", ""),
                })

            groups.append({
                "id": row["id"],
                "vendor_name": row.get("vendor_name", ""),
                "category": row.get("category", "餐點"),
                "description": row.get("description", ""),
                "deadline": to_local_naive(row.get("deadline")),
                "created_at": to_local_naive(row.get("created_at")),
                "menu": row.get("menu", []),  # 會在 menu.py 中由 sanitize_menu_dataframe 處理
                "orders": orders,
                "menu_image_bytes": image_bytes,
            })
        return groups
    except Exception as e:
        st.warning(f"載入團購資料時發生錯誤: {e}")
        return []


def db_delete_group(group_id: str) -> bool:
    """刪除一筆團購（連帶訂單會由 CASCADE 自動刪除）"""
    try:
        client = _get_supabase_client()
        client.table("groups").delete().eq("id", group_id).execute()
        return True
    except Exception as e:
        st.error(f"刪除團購失敗: {e}")
        return False


# ==================== 訂單 (orders) ====================

def db_save_order(group_id: str, order: dict) -> bool:
    """儲存一筆訂單"""
    try:
        client = _get_supabase_client()
        import uuid

        row = {
            "id": str(uuid.uuid4()),
            "group_id": group_id,
            "user_name": order.get("姓名", ""),
            "item_name": order.get("品項", ""),
            "unit_price": float(order.get("單價", 0)),
            "quantity": int(order.get("數量", 1)),
            "total_price": float(order.get("總價", 0)),
            "note": order.get("備註", ""),
            "ordered_at": order.get("下單時間", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        }

        client.table("orders").insert(row).execute()
        return True
    except Exception as e:
        st.error(f"儲存訂單失敗: {e}")
        return False
