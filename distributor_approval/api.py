import os

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, get_url, now_datetime, validate_email_address

from distributor_approval import utils
from distributor_approval.utils import DISTRIBUTOR_GROUP, PENDING

# ---- Settings you may want to tweak -------------------------------------
REQUIRED_DOCUMENTS = ("nif_document", "rc_document")  # uploads that must be present
DOCUMENT_FIELDS = ("nif_document", "rc_document", "nis_document")
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB
SEND_PASSWORD_SETUP_EMAIL = True  # email the new user a link to set a password
# -------------------------------------------------------------------------

_MAGIC = {
    ".pdf": (b"%PDF",),
    ".png": (b"\x89PNG",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=60 * 60)
def register_distributor(
    first_name,
    last_name,
    email,
    mobile,
    nif,
    rc,
    nis,
    company_name=None,
):
    """Public endpoint: create a distributor account in 'Pending Review' state.

    Send as multipart/form-data so the document files can be included:
    nif_document, rc_document, nis_document.
    """
    first_name = (first_name or "").strip()
    last_name = (last_name or "").strip()
    mobile = (mobile or "").strip()
    nif = _digits(nif)
    nis = _digits(nis)
    rc = (rc or "").strip()
    company_name = (company_name or "").strip()

    if not (first_name and last_name):
        frappe.throw(_("First name and last name are required."))
    if not mobile:
        frappe.throw(_("Mobile number is required."))

    email = validate_email_address(email, throw=True)

    # Basic format checks (adjust to your needs)
    if len(nif) < 15:
        frappe.throw(_("NIF must contain at least 15 digits."))
    if len(nis) < 15:
        frappe.throw(_("NIS must contain at least 15 digits."))
    if not rc:
        frappe.throw(_("RC is required."))

    if frappe.db.exists("User", email):
        frappe.throw(_("An account with this email already exists."))
    if frappe.db.exists("Customer", {"nif": nif}):
        frappe.throw(_("A distributor with this NIF is already registered."))

    files = _read_uploaded_files()

    user = _create_user(email, first_name, last_name, mobile)
    customer = _create_customer(
        user, first_name, last_name, mobile, nif, rc, nis, company_name
    )
    _attach_documents(customer, files)
    _notify_reviewers(customer)

    return {
        "status": "pending",
        "customer": customer.name,
        "message": _(
            "Your request has been received. We will review your documents and email you."
        ),
    }


@frappe.whitelist()
def get_distributor_status():
    """Status of the logged-in user (for the storefront)."""
    status = utils.get_distributor_status()
    return {
        "status": status,
        "can_view_prices": utils.can_view_prices(),
    }


@frappe.whitelist(allow_guest=True)
def can_view_prices():
    """True only for staff and approved distributors. Use this before showing prices."""
    return utils.can_view_prices()


# ---- helpers --------------------------------------------------------------


def _digits(value) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def _read_uploaded_files() -> dict:
    """Validate and read uploaded documents before anything is created."""
    uploaded = {}
    request_files = getattr(frappe.request, "files", None)

    for fieldname in DOCUMENT_FIELDS:
        f = request_files.get(fieldname) if request_files else None
        if not f or not f.filename:
            if fieldname in REQUIRED_DOCUMENTS:
                frappe.throw(_("Missing required document: {0}").format(fieldname))
            continue

        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            frappe.throw(_("Only PDF, JPG and PNG files are allowed."))

        content = f.read(MAX_FILE_BYTES + 1)
        if len(content) > MAX_FILE_BYTES:
            frappe.throw(_("Each file must be 5 MB or smaller."))
        if not any(content.startswith(sig) for sig in _MAGIC[ext]):
            frappe.throw(_("The uploaded file does not match its extension."))

        uploaded[fieldname] = (os.path.basename(f.filename), content)

    return uploaded


def _create_user(email, first_name, last_name, mobile):
    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "mobile_no": mobile,
            "enabled": 1,
            "user_type": "Website User",
            "send_welcome_email": 0,
        }
    )
    user.flags.ignore_permissions = True
    user.insert()

    try:
        user.add_roles("Customer")
    except Exception:
        frappe.log_error(title="Distributor Approval: add_roles failed")

    if SEND_PASSWORD_SETUP_EMAIL:
        try:
            user.reset_password(send_email=True)
        except Exception:
            frappe.log_error(title="Distributor Approval: password email failed")

    return user


def _create_customer(user, first_name, last_name, mobile, nif, rc, nis, company_name):
    group = (
        DISTRIBUTOR_GROUP
        if frappe.db.exists("Customer Group", DISTRIBUTOR_GROUP)
        else frappe.db.get_single_value("Selling Settings", "customer_group")
    )
    territory = (
        frappe.db.get_single_value("Selling Settings", "territory") or "All Territories"
    )

    customer = frappe.get_doc(
        {
            "doctype": "Customer",
            "customer_name": company_name or f"{first_name} {last_name}",
            "customer_type": "Company" if company_name else "Individual",
            "customer_group": group,
            "territory": territory,
            "nif": nif,
            "rc": rc,
            "nis": nis,
            "distributor_status": PENDING,
            "distributor_requested_on": now_datetime(),
        }
    )
    customer.append("portal_users", {"user": user.name})
    customer.flags.distributor_registration = True
    customer.insert(ignore_permissions=True)

    contact = frappe.get_doc(
        {
            "doctype": "Contact",
            "first_name": first_name,
            "last_name": last_name,
            "user": user.name,
            "email_ids": [{"email_id": user.name, "is_primary": 1}],
            "phone_nos": [{"phone": mobile, "is_primary_mobile_no": 1}],
            "links": [{"link_doctype": "Customer", "link_name": customer.name}],
        }
    )
    contact.insert(ignore_permissions=True)
    customer.db_set("customer_primary_contact", contact.name)

    return customer


def _attach_documents(customer, files: dict):
    for fieldname, (filename, content) in files.items():
        file_doc = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": filename,
                "attached_to_doctype": "Customer",
                "attached_to_name": customer.name,
                "attached_to_field": fieldname,
                "is_private": 1,
                "content": content,
            }
        )
        file_doc.save(ignore_permissions=True)
        customer.db_set(fieldname, file_doc.file_url)


def _notify_reviewers(customer):
    """Email the admins that a new distributor is waiting for review."""
    try:
        from frappe.utils.user import get_users_with_role

        recipients = [
            u
            for u in get_users_with_role("System Manager")
            if u and "@" in u and u not in ("admin@example.com",)
        ]
        if not recipients:
            return
        link = f"{get_url()}/app/customer/{frappe.utils.quote(customer.name)}"
        frappe.sendmail(
            recipients=recipients,
            subject=_("New distributor awaiting review: {0}").format(customer.customer_name),
            message=f'<p>NIF: {customer.nif}<br>RC: {customer.rc}<br>NIS: {customer.nis}</p>'
            f'<p><a href="{link}">{link}</a></p>',
        )
    except Exception:
        frappe.log_error(title="Distributor Approval: reviewer email failed")
