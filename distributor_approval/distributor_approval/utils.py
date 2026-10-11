import frappe

PENDING = "Pending Review"
APPROVED = "Approved"
REJECTED = "Rejected"

DISTRIBUTOR_GROUP = "Distributor"

# Roles allowed to change a distributor's status
REVIEW_ROLES = {"System Manager", "Sales Manager", "Sales Master Manager"}

# Customers created before this app (status left empty): should they see prices?
# False = strict (only explicitly "Approved" customers see prices).
BLANK_STATUS_COUNTS_AS_APPROVED = False


def get_distributor_status(user: str | None = None):
    """Return the best status among the customers linked to this user.

    APPROVED > PENDING > REJECTED, "" if a customer exists with no status,
    None if the user has no linked customer.
    """
    user = user or frappe.session.user
    if not user or user == "Guest":
        return None

    customers = frappe.get_all(
        "Portal User",
        filters={"user": user, "parenttype": "Customer"},
        pluck="parent",
    )
    if not customers:
        return None

    statuses = frappe.get_all(
        "Customer",
        filters={"name": ("in", customers)},
        pluck="distributor_status",
    )
    for wanted in (APPROVED, PENDING, REJECTED):
        if wanted in statuses:
            return wanted
    return ""


def is_staff(user: str) -> bool:
    return frappe.db.get_value("User", user, "user_type") == "System User"


def can_view_prices(user: str | None = None) -> bool:
    user = user or frappe.session.user
    if not user or user == "Guest":
        return False
    if is_staff(user):
        return True

    status = get_distributor_status(user)
    if status == APPROVED:
        return True
    if status == "" and BLANK_STATUS_COUNTS_AS_APPROVED:
        return True
    return False
