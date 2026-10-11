import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from distributor_approval.utils import DISTRIBUTOR_GROUP

CUSTOM_FIELDS = {
    "Customer": [
        {
            "fieldname": "distributor_section",
            "label": "Distributor Verification",
            "fieldtype": "Section Break",
        },
        {
            "fieldname": "distributor_status",
            "label": "Distributor Status",
            "fieldtype": "Select",
            "options": "\nPending Review\nApproved\nRejected",
            "in_standard_filter": 1,
            "no_copy": 1,
        },
        {
            "fieldname": "distributor_requested_on",
            "label": "Requested On",
            "fieldtype": "Datetime",
            "read_only": 1,
            "no_copy": 1,
        },
        {
            "fieldname": "distributor_reviewed_by",
            "label": "Reviewed By",
            "fieldtype": "Link",
            "options": "User",
            "read_only": 1,
            "no_copy": 1,
        },
        {
            "fieldname": "distributor_reviewed_on",
            "label": "Reviewed On",
            "fieldtype": "Datetime",
            "read_only": 1,
            "no_copy": 1,
        },
        {
            "fieldname": "rejection_reason",
            "label": "Rejection Reason",
            "fieldtype": "Small Text",
            "depends_on": "eval:doc.distributor_status=='Rejected'",
            "no_copy": 1,
        },
        {
            "fieldname": "legal_ids_section",
            "label": "Legal Identifiers (Algeria)",
            "fieldtype": "Section Break",
        },
        {"fieldname": "nif", "label": "NIF", "fieldtype": "Data", "no_copy": 1},
        {
            "fieldname": "rc",
            "label": "RC (Registre du Commerce)",
            "fieldtype": "Data",
            "no_copy": 1,
        },
        {"fieldname": "nis", "label": "NIS", "fieldtype": "Data", "no_copy": 1},
        {
            "fieldname": "legal_ids_col",
            "fieldtype": "Column Break",
        },
        {
            "fieldname": "nif_document",
            "label": "NIF Document",
            "fieldtype": "Attach",
            "no_copy": 1,
        },
        {
            "fieldname": "rc_document",
            "label": "RC Document",
            "fieldtype": "Attach",
            "no_copy": 1,
        },
        {
            "fieldname": "nis_document",
            "label": "NIS Document",
            "fieldtype": "Attach",
            "no_copy": 1,
        },
    ]
}


def setup():
    create_custom_fields(CUSTOM_FIELDS, update=True)
    _ensure_customer_group()
    frappe.clear_cache(doctype="Customer")


def _ensure_customer_group():
    if frappe.db.exists("Customer Group", DISTRIBUTOR_GROUP):
        return
    frappe.get_doc(
        {
            "doctype": "Customer Group",
            "customer_group_name": DISTRIBUTOR_GROUP,
            "parent_customer_group": "All Customer Groups",
            "is_group": 0,
        }
    ).insert(ignore_permissions=True)


def after_install():
    setup()


def after_migrate():
    setup()
