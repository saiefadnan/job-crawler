/**
 * ============================================================================
 * Google Apps Script: Drive Link Generator & Gmail Draft Creator
 * ============================================================================
 *
 * HOW IT WORKS:
 * 1. You upload your generated CV PDFs (from your local output/ folder) into
 *    a Google Drive folder (default name: "Job_CVs").
 * 2. Run `generateDriveLinksAndSync()` in this script:
 *    - Finds each CV PDF in your Drive folder by matching the filename in `cv_path`.
 *    - Makes the PDF shareable ("Anyone with the link can view").
 *    - Automatically populates the `drive_link` column in your Google Sheet!
 *    - (Optional) For email applications, it creates a draft in your Gmail with
 *      both the direct Drive download link AND the PDF attached.
 *
 * HOW TO USE:
 * 1. Open your Google Sheet containing the imported `data/applications.csv`.
 * 2. Create a folder in your Google Drive named `Job_CVs` and drop your generated
 *    PDFs into it (or change CV_FOLDER_NAME below to your folder's name).
 * 3. In Google Sheets, click Extensions -> Apps Script.
 * 4. Paste this entire script and save (Ctrl+S).
 * 5. Run `generateDriveLinksAndSync` or `generateDriveLinksOnly`.
 */

// Name of your Google Drive folder where you store/sync your output PDFs
const CV_FOLDER_NAME = "Job_CVs";

/**
 * ============================================================================
 * ONE-CLICK AUTHORIZATION FUNCTION
 * ============================================================================
 * Run this function ONCE in the Apps Script Editor toolbar:
 * 1. Select 'authorizePermissions' in the function dropdown.
 * 2. Click 'Run' (▶️).
 * 3. Click 'Review permissions' -> Select your Google account -> 'Advanced' -> 'Go to Job Tracker (unsafe)' -> 'Allow'.
 * This grants Google Drive, Sheets, and Gmail permissions so the Webhook can upload CVs!
 */
function authorizePermissions() {
  Logger.log("1. Checking Google Sheets permission...");
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  Logger.log("   Sheet OK: " + sheet.getName());

  Logger.log("2. Checking Google Drive permission...");
  const folderIter = DriveApp.getFoldersByName(CV_FOLDER_NAME);
  if (!folderIter.hasNext()) {
    DriveApp.createFolder(CV_FOLDER_NAME);
    Logger.log("   Created Drive folder: " + CV_FOLDER_NAME);
  } else {
    Logger.log("   Found Drive folder: " + CV_FOLDER_NAME);
  }

  Logger.log("3. Checking Gmail permission...");
  const drafts = GmailApp.getDrafts();
  Logger.log("   Gmail OK (Total drafts checked: " + drafts.length + ")");

  Logger.log("ALL PERMISSIONS AUTHORIZED! You can now deploy or re-deploy the Web App as 'New version'.");
  return "All permissions authorized successfully!";
}


/**
 * Populates the `drive_link` column in the Google Sheet for all rows
 * where the CV PDF exists in the Google Drive folder.
 */
function generateDriveLinksOnly() {
  processSheet({ createDrafts: false });
}

/**
 * Generates Drive links in the sheet AND creates ready-to-send drafts in Gmail.
 */
function generateDriveLinksAndSync() {
  processSheet({ createDrafts: true });
}

/**
 * Backwards-compatible alias for existing triggers.
 */
function createGmailDraftsFromSheet() {
  generateDriveLinksAndSync();
}


/**
 * Main processor for Drive link generation and Gmail drafting.
 */
