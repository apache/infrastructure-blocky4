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

""" iptables upload endpoint for Blocky/4"""


async def process(state: plugins.configuration.BlockyConfiguration, request, formdata: dict) -> dict:
    now = int(time.time())
    hostname = formdata.get("hostname")
    assert hostname, "Hostname entry cannot be empty!"
    iptables = formdata.get("iptables")
    assert isinstance(iptables, list), "IPTables entry must be a list of rules"

    # Set in-memory data, no sqlite here.
    for entry in iptables:
        assert "source" in entry, "Each iptables entry must have a source address!"
        entry["as_net"] = netaddr.IPNetwork(entry["source"])
        entry["hostname"] = hostname
    state.client_iptables[hostname] = (now, iptables)

    # All good!
    return {"success": True, "status": "saved", "message": f"iptable data for {hostname} has been saved."}


def register(config: plugins.configuration.BlockyConfiguration):
    return ahapi.endpoint(process)
