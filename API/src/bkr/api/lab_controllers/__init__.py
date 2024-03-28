from flask import abort

LABCONTROLLERS = {}

def post(lab_controller):
    fqdn = lab_controller.get("fqdn")
    user_name = lab_controller.get("user_name", "")
    email_address = lab_controller.get("email_address", "")
    password = lab_controller.get("password", "")

    if fqdn and fqdn not in LABCONTROLLERS:
        LABCONTROLLERS[fqdn] = {
                "fqdn": fqdn,
                "user_name": user_name,
                "email_address": email_address,
                "password": password,
                }
        return LABCONTROLLERS[fqdn], 201
    else:
        abort(
                406,
                f"Lab Controller with fqdn {fqdn} already exists",
                )

def search(offset=0, limit=None):
    start = 0
    end = len(LABCONTROLLERS.values())
    if offset and limit:
        start = offset * limit
        end = start + limit
    return list(LABCONTROLLERS.values())[start:end]

def get(lab_controller):
    pass
