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

### Week 10：關鍵字檢索與語意檢索
- 使用 jieba 斷詞、TF-IDF、BM25 與句向量，實作校規 chunks 檢索。
- 以 cosine 相似度比較句向量，並人工評估 10 個校規問題的前三名結果：TF-IDF 與 BM25 的 hit@3 為 0.5，dense 的 hit@3 為 1.0；關鍵字方法命中所有精確措辭題，dense 也命中所有口語改寫題。
- 完成 3 題反思與 2 個自訂問題，輸出檢索比較結果。
- 新增／更新檔案：`notebooks/10_vector_similarity.ipynb`、`week10_retrieval_comparison.json`、`AI_USAGE.md`、`README.md`。

#### 下課前檢查清單
- [x] 所有 7 個 `TODO` 檢查都通過，notebook 保留輸出並存檔
- [x] 反思 3 題已作答
- [x] `week10_retrieval_comparison.json` 已產生
- [x] `requirements.txt` 和 `.gitignore` 已更新（由 `10_0_setup.ipynb` 自動完成）
- [x] `AI_USAGE.md` 已新增 Week 10 段落：今天哪些地方問了 AI、AI 的回答哪裡正確或錯誤、你如何查證
- [x] `README.md` 已更新：新增 Week 10 的說明（本週完成的內容、新增的檔案）
- [x] 本次修改已 commit & push，並打開 GitHub 網頁確認檔案已經上傳

### Week 12: Chunking Strategies & Vector Index
- [x] **依結構切塊**：執行 `src/rechunk_v2.py`，產生 `data/processed_v2/`（策略 C、D）
- [x] **固定長度 + 重疊**：完成 `fixed_chunks`（策略 B）
- [x] **向量索引**：儲存 `data/embeddings/week12_v2_emb.npy`（策略 D，第 14 週使用）
- [x] **自動評估**：完成 `hit_at_k`、`topk_chars`，比較 4 種策略

  | 策略 | hit@3 | hit@5 |
  |---|---:|---:|
  | A 第8週 | 0.75 | 0.79 |
  | B 固定長度+重疊 (500/100) | 0.67 | 0.79 |
  | C 依條文(無標題) | 0.67 | 0.83 |
  | D 依條文+標題 | 0.71 | 0.88 |

- [x] **自己出題**：2 題，看 A、B、D 的排名
- [x] **選做比較**：將 B 的 `size/overlap` 從 `500/100` 改為 `300/50`

  | B 設定 | chunks | hit@3 | hit@5 | 前 5 名總字數最大值 |
  |---|---:|---:|---:|---:|
  | 500/100 | 808 | 0.67 | 0.79 | 2,500 |
  | 300/50 | 1,292 | 0.67 | 0.75 | 1,500 |

  hit@3 相同，較小 chunks 的 hit@5 低 0.04，但前 5 名最大字數少 1,000 字。

#### 下課前檢查清單
- [x] 所有 notebook 檢查通過，並保留執行輸出
- [x] 反思 3 題已作答
- [x] `week12_retrieval_eval.json` 已產生
- [x] `src/rechunk_v2.py` 在專案裡
- [x] `.gitignore` 已更新
- [x] README 與 AI_USAGE 已更新
- [x] (選做) 修改 B 設定並比較完成
- [x] commit & push，並打開 GitHub 確認