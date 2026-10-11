app_name = "distributor_approval"
app_title = "Distributor Approval"
app_publisher = "Your Company"
app_description = "B2B distributor registration (NIF / RC / NIS) with manual approval"
app_email = "you@example.com"
app_license = "MIT"

required_apps = ["erpnext"]

# Create the custom fields / customer group on install and keep them on migrate
after_install = "distributor_approval.install.after_install"
after_migrate = "distributor_approval.install.after_migrate"

doc_events = {
    "Customer": {
        "validate": "distributor_approval.events.customer_validate",
        "on_update": "distributor_approval.events.customer_on_update",
    }
}

# Usable inside Jinja templates: {{ can_view_prices() }}
jinja = {
    "methods": [
        "distributor_approval.utils.can_view_prices",
    ]
}
