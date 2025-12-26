-- 問答記錄表
-- 用於記錄使用者的問答歷史，包含時間、搜尋關鍵字、IP 等資訊

CREATE TABLE IF NOT EXISTS query_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 問答內容
    question TEXT NOT NULL,                    -- 使用者問題
    answer TEXT,                               -- AI 回答
    
    -- 關聯文件
    document_ids UUID[],                       -- 查詢的文件 ID 列表
    
    -- 搜尋相關
    search_keywords TEXT[],                    -- 搜尋關鍵字
    matched_blocks JSONB,                      -- 匹配的區塊資訊（包含 block_id, document_id, filename, page, similarity）
    similarity_scores FLOAT[],                 -- 相似度分數列表
    
    -- 使用者資訊
    ip_address VARCHAR(45),                    -- 使用者 IP（支援 IPv6）
    user_agent TEXT,                           -- 瀏覽器/客戶端資訊
    
    -- 時間與效能
    query_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 查詢時間
    response_time_ms INTEGER,                  -- 回應時間（毫秒）
    
    -- 狀態
    status VARCHAR(20) DEFAULT 'success'       -- 狀態：success / error
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_query_logs_time ON query_logs(query_time DESC);
CREATE INDEX IF NOT EXISTS idx_query_logs_ip ON query_logs(ip_address);
CREATE INDEX IF NOT EXISTS idx_query_logs_document_ids ON query_logs USING GIN(document_ids);
CREATE INDEX IF NOT EXISTS idx_query_logs_status ON query_logs(status);

-- 查詢範例
-- 取得最近 50 筆問答記錄
-- SELECT * FROM query_logs ORDER BY query_time DESC LIMIT 50;

-- 查詢特定 IP 的問答記錄
-- SELECT * FROM query_logs WHERE ip_address = '192.168.1.1' ORDER BY query_time DESC;

-- 查詢特定文件的問答記錄
-- SELECT * FROM query_logs WHERE 'your-document-uuid' = ANY(document_ids) ORDER BY query_time DESC;

-- 統計最近 7 天的問答次數
-- SELECT DATE(query_time) as date, COUNT(*) as count 
-- FROM query_logs 
-- WHERE query_time >= NOW() - INTERVAL '7 days'
-- GROUP BY DATE(query_time) 
-- ORDER BY date DESC;

-- 統計各 IP 的問答次數
-- SELECT ip_address, COUNT(*) as count 
-- FROM query_logs 
-- GROUP BY ip_address 
-- ORDER BY count DESC;

