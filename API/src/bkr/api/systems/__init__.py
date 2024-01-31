from flask import abort
from bkr.api.lab_controllers import LABCONTROLLERS
from bkr.api.arches import ARCHES
#from bkr.model import System

SYSTEMS = {}

def post(system):
    fqdn = system.get("fqdn")
    owner = system.get("owner")
    status = system.get("status", "unavailable")
    status_reason = system.get("status_reason", "")
    arches = system.get("arches", [])
    power = system.get("power", {})
    location = system.get("location", "")
    lender = system.get("lender", "")
    vender = system.get("vender", "")
    model = system.get("model", "")
    serial = system.get("serial", "")
    lab_controller = system.get("lab_controller", "")

    if lab_controller and lab_controller not in LABCONTROLLERS:
        abort(
                406,
                f"Lab Controller {lab_controller} doesn't exist",
                )

    for arch in arches:
        if arch not in ARCHES:
            abort(
                    406,
                    f"{arch} doesn't exist, create it first.",
                    )

    if fqdn and fqdn not in SYSTEMS:
        SYSTEMS[fqdn] = {
                "fqdn": fqdn,
                "owner": owner,
                "status": status,
                "status_reason": status_reason,
                "arches": arches,
                "power": power,
                "location": location,
                "lender": lender,
                "vender": vender,
                "model": model,
                "serial": serial,
                "lab_controller": lab_controller,
                }
        return SYSTEMS[fqdn], 201
    else:
        abort(
                406,
                f"System with fqdn {fqdn} already exists",
                )

def search(offset=0, limit=None):
    start = 0
    end = len(SYSTEMS.values())
    if offset and limit:
        start = offset * limit
        end = start + limit
    return list(SYSTEMS.values())[start:end]

def get(fqdn):
    if fqdn in SYSTEMS:
        return SYSTEMS[fqdn]
    else:
        abort(
                404,
                f"System with fqdn {fqdn} not found",
                )

def put(fqdn):
    pass

def delete(fqdn):
    pass
