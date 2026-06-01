-- ============================================================
-- Supabase 資料庫建表 SQL
-- 請在 Supabase Dashboard → SQL Editor 中執行此腳本
-- ============================================================

-- 1. 店家表
CREATE TABLE IF NOT EXISTS vendors (
    id          TEXT PRIMARY KEY,
    vendor_name TEXT NOT NULL DEFAULT '',
    category    TEXT NOT NULL DEFAULT '餐點',
    description TEXT DEFAULT '',
    menu        JSONB DEFAULT '[]'::jsonb,
    menu_image_b64 TEXT,  -- base64 編碼的圖片
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

-- 2. 團購表
CREATE TABLE IF NOT EXISTS groups (
    id          TEXT PRIMARY KEY,
    vendor_name TEXT NOT NULL DEFAULT '',
    category    TEXT NOT NULL DEFAULT '餐點',
    description TEXT DEFAULT '',
    deadline    TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now(),
    menu        JSONB DEFAULT '[]'::jsonb,
    menu_image_b64 TEXT,
    updated_at  TIMESTAMPTZ DEFAULT now()
);

-- 3. 訂單表（關聯到團購）
CREATE TABLE IF NOT EXISTS orders (
    id          TEXT PRIMARY KEY,
    group_id    TEXT NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_name   TEXT NOT NULL DEFAULT '',
    item_name   TEXT NOT NULL DEFAULT '',
    unit_price  NUMERIC(10,2) NOT NULL DEFAULT 0,
    quantity    INTEGER NOT NULL DEFAULT 1,
    total_price NUMERIC(10,2) NOT NULL DEFAULT 0,
    note        TEXT DEFAULT '',
    ordered_at  TEXT DEFAULT '',
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- 建立索引加速查詢
CREATE INDEX IF NOT EXISTS idx_orders_group_id ON orders(group_id);
CREATE INDEX IF NOT EXISTS idx_groups_deadline ON groups(deadline);

-- 啟用 Row Level Security（RLS）但允許所有操作（適合團隊內部使用）
-- 如果你需要更嚴格的權限控制，可以自行修改 policy
ALTER TABLE vendors ENABLE ROW LEVEL SECURITY;
ALTER TABLE groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

-- 允許 anon key 存取所有資料（適合內部團購系統）
DROP POLICY IF EXISTS "允許所有人讀寫 vendors" ON vendors;
CREATE POLICY "允許所有人讀寫 vendors"
    ON vendors FOR ALL
    USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "允許所有人讀寫 groups" ON groups;
CREATE POLICY "允許所有人讀寫 groups"
    ON groups FOR ALL
    USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "允許所有人讀寫 orders" ON orders;
CREATE POLICY "允許所有人讀寫 orders"
    ON orders FOR ALL
    USING (true) WITH CHECK (true);

-- 自動更新 updated_at 欄位的觸發器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER vendors_updated_at
    BEFORE UPDATE ON vendors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER groups_updated_at
    BEFORE UPDATE ON groups
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
