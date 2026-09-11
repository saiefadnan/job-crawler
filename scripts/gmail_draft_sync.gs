/**
 * ============================================================================
 * Google Apps Script: Automated Gmail Draft Creator from Job Search Tracker
 * ============================================================================
 *
 * HOW TO USE:
 * 1. Open your Google Sheet where data/applications.csv is imported or synced.
 * 2. Go to: Extensions -> Apps Script.
 * 3. Delete any boilerplate code and paste this entire script.
 * 4. Click "Save" (Ctrl+S) and then click "Run" -> select `createGmailDraftsFromSheet`.
 * 5. Grant the one-time Gmail permissions when prompted by Google.
 * 6. Check your Gmail "Drafts" folder! Each email draft will be waiting for your
 *    final review before sending.
 *
 * OPTIONAL AUTOMATION:
 * - In Apps Script, click "Triggers" (alarm clock icon on left sidebar).
 * - Click "+ Add Trigger".
 * - Choose `createGmailDraftsFromSheet`, event source "Time-driven", run daily or hourly.
 */

function createGmailDraftsFromSheet() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const data = sheet.getDataRange().getValues();

  if (data.length < 2) {
    Logger.log("No data found in sheet (need at least headers and 1 row).");
    return;
  }

  const headers = data[0].map(h => String(h).trim().toLowerCase());
  
  // Locate required columns dynamically
  const emailCol = headers.indexOf("email_to");
  const subjectCol = headers.indexOf("email_subject");
  const bodyCol = headers.indexOf("email_body");
  const statusCol = headers.indexOf("apply_status");
  const methodCol = headers.indexOf("apply_method");
  const companyCol = headers.indexOf("company");

  if (emailCol === -1 || subjectCol === -1 || bodyCol === -1 || statusCol === -1) {
    SpreadsheetApp.getUi().alert(
      "Missing required columns! Ensure 'email_to', 'email_subject', 'email_body', and 'apply_status' exist."
    );
    return;
  }

  let createdCount = 0;

  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const applyMethod = String(row[methodCol] || "").toLowerCase().trim();
    const currentStatus = String(row[statusCol] || "").trim();
    const recipient = String(row[emailCol] || "").trim();
    const subject = String(row[subjectCol] || "").trim();
    const body = String(row[bodyCol] || "").trim();
    const company = row[companyCol] || "Company";

    // Only process email applications that are currently in EMAIL_DRAFTED state
    if (applyMethod === "email" && currentStatus === "EMAIL_DRAFTED" && recipient) {
      try {
        // Create draft directly in Gmail Drafts folder
        GmailApp.createDraft(recipient, subject, body);
        
        // Update status in sheet to prevent duplicate drafts
        sheet.getRange(i + 1, statusCol + 1).setValue("GMAIL_DRAFT_CREATED");
        createdCount++;
        Logger.log(`[Created Draft] ${company} -> ${recipient}`);
      } catch (err) {
        Logger.log(`[Error] Failed for row ${i + 1} (${company}): ${err.message}`);
      }
    }
  }

  Logger.log(`Finished processing. Created ${createdCount} new Gmail draft(s).`);
  
  // Show UI alert if running interactively
  try {
    SpreadsheetApp.getUi().alert(`Done! Successfully created ${createdCount} draft(s) in your Gmail.`);
  } catch (e) {
    // Silent if running on an automated time trigger
  }
}
