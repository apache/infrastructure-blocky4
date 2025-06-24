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
import operator
import time
import uuid
import aiohttp.web

""" client-side unblocking endpoint for Blocky/4"""

# Infraction rules:
# niceness -1 == You can unblock yourself by visiting from that IP
# niceness -2 or above == You can't unblock yourself, send an email..

async def process(state: plugins.configuration.BlockyConfiguration, request, formdata: dict) -> dict:
    token = formdata.get('token', None)
    if token:
        my_ip = request.headers["x-forwarded-for"]
        entry = state.sqlite.fetchone("santalist", token=token)
        if entry:
            if entry["ip"] == my_ip:
                if entry["niceness"] >= -1:  # If >= -1, they can unblock themselves
                    now = int(time.time())
                    expires = now + 600  # now + 10 min
                    entry["token"] = str(uuid.uuid4())  # Moon Healing Escalation....REFRESH! (so they can't use it again)
                    state.sqlite.update("santalist", entry, ip=my_ip)  # Update santa's list db with new token
                    state.allow_list.add(ip=my_ip, expires=expires, reason="Temporary soft-allowlisted to unblock, through self-serve UI.", host="*", force=True)
                    return aiohttp.web.Response(status=200, text=f"Successfully unblocked IP {my_ip}")
                return aiohttp.web.Response(status=422, text="You cannot automatically unblock this IP address due to its infraction count. Please contact abuse@infra.apache.org instead.")
            return aiohttp.web.Response(status=422, text="This token is not valid for the IP address you are currently connecting from. It must be used from the IP address that originated the block.")
    return aiohttp.web.Response(status=410, text="This token is invalid or has already been used to unblock this IP address. If you are still blocked from accessing our resources, please contact abuse@infra.apache.org")


def register(config: plugins.configuration.BlockyConfiguration):
    return ahapi.endpoint(process)
