/**
 * MailOrbit Google Apps Script Email Relay
 * 
 * Secure, per-user email relay deployed as a Google Apps Script Web App.
 * Relays cold emails via the user's personal Gmail account using MailApp.
 * 
 * Security & Reliability Features:
 * 1. Token in Script Properties: Stored in PropertiesService ("RELAY_AUTH_TOKEN"), NEVER hardcoded.
 * 2. Quota Guard: Checks MailApp.getRemainingDailyQuota() and returns QUOTA_EXCEEDED if 0.
 * 3. Idempotency: Uses CacheService to reject duplicate idempotency keys (persists up to 6 hours).
 * 4. Recipient Validation: Strict email regex check before sending.
 * 5. Attachment Size Guard: Enforces Google's 25 MB total attachment limit.
 * 6. Zero Secret Logging: Never logs auth tokens or request credentials to Logger/Cloud Logs.
 */

// Basic email validation regex conforming to RFC 5322 standard
const EMAIL_REGEX = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/;
const MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024; // 25 MB limit for Gmail

function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return jsonResponse({
        success: false,
        error: "MISSING_PAYLOAD",
        message: "No POST body received."
      }, 400);
    }

    let payload;
    try {
      payload = JSON.parse(e.postData.contents);
    } catch (parseErr) {
      return jsonResponse({
        success: false,
        error: "INVALID_JSON",
        message: "Could not parse request body as JSON."
      }, 400);
    }

    // 1. Verify Secret Auth Token from Script Properties
    const scriptProps = PropertiesService.getScriptProperties();
    const configuredToken = scriptProps.getProperty("RELAY_AUTH_TOKEN");

    if (!configuredToken) {
      return jsonResponse({
        success: false,
        error: "NOT_CONFIGURED",
        message: "Relay auth token is not configured in Script Properties."
      }, 500);
    }

    const incomingToken = payload.token;
    if (!incomingToken || incomingToken !== configuredToken) {
      return jsonResponse({
        success: false,
        error: "UNAUTHORIZED",
        message: "Invalid or missing relay authentication token."
      }, 401);
    }

    // 2. Daily Quota Guard
    const remainingQuota = MailApp.getRemainingDailyQuota();
    if (remainingQuota <= 0) {
      return jsonResponse({
        success: false,
        error: "QUOTA_EXCEEDED",
        remaining_quota: 0,
        message: "Gmail daily sending quota has been reached for today."
      }, 429);
    }

    // 3. Idempotency Check
    const idempotencyKey = payload.idempotency_key;
    if (idempotencyKey) {
      const cache = CacheService.getScriptCache();
      const existing = cache.get("idem_" + idempotencyKey);
      if (existing) {
        return jsonResponse({
          success: false,
          error: "DUPLICATE_REQUEST",
          idempotency_key: idempotencyKey,
          message: "Request with this idempotency key was already processed."
        }, 409);
      }
    }

    // 4. Validate Recipient Email Address
    const recipient = (payload.to || "").trim();
    if (!recipient || !EMAIL_REGEX.test(recipient)) {
      return jsonResponse({
        success: false,
        error: "INVALID_EMAIL",
        message: "Invalid recipient email address: " + recipient
      }, 400);
    }

    // 5. Validate and Prepare Mail Options
    const subject = payload.subject || "(No Subject)";
    const htmlBody = payload.html_body || payload.body || "";
    const plainBody = payload.plain_body || stripHtml(htmlBody);

    const mailOptions = {
      to: recipient,
      subject: subject,
      body: plainBody,
      htmlBody: htmlBody
    };

    if (payload.reply_to) {
      mailOptions.replyTo = payload.reply_to;
    }
    if (payload.cc) {
      mailOptions.cc = payload.cc;
    }
    if (payload.bcc) {
      mailOptions.bcc = payload.bcc;
    }

    // 6. Handle Attachments (with 25 MB Guard)
    let totalAttachmentBytes = 0;
    if (payload.attachments && Array.isArray(payload.attachments)) {
      const blobs = [];
      for (let i = 0; i < payload.attachments.length; i++) {
        const att = payload.attachments[i];
        if (!att.filename || !att.base64_content) {
          continue;
        }

        const decodedBytes = Utilities.base64Decode(att.base64_content);
        totalAttachmentBytes += decodedBytes.length;

        if (totalAttachmentBytes > MAX_ATTACHMENT_BYTES) {
          return jsonResponse({
            success: false,
            error: "ATTACHMENT_TOO_LARGE",
            message: "Total attachments exceed the 25 MB limit (" + totalAttachmentBytes + " bytes)."
          }, 413);
        }

        const blob = Utilities.newBlob(decodedBytes, att.mime_type || "application/octet-stream", att.filename);
        blobs.push(blob);
      }
      if (blobs.length > 0) {
        mailOptions.attachments = blobs;
      }
    }

    // 7. Dispatch Mail
    MailApp.sendEmail(mailOptions);

    // 8. Cache Idempotency Key (cached for 6 hours = 21600 seconds)
    if (idempotencyKey) {
      try {
        CacheService.getScriptCache().put("idem_" + idempotencyKey, "SENT", 21600);
      } catch (cacheErr) {
        // Cache error shouldn't abort a successful send
      }
    }

    return jsonResponse({
      success: true,
      message: "Email dispatched successfully via Gmail MailApp",
      recipient: recipient,
      remaining_quota: MailApp.getRemainingDailyQuota()
    }, 200);

  } catch (err) {
    return jsonResponse({
      success: false,
      error: "SEND_FAILED",
      message: err.toString()
    }, 500);
  }
}

function doGet(e) {
  // Simple health check endpoint for relay verification
  const remainingQuota = MailApp.getRemainingDailyQuota();
  return jsonResponse({
    status: "ok",
    service: "MailOrbit Google Apps Script Relay",
    version: "1.0.0",
    remaining_quota: remainingQuota
  }, 200);
}

function jsonResponse(data, statusCode) {
  const output = ContentService.createTextOutput(JSON.stringify(data));
  output.setMimeType(ContentService.MimeType.JSON);
  return output;
}

function stripHtml(html) {
  return html.replace(/<[^>]*>?/gm, " ").replace(/\s+/g, " ").trim();
}

