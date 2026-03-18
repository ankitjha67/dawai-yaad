"""FCM push notification service — Firebase Cloud Messaging integration.

Gracefully degrades when Firebase is not configured (dev mode):
logs the notification but does not send it.
"""

import logging
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Firebase Admin SDK initialization (lazy)
_firebase_app = None
_fcm_available = False


def _init_firebase() -> bool:
    """Initialize Firebase Admin SDK if configured. Returns True on success."""
    global _firebase_app, _fcm_available

    if _firebase_app is not None:
        return _fcm_available

    if not settings.fcm_project_id:
        logger.info("FCM not configured — push notifications will be logged only")
        _firebase_app = False  # Mark as attempted
        _fcm_available = False
        return False

    try:
        import firebase_admin
        from firebase_admin import credentials

        # Use application default credentials or service account
        cred = credentials.ApplicationDefault()
        _firebase_app = firebase_admin.initialize_app(cred, {
            "projectId": settings.fcm_project_id,
        })
        _fcm_available = True
        logger.info("Firebase Admin SDK initialized successfully")
        return True
    except Exception as e:
        logger.warning(f"Firebase initialization failed: {e}. Push notifications disabled.")
        _firebase_app = False
        _fcm_available = False
        return False


def send_push(
    fcm_token: str,
    title: str,
    body: str,
    data: Optional[dict] = None,
    critical: bool = False,
) -> bool:
    """Send a push notification via FCM.

    Args:
        fcm_token: Device FCM registration token.
        title: Notification title.
        body: Notification body text.
        data: Optional data payload (key-value pairs).
        critical: If True, sends as high-priority (bypasses silent mode on Android).

    Returns:
        True if sent successfully, False otherwise.
    """
    if not fcm_token:
        logger.debug("No FCM token — skipping push")
        return False

    _init_firebase()

    if not _fcm_available:
        logger.info(f"[DEV PUSH] → {title}: {body} (token={fcm_token[:12]}...)")
        return True  # Return True in dev mode so callers proceed normally

    try:
        from firebase_admin import messaging

        # Build notification
        notification = messaging.Notification(title=title, body=body)

        # Android config with priority
        android_config = messaging.AndroidConfig(
            priority="high" if critical else "normal",
            notification=messaging.AndroidNotification(
                title=title,
                body=body,
                channel_id="medication_critical" if critical else "medication_reminder",
                sound="alarm" if critical else "default",
            ),
        )

        # APNS config for iOS
        apns_config = messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    alert=messaging.ApsAlert(title=title, body=body),
                    sound="critical" if critical else "default",
                    content_available=True,
                ),
            ),
        )

        message = messaging.Message(
            notification=notification,
            android=android_config,
            apns=apns_config,
            data=data or {},
            token=fcm_token,
        )

        response = messaging.send(message)
        logger.info(f"FCM push sent: {response}")
        return True

    except Exception as e:
        logger.error(f"FCM push failed: {e}")
        return False


def send_push_to_many(
    fcm_tokens: list[str],
    title: str,
    body: str,
    data: Optional[dict] = None,
    critical: bool = False,
) -> int:
    """Send push notification to multiple devices.

    Returns count of successful sends.
    """
    sent = 0
    for token in fcm_tokens:
        if send_push(token, title, body, data, critical):
            sent += 1
    return sent
