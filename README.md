# NLP 自然語言處理 (115 S1) - 課程專案

本專案為 NLP 課程開發環境與實作練習區。

---

## 開發者資訊 (Developer Info)
* **學號**：[U12627013]
* **姓名**：[林正皓]

## 硬體與環境狀態 (Environment Setup)
**PyTorch 執行環境**：<br>
PyTorch 版本：2.5.1+cu121<br>
CUDA 是否可用：True<br>
GPU 數量：1<br>
目前 GPU：NVIDIA GeForce RTX 4060 Laptop GPU<br>
CUDA 版本：12.1<br>
張量所在裝置：cuda:0<br>
GPU 測試成功

---

## 課程任務清單 (Task Checklist)

### Week 2：開發環境與專案架構初始化
請在完成下列任務後，將 `[ ]` 改為 `[x]`：
- [x] 成功建立 GitHub 帳號並 Clone 本專案至本機端。
- [x] 成功建立 `.venv` 虛擬環境，並透過 `.gitignore` 隱藏底層檔案。
- [x] 成功於虛擬環境內安裝通用套件清單 (`requirements.txt`) 與專屬硬體版本的 PyTorch。
- [x] 更新本 README 文件，填寫學號、姓名與 PyTorch 環境狀態。
- [x] 成功使用 Git 完成 `commit` 並 `push` 同步至 GitHub 雲端。

### Week 4 / 8: Data Ingestion & Topology-Aware Chunking
- [x] **環境建置與版控防護**：`requirements.txt` 已列出 `docling`、`matplotlib`；`.gitignore` 忽略原始 PDF、中間 Markdown 與處理後 JSON，並保留 `.keep` 目錄結構。
- [x] **資料擷取與合併答案已填入 Notebook**：1-A、1-B、1-C 的正則與提示詞答案已寫入。
  - [x] 1-A：重新執行目前程式，斷言通過。
  - [x] 1-B：重新執行目前程式，斷言通過。
  - [x] 1-C：重新執行目前程式，斷言通過。
- [x] **結構健全度 (Mechanical Sanity)**：批次管線已執行；Cleaned/Raw 拓撲錨定率皆為 100%，文本長度中位數為 269/205。
- [x] **語意品質 (Semantic Quality)**：Shannon Information Entropy 中位數已計算；Cleaned 5.03，Raw 4.72。
- [x] **觀測儀表板與報告**：Notebook 已保留 4 拼圖輸出，根目錄 `metrics.json` 已產生。
