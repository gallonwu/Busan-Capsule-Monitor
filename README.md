# 釜山膠囊列車 LINE 即時票況通知

監控天空膠囊（尾浦）官網以下條件：

- 日期：2026/10/12～2026/10/16
- 時段：全天
- 數量：至少 1 張
- 頻率：每 30 秒
- 通知：LINE Messaging API
- 部署：Railway Docker 常駐服務

## Railway Variables

在 Railway 專案的 **Variables** 設定：

- `LINE_CHANNEL_ACCESS_TOKEN`
- `LINE_USER_ID`
- `CHECK_INTERVAL_SECONDS`：`30`

前兩項屬於私密資料，請勿寫入程式或傳到公開對話。

## 部署

1. 將本資料夾上傳至 GitHub repository。
2. 在 Railway 建立專案並選擇 **Deploy from GitHub repo**。
3. 選取 repository，Railway 會依 `Dockerfile` 自動建置。
4. 加入上述三個 Variables。
5. 在 Logs 確認出現「監控啟動」與查詢結果。

瀏覽器會在雲端常駐。程式只在出現符合條件的票或票況內容改變時推播，避免每 30 秒傳送相同通知。雲端主機或官網偶發失敗時，程式會在下一輪自動重試。