function processSheet(options) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const data = sheet.getDataRange().getValues();

  if (data.length < 2) {
    Logger.log("No data found in sheet.");
    return;
  }

  const headers = data[0].map(h => String(h).trim().toLowerCase());
  
  // Locate columns dynamically
  const cvPathCol = headers.indexOf("cv_path");
  let driveCol = headers.indexOf("drive_link");
  const emailCol = headers.indexOf("email_to");
  const subjectCol = headers.indexOf("email_subject");
  const bodyCol = headers.indexOf("email_body");
  const statusCol = headers.indexOf("apply_status");
  const methodCol = headers.indexOf("apply_method");
  const companyCol = headers.indexOf("company");

  // If drive_link column does not exist yet, add it automatically
  if (driveCol === -1) {
    driveCol = headers.length;
    sheet.getRange(1, driveCol + 1).setValue("drive_link");
  }

  // Find Google Drive CV Folder
  const folderIter = DriveApp.getFoldersByName(CV_FOLDER_NAME);
  let cvFolder = null;
  if (folderIter.hasNext()) {
    cvFolder = folderIter.next();
  } else {
    Logger.log(`Folder '${CV_FOLDER_NAME}' not found in Google Drive. You can create it to auto-generate links.`);
  }

  let linksGenerated = 0;
  let draftsCreated = 0;

  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const rawCvPath = String(row[cvPathCol] || "");
    let existingDriveLink = String(row[driveCol] || "").trim();
    const applyMethod = String(row[methodCol] || "").toLowerCase().trim();
    const currentStatus = String(row[statusCol] || "").trim();
    const recipient = String(row[emailCol] || "").trim();
    const subject = String(row[subjectCol] || "").trim();
    let body = String(row[bodyCol] || "").trim();
    const company = row[companyCol] || "Company";

    let cvFile = null;

    // 1. Generate Google Drive link if missing and folder exists
    if (cvFolder && rawCvPath) {
      // Extract filename (e.g., "ExtraHop_SoftwareEngineerIIIAIML_CV.pdf")
      const fileName = rawCvPath.replace(/\\/g, "/").split("/").pop();

      const files = cvFolder.getFilesByName(fileName);
      if (files.hasNext()) {
        cvFile = files.next();
        if (!existingDriveLink) {
          // Set to anyone with link can view
          cvFile.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
          existingDriveLink = cvFile.getUrl();
          sheet.getRange(i + 1, driveCol + 1).setValue(existingDriveLink);
          linksGenerated++;
          Logger.log(`[Drive Link Generated] ${company} -> ${existingDriveLink}`);
        }
      }
    }

    // 2. Create Gmail draft if enabled and row is ready
    if (options.createDrafts && applyMethod === "email" && currentStatus === "EMAIL_DRAFTED" && recipient) {
      try {
        // Embed the Drive link into the email body if available
        if (existingDriveLink && !body.includes(existingDriveLink)) {
          body = body.replace(
            "I have attached my tailored CV for your review.",
            `You can view/download my tailored CV directly here:\n${existingDriveLink}\n\n(I have also attached the PDF for your convenience).`
          );
        }

        const draftOptions = {};
        if (cvFile) {
          draftOptions.attachments = [cvFile.getAs(MimeType.PDF)];
        }

        GmailApp.createDraft(recipient, subject, body, draftOptions);
        
        sheet.getRange(i + 1, statusCol + 1).setValue("GMAIL_DRAFT_CREATED");
        draftsCreated++;
        Logger.log(`[Draft Created] ${company} -> ${recipient}`);
      } catch (err) {
        Logger.log(`[Error] Failed row ${i + 1} (${company}): ${err.message}`);
      }
    }
  }

  const msg = `Completed!\n- Drive links populated: ${linksGenerated}\n- Gmail drafts created: ${draftsCreated}`;
  Logger.log(msg);

  try {
    SpreadsheetApp.getUi().alert(msg);
  } catch (e) {
    // Silent on time-driven triggers
  }
}


/**
 * ============================================================================
 * WEBHOOK ENDPOINT: doPost(e)
 * ============================================================================
 * Allows Python to send applications directly to Google Sheets in real-time.
 *
 * HOW TO GET WEBHOOK URL:
 * 1. At the top right of Apps Script, click: "Deploy" -> "New deployment".
 * 2. Click the gear icon next to "Select type" and choose "Web app".
 * 3. Set:
 *    - Description: "Job Tracker Webhook"
 *    - Execute as: "Me"
 *    - Who has access: "Anyone"  <-- Required so Python can POST without OAuth
 * 4. Click "Deploy".
 * 5. Copy the "Web app URL" (looks like: https://script.google.com/macros/s/.../exec).
 * 6. Paste it into your local `.env` file as:
 *    GOOGLE_SHEET_WEBHOOK_URL=https://script.google.com/macros/s/.../exec
 */
