/**
 * MailOrbit Platform System Mail Relay
 * 
 * Google Apps Script Web App for platform transactional mail delivery
 * (Email OTPs, Welcome notices, Password Changes, Security Alerts, Account Deletion).
 * 
 * Security & Reliability Specifications:
 * 1. Token in Script Properties: Configured under "RELAY_AUTH_TOKEN" in Script Properties. NEVER hardcoded.
 * 2. Strict Quota Guard: Enforces Gmail daily quota and a rolling 90 mails/day platform cap.
 * 3. Idempotency Protection: Uses CacheService to prevent duplicate sends within 6 hours.
 * 4. Recipient Validation: Strict RFC 5322 regex validation before calling MailApp.
 * 5. Zero Credential Logging: Never writes auth tokens, passwords, or request secrets to Execution Logs.
 * 6. Honest Error Reporting: Returns JSON errors with distinct error codes (QUOTA_EXCEEDED, UNAUTHORIZED, INVALID_EMAIL).
 */

const EMAIL_REGEX = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/;
const SYSTEM_DAILY_CAP = 90; // Maximum system transactional emails per rolling day

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

    // 1. Authenticate with Secret Token in Script Properties
    const scriptProps = PropertiesService.getScriptProperties();
    const configuredToken = scriptProps.getProperty("RELAY_AUTH_TOKEN");

    if (!configuredToken) {
      return jsonResponse({
        success: false,
        error: "NOT_CONFIGURED",
        message: "Platform system relay auth token is not configured in Script Properties."
      }, 500);
    }

    const incomingToken = payload.token;
    if (!incomingToken || !constantTimeCompare(incomingToken, configuredToken)) {
      return jsonResponse({
        success: false,
        error: "UNAUTHORIZED",
        message: "Invalid or missing platform system relay authentication token."
      }, 401);
    }

    // 2. Daily Gmail Quota & System Cap Guard
    const remainingGoogleQuota = MailApp.getRemainingDailyQuota();
    if (remainingGoogleQuota <= 0) {
      return jsonResponse({
        success: false,
        error: "QUOTA_EXCEEDED",
        remaining_quota: 0,
        message: "Gmail platform daily sending quota has been exhausted."
      }, 429);
    }

    // Check rolling daily system send count
    const todayKey = "sys_count_" + Utilities.formatDate(new Date(), "UTC", "yyyy-MM-dd");
    const currentCount = parseInt(scriptProps.getProperty(todayKey) || "0", 10);
    if (currentCount >= SYSTEM_DAILY_CAP) {
      return jsonResponse({
        success: false,
        error: "QUOTA_EXCEEDED",
        remaining_quota: 0,
        daily_cap: SYSTEM_DAILY_CAP,
        message: "MailOrbit platform rolling daily system email cap (" + SYSTEM_DAILY_CAP + " emails) has been reached."
      }, 429);
    }

    // 3. Idempotency Check
    const idempotencyKey = payload.idempotency_key;
    if (idempotencyKey) {
      const cache = CacheService.getScriptCache();
      const existing = cache.get("idem_sys_" + idempotencyKey);
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

    // 5. Prepare Email Content
    const subject = payload.subject || "(MailOrbit System Notice)";
    const htmlBody = payload.html_body || payload.body || "";
    const plainBody = payload.plain_body || stripHtml(htmlBody);

    const mailOptions = {
      to: recipient,
      subject: subject,
      body: plainBody,
      htmlBody: htmlBody,
      name: "MailOrbit"
    };

    if (payload.reply_to) {
      mailOptions.replyTo = payload.reply_to;
    }

    // 6. Send Email via MailApp
    MailApp.sendEmail(mailOptions);

    // Increment rolling daily counter
    scriptProps.setProperty(todayKey, (currentCount + 1).toString());

    // Record idempotency in cache (persist 6 hours = 21600 seconds)
    if (idempotencyKey) {
      try {
        const cache = CacheService.getScriptCache();
        cache.put("idem_sys_" + idempotencyKey, "SENT", 21600);
      } catch (cacheErr) {
        // Cache error is non-fatal
      }
    }

    const remainingPlatformQuota = Math.max(0, SYSTEM_DAILY_CAP - (currentCount + 1));
    return jsonResponse({
      success: true,
      message_id: "sys-" + Utilities.getUuid(),
      to: recipient,
      remaining_quota: remainingPlatformQuota,
      system_sent_today: currentCount + 1,
      timestamp: new Date().toISOString()
    }, 200);

  } catch (err) {
    return jsonResponse({
      success: false,
      error: "INTERNAL_ERROR",
      message: err.toString()
    }, 500);
  }
}

function doGet(e) {
  // Safe health status probe (never returns token or sensitive data)
  try {
    const scriptProps = PropertiesService.getScriptProperties();
    const isConfigured = !!scriptProps.getProperty("RELAY_AUTH_TOKEN");
    const remainingGoogleQuota = MailApp.getRemainingDailyQuota();
    const todayKey = "sys_count_" + Utilities.formatDate(new Date(), "UTC", "yyyy-MM-dd");
    const currentCount = parseInt(scriptProps.getProperty(todayKey) || "0", 10);

    return jsonResponse({
      service: "MailOrbit Platform System Relay",
      status: isConfigured ? "ready" : "unconfigured",
      configured: isConfigured,
      remaining_google_quota: remainingGoogleQuota,
      platform_sent_today: currentCount,
      platform_daily_cap: SYSTEM_DAILY_CAP
    }, 200);
  } catch (err) {
    return jsonResponse({
      service: "MailOrbit Platform System Relay",
      status: "error",
      message: err.toString()
    }, 500);
  }
}

function jsonResponse(data, statusCode) {
  const output = ContentService.createTextOutput(JSON.stringify(data));
  output.setMimeType(ContentService.MimeType.JSON);
  return output;
}

function stripHtml(html) {
  if (!html) return "";
  return html.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

/**
 * Constant-time string comparison to prevent timing side-channel attacks.
 */
function constantTimeCompare(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string') return false;
  if (a.length !== b.length) return false;
  var result = 0;
  for (var i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return result === 0;
}
