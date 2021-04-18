# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

from datetime import timedelta

from flask import jsonify, request
from sqlalchemy.orm import joinedload

from bkr.server.app import app
from bkr.server.flask_util import admin_auth_required, read_json_request
from bkr.server.model import Watchdog, Recipe, RecipeSet, Job, RecipeTask


@app.route("/watchdogs", methods=["GET"])
def get_watchdogs():
    query = (
        Watchdog.by_status(status=u"active")
        .join(Watchdog.recipe)
        .join(Recipe.recipeset)
        .join(RecipeSet.job)
        .order_by(Job.id)
        .options(
            joinedload(Watchdog.recipe)
            .joinedload(Recipe.recipeset)
            .joinedload(RecipeSet.job),
            joinedload(Watchdog.recipe)
            .joinedload(Recipe.recipeset)
            .joinedload(RecipeSet.lab_controller),
            joinedload(Watchdog.recipetask).joinedload(RecipeTask.task),
        )
    )

    items = []
    for watchdog in query:
        w = {
            "job_id": watchdog.recipe.recipeset.job_id,
            "system_name": watchdog.recipe.resource.fqdn,
            "lab_controller": watchdog.recipe.recipeset.lab_controller.fqdn,
            "task_name": watchdog.recipetask.name,
            "kill_time": watchdog.kill_time,
        }
        items.append(w)

    payload = {"length": len(items), "items": items}

    return jsonify(payload)


@app.route("/watchdogs", methods=["POST"])
@admin_auth_required
def set_watchdogs():
    """Allow admins to push watchdog times out after an outage"""
    payload = read_json_request(request)
    time = payload.get("time")

    items = []
    for w in Watchdog.by_status(status=u"active"):
        n_kill_time = w.kill_time + timedelta(seconds=time)
        record = {
            "recipe_id": w.recipe_id,
            "old_time": w.kill_time,
            "new_time": n_kill_time,
        }
        w.kill_time = n_kill_time
        items.append(record)

    payload = {"length": len(items), "items": items}

    return jsonify(payload)
