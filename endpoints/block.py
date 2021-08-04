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
import netaddr
import time

""" Generic add-block endpoint for Blocky/4"""


async def process(state: plugins.configuration.BlockyConfiguration, request, formdata: dict) -> dict:
    force = formdata.get("force", False)
    ip = formdata.get("ip")
    reason = formdata.get("reason", "no reason specified")
    expires = int(formdata.get("expires", 0))
    if not expires:
        expires = time.time() + state.default_expire_seconds
    host = formdata.get("host", plugins.configuration.DEFAULT_HOST_BLOCK)
    ip_as_network = netaddr.IPNetwork(ip)

    # Check if IP address conflicts with an entry on the allow list
    to_remove = []
    for network in state.allow_list:
        if ip_as_network in network.network or network.network in ip_as_network:
            if force:
                to_remove.append(network)
            else:
                return {
                    "success": False,
                    "status": "failure",
                    "message": f"IP entry {ip} conflicts with allow list entry {network.network}. "
                    "Please address this or use force=true to override.",
                }

    # Check if already blocked
    for network in state.block_list:
        if ip_as_network in network.network or network.network in ip_as_network:
            if force:
                to_remove.append(network)
            else:
                return {
                    "success": False,
                    "status": "failure",
                    "message": f"IP entry {ip} conflicts with block list entry {network.network}. "
                    "Please address this or use force=true to override.",
                }
    # If force=true and a conflict was found, remove the conflicting entry
    for entry in to_remove:
        if entry in state.allow_list:
            state.sqlite.delete("allowlist", ip=entry["ip"])
            state.allow_list.remove(entry)
        if entry in state.block_list:
            state.sqlite.delete("blocklist", ip=entry["ip"])
            state.block_list.remove(entry)

    # Now add the block
    now = int(time.time())
    new_block = plugins.configuration.BlockyBlock(
        ip=ip,
        timestamp=now,
        expires=expires,
        reason=reason,
        host=host,
    )
    state.block_list.append(new_block)
    state.sqlite.insert(
        "blocklist",
        new_block,
    )

    # Add to audit log
    state.sqlite.insert(
        "auditlog",
        {"ip": ip, "timestamp": int(time.time()), "event": f"Blocked IP {ip}: {reason}"},
    )

    # All good!
    return {"success": True, "status": "blocked", "message": f"IP {ip} added to block list"}


def register(config: plugins.configuration.BlockyConfiguration):
    return ahapi.endpoint(process)
