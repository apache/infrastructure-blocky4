#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import ahapi
import plugins.configuration
import re

""" rules get/set endpoint for Blocky/4"""


def validate_filter(filter):
    """Ensures a search filter is valid"""
    for entry in filter.split("\n"):
        if entry:
            k, o, v = entry.split(" ", 2)  # key, operator, value
            if o.startswith("!"):  # exclude as search param?
                o = o[1:]
            if o == "=":
                return True
            elif o == "~=":
                return True
            elif o == "==":
                return True
            else:
                raise TypeError(f"Unknown operator {o} in search filter: {entry}")


async def process(state: plugins.configuration.BlockyConfiguration, request, formdata: dict) -> dict:

    # Fetching rules?
    if request.method == "GET":
        rules = [x for x in state.sqlite.fetch("rules", limit=0)]
        return rules

    # Removing a rule?
    if request.method == "DELETE":
        rule_id = formdata.get("rule", -1)
        rule = state.sqlite.fetchone("rules", id=rule_id)
        if rule:
            state.sqlite.delete("rules", id=rule_id)
            return {"success": True, "status": "deleted", "message": f"Rule #{rule_id} has been deleted."}
        else:
            return {"success": False, "status": "not found", "message": f"Rule #{rule_id} does not exist."}

    # Adding a rule?
    if request.method == "PUT":
        try:
            description = formdata.get("description")
            assert description, "Please provide a description for your new rule"
            aggtype = formdata.get("aggtype")
            assert aggtype in ["requests", "bytes"], "aggtype must be either requests or bytes"
            limit = int(formdata.get("limit"))
            assert limit > 0, "limit must be greater than zero"
            duration = formdata.get("duration")
            assert re.match(r"^\d+[dhms]", duration), "duration must be of format 0-99[d/h/m/s], for instance 24h or 45m"
            filters = formdata.get("filter", "")
            try:
                validate_filter(filters)
            except TypeError as e:
                raise AssertionError(e)
        except AssertionError as e:
            return {
                "success": False,
                "status": "assertion error",
                "message": str(e),
            }
        entry = {
            "description": description,
            "aggtype": aggtype,
            "limit": limit,
            "duration": duration,
            "filters": filters,
        }
        # Check for duplicates first
        entry_inserted = state.sqlite.fetchone("rules", **entry)
        if entry_inserted:
            return {
                "success": False,
                "status": "duplicate",
                "message": f"Rule #{entry_inserted['id']} already exists with these parameters",
            }

        # Insert and return the ID it got
        state.sqlite.insert("rules", entry)
        entry_inserted = state.sqlite.fetchone("rules", **entry)
        return {"success": True, "status": "added", "message": f"Rule #{entry_inserted['id']} has been added"}

    # Patching a rule?
    if request.method == "PATCH":
        try:
            rule_id = int(formdata.get("rule", -1))
            description = formdata.get("description")
            assert description, "Please provide a description for your new rule"
            aggtype = formdata.get("aggtype")
            assert aggtype in ["requests", "bytes"], "aggtype must be either requests or bytes"
            limit = int(formdata.get("limit"))
            assert limit > 0, "limit must be greater than zero"
            duration = formdata.get("duration")
            assert re.match(r"^\d+[dhms]", duration), "duration must be of format 0-99[d/h/m/s], for instance 24h or 45m"
            filters = formdata.get("filter", "")
            try:
                validate_filter(filters)
            except TypeError as e:
                raise AssertionError(e)
        except AssertionError as e:
            return {
                "success": False,
                "status": "assertion error",
                "message": str(e),
            }
        entry = {
            "description": description,
            "aggtype": aggtype,
            "limit": limit,
            "duration": duration,
            "filters": filters,
        }
        # Check that rule exists
        existing_entry = state.sqlite.fetchone("rules", id=rule_id)
        if not existing_entry:
            return {"success": False, "status": "not found", "message": f"Rule #{rule_id} does not exist"}

        # Upsert rule
        state.sqlite.upsert("rules", entry, id=rule_id)
        return {"success": True, "status": "modified", "message": f"Rule #{rule_id} has been modified"}


def register(config: plugins.configuration.BlockyConfiguration):
    return ahapi.endpoint(process)
