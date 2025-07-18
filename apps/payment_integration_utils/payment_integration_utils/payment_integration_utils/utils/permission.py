import frappe
from frappe import _

from payment_integration_utils.payment_integration_utils.constants.roles import (
    ROLE_PROFILE,
)


def has_payment_permissions(
    payment_entries: str | list[str],
    throw: bool = False,
    ignore_impersonation: bool = False,
) -> bool:
    """
    Check current user has payment permissions or not!

    :param payment_entries: Payment Entry name or list of names.
    :param throw: If `True`, throws `PermissionError` if user doesn't have access.
    :param ignore_impersonation: If `True`, ignores the impersonation check.

    ---
    Checks:
    - User has role of payment authorizer.
    - User is not impersonated.
    - User can read integration documents.
    - User have permissions to submit/cancel the PE.
    """
    if frappe.session.user == "Administrator":
        if throw:
            frappe.throw(
                msg=_("Administrator can't authorize the payment."),
                title=_("Permission Error"),
                exc=frappe.PermissionError,
            )

        return False

    if not ignore_impersonation and frappe.session.data.get("impersonated_by"):
        if throw:
            frappe.throw(
                msg=_("Impersonated user can't authorize the payment."),
                title=_("Permission Error"),
                exc=frappe.PermissionError,
            )

        return False

    if not has_payment_authorizer_role(throw=throw):
        return False

    if not has_payment_entry_permission(payment_entries, throw=throw):
        return False

    return True


def has_payment_authorizer_role(*, throw=False) -> bool | None:
    has_authorizer_role = ROLE_PROFILE.PAYMENT_AUTHORIZER.value in frappe.get_roles()

    if not has_authorizer_role and throw:
        frappe.throw(
            title=_("Permission Error"),
            msg=_("You don't have permission to authorize the payment."),
            exc=frappe.PermissionError,
        )

    return has_authorizer_role


def has_payment_entry_permission(
    payment_entries: str | list[str], *, throw=False
) -> bool | None:
    """
    Check if user can submit/cancel the payment entries.
    Also checks for Integration Setting permission.

    :param payment_entries: Payment Entry name or list of names.
    :param throw: If `True`, throws `PermissionError` if user doesn't have access.

    ---
    If any single PE doesn't have permission, returns `False`.
    """
    if isinstance(payment_entries, str):
        payment_entries = [payment_entries]

    # Integration Setting.
    integration_settings = set(
        frappe.get_all(
            "Payment Entry",
            filters={"name": ("in", payment_entries)},
            fields=("integration_doctype", "integration_docname"),
            as_list=True,
        )
    )

    if not integration_settings:
        if throw:
            frappe.throw(
                title=_("Integration Settings Not Found"),
                msg=_("Please select valid Payment Entries to make payment."),
                exc=frappe.DoesNotExistError,
            )

        return False

    for doctype, docname in integration_settings:
        # integration setting is not set
        if not doctype or not docname:
            continue

        permission = frappe.has_permission(doctype, doc=docname, throw=throw)

        if not permission:
            return False

    # Payment Entry.
    for pe in payment_entries:
        permission = frappe.has_permission("Payment Entry", "submit", pe, throw=throw)

        if not permission:
            return False

    return True