function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return ContentService.createTextOutput(
        JSON.stringify({ status: "error", message: "No post data received" })
      ).setMimeType(ContentService.MimeType.JSON);
    }

    const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    const contents = JSON.parse(e.postData.contents);

    // 0. Cloud Cleanup Action (Google Drive CVs, Google Sheet rows, Gmail drafts)
    if (contents.action === "cleanup") {
      const ttlDays = contents.ttl_days || 30;
      const result = run30DayCleanup(ttlDays);
      return ContentService.createTextOutput(
        JSON.stringify({
          status: "success",
          message: "30-Day cloud cleanup completed",
          purged: result
        })
      ).setMimeType(ContentService.MimeType.JSON);
    }

    let driveLink = contents.drive_link || "";
    let cvFile = null;
    let driveError = null;
    let gmailError = null;

    // 1. If base64 PDF is transmitted (e.g. from GitHub Actions runner or local CLI), save to Google Drive
    if (contents.pdf_base64 && contents.cv_filename) {
      try {
        const folderIter = DriveApp.getFoldersByName(CV_FOLDER_NAME);
        const folder = folderIter.hasNext() ? folderIter.next() : DriveApp.createFolder(CV_FOLDER_NAME);
        const blob = Utilities.newBlob(
          Utilities.base64Decode(contents.pdf_base64),
          "application/pdf",
          contents.cv_filename
        );
        cvFile = folder.createFile(blob);
        cvFile.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
        driveLink = cvFile.getUrl();
        contents.drive_link = driveLink;
      } catch (driveErr) {
        driveError = driveErr.message;
        Logger.log("[Drive Upload Warning] " + driveErr.message);
      }
    }

    // 2. If email application, automatically create ready-to-send draft in Gmail with attached PDF
    if (contents.apply_method === "email" && contents.email_to) {
      try {
        let emailBody = contents.email_body || "";
        if (driveLink && !emailBody.includes(driveLink)) {
          emailBody = emailBody.replace(
            "I have attached my tailored CV for your review.",
            "You can view/download my tailored CV directly here:\n" + driveLink + "\n\n(I have also attached the PDF for your convenience)."
          );
          contents.email_body = emailBody;
        }

        const draftOptions = {};
        if (cvFile) {
          draftOptions.attachments = [cvFile.getAs(MimeType.PDF)];
        }

        GmailApp.createDraft(
          contents.email_to,
          contents.email_subject || "Job Application",
          emailBody,
          draftOptions
        );
        contents.apply_status = "GMAIL_DRAFT_CREATED";
      } catch (gmailErr) {
        gmailError = gmailErr.message;
        Logger.log("[Gmail Draft Warning] " + gmailErr.message);
      }
    }

    const defaultHeaders = [
      "date", "job_id", "company", "title", "score", "status",
      "url", "matched_keywords", "cv_path", "drive_link",
      "apply_method", "email_to", "email_subject", "email_body",
      "draft_path", "apply_status"
    ];

    // If sheet has no rows, add standard headers first
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(defaultHeaders);
    }

    // Read current header row to map fields dynamically
    const headerRow = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
    const currentHeaders = headerRow.map(h => String(h).trim().toLowerCase());

    const newRow = currentHeaders.map(header => {
      const val = contents[header];
      if (val === undefined || val === null) return "";
      if (Array.isArray(val)) return val.join(", ");
      return val;
    });

    sheet.appendRow(newRow);

    return ContentService.createTextOutput(
      JSON.stringify({ 
        status: "success", 
        message: "Row appended successfully", 
        drive_link: driveLink,
        drive_error: driveError,
        gmail_error: gmailError,
        apply_status: contents.apply_status 
      })
    ).setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(
      JSON.stringify({ status: "error", message: err.message })
    ).setMimeType(ContentService.MimeType.JSON);
  }
}


