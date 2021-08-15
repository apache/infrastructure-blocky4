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
import time
import netaddr

""" search endpoint for Blocky/4"""

MAX_IPTABLES_RECORDS = 50


async def process(state: plugins.configuration.BlockyConfiguration, request, formdata: dict) -> dict:
    now = int(time.time())
    source = formdata.get("source")
    try:
        as_net = netaddr.IPNetwork(source)
    except netaddr.core.AddrFormatError as e:
        return {
            "success": False,
            "status": "invalid",
            "message": f"Address parsing error: {e}"
        }
    results = {"allow": [], "block": [], "iptables": []}

    # Search allow list
    for entry in state.allow_list:
        if entry.network in as_net or as_net in entry.network:
            results["allow"].append(entry)

    # Search block list
    for entry in state.block_list:
        if entry.network in as_net or as_net in entry.network:
            results["block"].append(entry)

    # Search iptables (max 50-ish records)
    now = time.time()
    for hostname, entry in state.client_iptables.items():
        timestamp, iptables = entry
        if timestamp > now - 86400:  # Don't wanna fetch machines that have been offline for more than a day
            for rule in iptables:
                if rule["as_net"] in as_net or as_net in rule["as_net"]:
                    x_rule = dict(rule)
                    del x_rule["as_net"]  # Can't serialize
                    results["iptables"].append(x_rule)
                    if len(results["iptables"]) >= MAX_IPTABLES_RECORDS:
                        break
        if len(results["iptables"]) >= MAX_IPTABLES_RECORDS:
            break

    # All good!
    return results


def register(config: plugins.configuration.BlockyConfiguration):
    return ahapi.endpoint(process)
