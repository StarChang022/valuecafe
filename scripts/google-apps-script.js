/**
 * ValueCafe Contact Form - Google Apps Script (GAS) 後端程式碼
 * 
 * 部署說明：
 * 1. 前往 Google Apps Script (https://script.google.com/) 或在關聯的 Google 試算表中開啟「擴充功能」>「Apps Script」。
 * 2. 將程式碼貼入 Code.gs 中。
 * 3. 點擊右上角「部署」>「管理部署作業」。
 * 4. 點選編輯圖示（鉛筆），版本選擇「新版本」，並確保存取權為「所有人（Anyone）」。
 * 5. 點擊「部署」儲存生效。
 */

function doPost(e) {
  try {
    var params = e.parameter || {};
    var name = params.name || '';
    var email = params.email || '';
    var subject = params.subject || '';
    var message = params.message || '';
    
    // 設定時區與時間格式
    var dateFormatted = Utilities.formatDate(new Date(), "Asia/Taipei", "yyyy/MM/dd HH:mm:ss");

    // 收件者信箱（請替換為您的接收信箱，例如 a03125694@gmail.com 或 valuecafecc@gmail.com）
    var recipientEmail = "a03125694@gmail.com";

    // 信件主旨
    var emailSubject = "【ValueCafe 官網新留言】 " + subject + " - " + name;

    // 信件 HTML 內文（在 Subject 與留言內文區塊之間加入 <br> 隔開）
    var htmlBody = 
      '<div style="font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Helvetica, Arial, sans-serif; font-size: 15px; color: #333; line-height: 1.6;">' +
        '<div style="font-weight: bold; font-size: 16px;">☕ ValueCafe Contact Form</div>' +
        '<hr style="border: none; border-top: 1px solid #e0e0e0; margin: 12px 0 16px 0;">' +
        '<div>' +
          '<b>Date : </b>' + dateFormatted + '<br>' +
          '<b>Name : </b>' + escapeHtml(name) + '<br>' +
          '<b>Email : </b>' + escapeHtml(email) + '<br>' +
          '<b>Subject : </b>' + escapeHtml(subject) + '<br>' +
        '</div>' +
        '<br>' + // <-- 留言內文與上方 Subject 以 <br> 隔開
        '<div style="background-color: #f8f9fa; border-left: 4px solid #333; padding: 12px 16px; margin: 0; white-space: pre-wrap; color: #222;">' +
          escapeHtml(message) +
        '</div>' +
      '</div>';

    // 寄送通知信件
    MailApp.sendEmail({
      to: recipientEmail,
      subject: emailSubject,
      htmlBody: htmlBody,
      replyTo: email
    });

    // 若有綁定 Google Sheet，也可在此記錄每一筆留言（選填）：
    /*
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    sheet.appendRow([dateFormatted, name, email, subject, message]);
    */

    return ContentService.createTextOutput(JSON.stringify({ result: 'success' }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({ result: 'error', error: error.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// 輔助函式：防止 HTML 標籤注入
function escapeHtml(text) {
  if (!text) return '';
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

