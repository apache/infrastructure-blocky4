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
import plugins.lists
import time

""" Generic add-block endpoint for Blocky/4"""


async def process(state: plugins.configuration.BlockyConfiguration, request, formdata: dict) -> dict:
    now = int(time.time())
    force = bool(formdata.get("force", False))
    ip = formdata.get("ip")
    reason = formdata.get("reason", "no reason specified")
    expires = int(formdata.get("expires", 0))
    if not expires:
        expires = now + state.default_expire_seconds
    host = formdata.get("host", plugins.configuration.DEFAULT_HOST_BLOCK)

    try:
        state.block_list.add(ip=ip, expires=expires, reason=reason, host=host, force=force)
    except plugins.lists.BlockListException as e:
        return {"success": False, "status": "failure", "message": str(e)}

    # All good!
    return {"success": True, "status": "blocked", "message": f"IP {ip} added to block list"}


def register(config: plugins.configuration.BlockyConfiguration):
    return ahapi.endpoint(process)
