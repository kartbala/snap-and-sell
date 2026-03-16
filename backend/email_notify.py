"""Email notification composition for Snap & Sell.

Composes email dicts (to, subject, body) that can be sent via
Google Workspace MCP's send_gmail_message tool during Claude Code sessions.
"""
from __future__ import annotations
import os

DEFAULT_NOTIFICATION_EMAIL = os.environ.get(
    "NOTIFICATION_EMAIL", "karthik@balasubramanian.us"
)
DEFAULT_CONTACT_NUMBER = os.environ.get(
    "GOOGLE_VOICE_NUMBER", "+1-202-684-6252"
)


def compose_seller_notification(
    listing_title: str,
    buyer_name: str,
    offer_amount: float,
    decision: str,
    dashboard_url: str = "",
    notification_email: str = DEFAULT_NOTIFICATION_EMAIL,
) -> dict:
    """Compose an email to the seller about a new offer."""
    subject = f"Snap & Sell: New offer on {listing_title} — {decision}"
    body = (
        f"New offer received:\n\n"
        f"Item: {listing_title}\n"
        f"Buyer: {buyer_name}\n"
        f"Offer: ${offer_amount:,.2f}\n"
        f"Decision: {decision}\n"
    )
    if dashboard_url:
        body += f"\nReview in dashboard: {dashboard_url}\n"
    return {"to": notification_email, "subject": subject, "body": body}


def compose_buyer_acceptance(
    listing_title: str,
    offer_amount: float,
    buyer_email: str,
    pickup_type: str,
    pickup_details: str,
    contact_number: str = DEFAULT_CONTACT_NUMBER,
) -> dict:
    """Compose an email to the buyer that their offer was accepted."""
    subject = f"Your offer on {listing_title} was accepted!"
    body = (
        f"Great news! Your offer of ${offer_amount:,.2f} for {listing_title} has been accepted.\n\n"
        f"Pickup: {pickup_details}\n"
        f"Contact Karthik at {contact_number} to arrange a time.\n"
    )
    if pickup_type == "home":
        body += "\nPlease text or call to confirm a pickup window.\n"
    else:
        body += "\nMeet at the location above. Bring exact cash or Venmo/Zelle.\n"
    return {"to": buyer_email, "subject": subject, "body": body}
