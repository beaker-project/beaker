from flask import abort

ARCHES = {}

def post(arch):
    if arch and arch not in ARCHES:
        ARCHES[arch] = {
                "arch": arch,
                }
        return ARCHES[arch], 201
    else:
        abort(
                406,
                f"{arch} already exists",
                )

def search(offset=0, limit=None):
    start = 0
    end = len(ARCHES.values())
    if offset and limit:
        start = offset * limit
        end = start + limit
    return list(ARCHES.values())[start:end]