/**
 * ============================================================================
 * 30-DAY RETENTION CLEANUP FOR CLOUD STORAGE
 * ============================================================================
 */

/**
 * Prunes files in Google Drive folder 'Job_CVs' older than ttlDays.
 */
function pruneExpiredDriveFiles(ttlDays = 30) {
  const cutoffDate = new Date(Date.now() - ttlDays * 24 * 60 * 60 * 1000);
  const folderIter = DriveApp.getFoldersByName(CV_FOLDER_NAME);
  let purgedCount = 0;

  if (folderIter.hasNext()) {
    const folder = folderIter.next();
    const files = folder.getFiles();
    while (files.hasNext()) {
      const file = files.next();
      if (file.getDateCreated() < cutoffDate) {
        file.setTrashed(true);
        purgedCount++;
      }
    }
  }
  Logger.log(`[Drive Prune] Purged ${purgedCount} files older than ${ttlDays} days from '${CV_FOLDER_NAME}'.`);
  return purgedCount;
}

/**
 * Prunes rows in the active Google Sheet where the 'date' column is older than ttlDays.
 */
function pruneExpiredSheetRows(ttlDays = 30) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const data = sheet.getDataRange().getValues();
  if (data.length <= 1) return 0;

  const headers = data[0].map(h => String(h).trim().toLowerCase());
  const dateCol = headers.indexOf("date");
  if (dateCol === -1) return 0;

  const cutoffDate = new Date(Date.now() - ttlDays * 24 * 60 * 60 * 1000);
  let purgedRows = 0;

  // Iterate backwards from bottom to row 2
  for (let i = data.length - 1; i >= 1; i--) {
    const rawDate = data[i][dateCol];
    if (!rawDate) continue;
    const rowDate = new Date(rawDate);
    if (!isNaN(rowDate.getTime()) && rowDate < cutoffDate) {
      sheet.deleteRow(i + 1);
      purgedRows++;
    }
  }
  Logger.log(`[Sheet Prune] Purged ${purgedRows} rows older than ${ttlDays} days.`);
  return purgedRows;
}

/**
 * Prunes job application drafts in Gmail older than ttlDays.
 */
function pruneExpiredGmailDrafts(ttlDays = 30) {
  const cutoffDate = new Date(Date.now() - ttlDays * 24 * 60 * 60 * 1000);
  const drafts = GmailApp.getDrafts();
  let purgedDrafts = 0;

  for (let i = 0; i < drafts.length; i++) {
    const draft = drafts[i];
    const msg = draft.getMessage();
    const subject = (msg.getSubject() || "").toLowerCase();
    // Target job application drafts
    if (subject.includes("application:") || subject.includes("job application")) {
      if (msg.getDate() < cutoffDate) {
        draft.deleteDraft();
        purgedDrafts++;
      }
    }
  }
  Logger.log(`[Gmail Draft Prune] Purged ${purgedDrafts} drafts older than ${ttlDays} days.`);
  return purgedDrafts;
}

/**
 * Master 30-Day Cloud Cleanup function.
 * Can be run manually from Apps Script or triggered automatically via webhook / time-driven trigger.
 */
function run30DayCleanup(ttlDays = 30) {
  const drivePurged = pruneExpiredDriveFiles(ttlDays);
  const sheetPurged = pruneExpiredSheetRows(ttlDays);
  const draftsPurged = pruneExpiredGmailDrafts(ttlDays);
  const summary = {
    drive: drivePurged,
    sheet: sheetPurged,
    gmail: draftsPurged
  };
  Logger.log(`[30-Day Cloud Cleanup] Drive: -${drivePurged}, Sheet: -${sheetPurged}, Gmail: -${draftsPurged}`);
  return summary;
}
