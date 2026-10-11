import frappe
from frappe import _
from frappe.utils import get_url, now_datetime

from distributor_approval.utils import APPROVED, PENDING, REJECTED, REVIEW_ROLES


def customer_validate(doc, method=None):
    """Only reviewers may change the distributor status."""
    before = doc.get_doc_before_save()
    old = (before.get("distributor_status") if before else None) or ""
    new = doc.get("distributor_status") or ""

    if old == new:
        return

    # Status set by our own public registration endpoint
    if doc.flags.get("distributor_registration"):
        return

    if frappe.flags.in_install or frappe.flags.in_patch or frappe.flags.in_migrate:
        return

    if not (REVIEW_ROLES & set(frappe.get_roles())):
        frappe.throw(
            _("You are not allowed to change the distributor status."),
            frappe.PermissionError,
        )

    if new == REJECTED and not (doc.get("rejection_reason") or "").strip():
        frappe.throw(_("Please enter a rejection reason."))

    if new in (APPROVED, REJECTED):
        doc.distributor_reviewed_by = frappe.session.user
        doc.distributor_reviewed_on = now_datetime()
    if new == APPROVED:
        doc.rejection_reason = None
    if new in (PENDING, ""):
        doc.distributor_reviewed_by = None
        doc.distributor_reviewed_on = None


def customer_on_update(doc, method=None):
    """Email the distributor when the status changes to Approved / Rejected."""
    before = doc.get_doc_before_save()
    if not before:
        return

    old = before.get("distributor_status") or ""
    new = doc.get("distributor_status") or ""
    if old == new or new not in (APPROVED, REJECTED):
        return

    recipients = [p.user for p in (doc.get("portal_users") or []) if p.user]
    if not recipients and doc.get("email_id"):
        recipients = [doc.email_id]
    if not recipients:
        return

    url = get_url()
    if new == APPROVED:
        subject = _("Your distributor account has been approved")
        message = f"""
        <p>مرحباً {frappe.utils.escape_html(doc.customer_name)}،</p>
        <p>تمت الموافقة على حسابك كموزع. يمكنك الآن تسجيل الدخول لرؤية الأسعار والطلب.</p>
        <p><a href="{url}">{url}</a></p>
        <hr>
        <p>Hello {frappe.utils.escape_html(doc.customer_name)},</p>
        <p>Your distributor account has been approved. You can now sign in to see prices and order.</p>
        """
    else:
        reason = frappe.utils.escape_html(doc.get("rejection_reason") or "-")
        subject = _("Your distributor application was not approved")
        message = f"""
        <p>مرحباً {frappe.utils.escape_html(doc.customer_name)}،</p>
        <p>نأسف، لم تتم الموافقة على طلبك. السبب: {reason}</p>
        <p>يمكنك التواصل معنا لتصحيح بياناتك.</p>
        <hr>
        <p>Hello {frappe.utils.escape_html(doc.customer_name)},</p>
        <p>Unfortunately your application was not approved. Reason: {reason}</p>
        """

    try:
        frappe.sendmail(recipients=recipients, subject=subject, message=message)
    except Exception:
        frappe.log_error(title="Distributor Approval: email failed")
