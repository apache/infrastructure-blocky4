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
import aiohttp.web

""" abuse log viewer endpoint for Blocky/4"""


async def process(state: plugins.configuration.BlockyConfiguration, request, formdata: dict) -> dict:
    now = int(time.time())
    source = formdata.get("source")
    count = int(formdata.get("count", 1))
    _type = "csv" if formdata.get("type", "log") == "csv" else "log"
    try:
        as_net = netaddr.IPNetwork(source)
    except netaddr.core.AddrFormatError as e:
        return {
            "success": False,
            "status": "invalid",
            "message": f"Address parsing error: {e}"
        }
    reports = []
    results = list(state.sqlite.fetch("abuselog", limit=None))
    for entry in reversed(results):
        network = netaddr.IPNetwork(entry['ip'])
        if network in as_net or as_net in network:
            data = entry.get(_type, "")
            if data:
                reports.append(data)
        count -= 1
        if count <= 0:
          break


    # All good!
    if reports:
        ct = "text/plain"
        if _type == "csv":
            ct = "text/csv"
        return aiohttp.web.Response(status=200, content_type=ct, text="\n---------------------------------------------\n\n".join(reports))
    else:
        return "No results found..."


def register(config: plugins.configuration.BlockyConfiguration):
    return ahapi.endpoint(process)
