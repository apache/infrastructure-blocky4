#!/usr/bin/env python3

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
#

# Background worker - finds bans and adds 'em, and such and things

import asyncio
import elasticsearch_dsl
import elasticsearch
import typing
import netaddr
import time
import plugins.configuration
import plugins.lists
import datetime

MAX_DB_DAYS = 3  # Only look backwards up to three days. No sense in involving every index in our search.
CLIENT_IP_NAME = "client_ip"
TIMESTAMP_NAME = "@timestamp"


async def find_top_clients(
    config: plugins.configuration.BlockyConfiguration,
    aggtype: typing.Literal["bytes", "requests"] = "requests",
    duration: str = "12h",
    no_hits: int = 100,
    filters: typing.List[str] = [],
) -> typing.List[typing.Tuple[str, int]]:
    """Finds the top clients (IPs) in the database based on the parameters provided.
    Searches for the top clients by either traffic volume (bytes) or requests."""
    assert aggtype in ["bytes", "requests"], "Only by-bytes or by-requests aggregations are supported"
    if isinstance(filters, str):
        filters = [filters]
    elif filters is None:
        filters = []

    q = elasticsearch_dsl.Search(using=config.elasticsearch)
    q = q.filter("range", **{TIMESTAMP_NAME: {"gte": f"now-{duration}"}})

    # Make a list of the past three days' index names:
    d = datetime.datetime.utcnow()
    t = []
    for i in range(0, MAX_DB_DAYS):
        index_name = d.strftime(config.index_pattern)
        has_index = await config.elasticsearch.indices.exists(index=index_name)
        if has_index:
            t.append(index_name)
            d -= datetime.timedelta(days=1)
    threes = ",".join(t)
    if not threes:
        return []

    # Add all search filters
    for entry in filters:
        if entry:
            k, o, v = entry.split(" ", 2)  # key, operator, value
            xq = q.query  # Default is to add as search param
            if o.startswith("!"):  # exclude as search param?
                o = o[1:]
                xq = q.exclude
            if o == "=":
                q = xq("match", **{k: v})
            elif o == "~=":
                q = xq("regexp", **{k: v})
            elif o == "==":
                q = xq("term", **{k: v})
            else:
                raise TypeError(f"Unknown operator {o} in search filter: {entry}")
    if aggtype == "requests":
        q.aggs.bucket("requests_per_ip", elasticsearch_dsl.A("terms", field=f"{CLIENT_IP_NAME}.keyword", size=no_hits))
    elif aggtype == "bytes":
        q.aggs.bucket(
            "requests_per_ip",
            elasticsearch_dsl.A("terms", field=f"{CLIENT_IP_NAME}.keyword", size=no_hits, order={"bytes_sum": "desc"}),
        ).metric("bytes_sum", "sum", field="bytes")

    resp = await config.elasticsearch.search(index=threes, body=q.to_dict(), size=0, timeout="30s")
    top_ips = []
    if "aggregations" not in resp:
        print(f"Could not find aggregated data. Are you sure the index pattern {config.index_pattern} exists?")
        return []

    for entry in resp["aggregations"]["requests_per_ip"]["buckets"]:
        if "bytes_sum" in entry:
            top_ips.append(
                (
                    entry["key"],
                    int(entry["bytes_sum"]["value"]),
                )
            )
        else:
            top_ips.append(
                (
                    entry["key"],
                    int(entry["doc_count"]),
                )
            )
    return top_ips


class BanRule:
    def __init__(self, ruledict):
        self.description = ruledict["description"]
        self.aggtype = ruledict["aggtype"]
        self.limit = ruledict["limit"]
        self.duration = ruledict["duration"]
        self.filters = [x.strip() for x in ruledict["filters"].split("\n") if x.strip()]

    async def list_offenders(self, config: plugins.configuration.BlockyConfiguration):
        """Find top clients by $metric, see if they cross the limit..."""
        offenders = []
        candidates = []
        try:
            candidates = await find_top_clients(config, aggtype=self.aggtype, duration=self.duration, filters=self.filters)
        except (asyncio.exceptions.TimeoutError, elasticsearch.exceptions.ConnectionTimeout, elasticsearch.exceptions.ConnectionError):
            print("Offender search timed out, retrying later!")
        except elasticsearch.exceptions.TransportError:
            print("Transport error (503?), retrying later")
        for candidate in candidates:
            if candidate[1] >= self.limit:
                offenders.append(candidate)
        return offenders


async def run(config: plugins.configuration.BlockyConfiguration):

    # Search forever, sleep a little in between
    while True:
        # Find expired rules
        now = int(time.time())
        all_items = [item for item in config.sqlite.fetch("lists", limit=0)]
        for item in all_items:
            if item['expires'] == -1:
                continue  # never expires
            if item['expires'] < now:
                print(f"Expiring {item['type']} rule for {item['ip']}")
                if item['type'] == 'allow':
                    config.allow_list.remove(item['ip'])
                elif item['type'] == 'block':
                    config.block_list.remove(item['ip'])
                    # Try adding a temporary whitelist entry to flush on hosts
                    try:
                        config.allow_list.add(
                            ip=item["ip"],
                            timestamp=now,
                            expires=now + 600,  # Expire this rule in 10 minutes
                            reason="Temporary allow-listed by BLocky4 to unblock IP due to block expiring",
                            host=plugins.configuration.DEFAULT_HOST_BLOCK,
                            force=False
                        )
                    except plugins.lists.BlockListException:
                        pass  # If it conflicts, it should already be unblocked, so we don't care.
                else:
                    print("I don't actually know items of type {item['type']}, ignoring...")

        all_rules = [item for item in config.sqlite.fetch("rules", limit=0)]
        for rule in all_rules:
            #  print(f"Running rule #{rule['id']}: {rule['description']}...")
            my_rule = BanRule(rule)
            off = await my_rule.list_offenders(config)
            if off:
                for offender in off:
                    off_ip = offender[0]
                    off_limit = offender[1]
                    off_ip_na = netaddr.IPAddress(off_ip)
                    ignore_ip = False
                    for allowed_ip in config.allow_list:
                        if (
                            isinstance(allowed_ip.network, netaddr.IPNetwork)
                            and off_ip_na in allowed_ip.network
                            or isinstance(allowed_ip.network, netaddr.IPAddress)
                            and off_ip_na == allowed_ip.network
                        ):
                            #  print(f"IP {off_ip} is on the allow list, ignoring...")
                            ignore_ip = True
                            break
                    for blocked_ip in config.block_list:
                        if (
                            isinstance(blocked_ip.network, netaddr.IPNetwork)
                            and off_ip_na in blocked_ip.network
                            or isinstance(blocked_ip.network, netaddr.IPAddress)
                            and off_ip_na == blocked_ip.network
                        ):
                            #  print(f"IP {off_ip} is already blocked, ignoring...")
                            ignore_ip = True
                            break
                    if not ignore_ip:
                        off_reason = f"{rule['description']} ({off_limit} >= {rule['limit']})"
                        print(f"Found new offender, {off_ip}: {off_reason}")
                        now = int(time.time())
                        expires = now + config.default_expire_seconds
                        config.block_list.add(
                            ip=off_ip,
                            timestamp=now,
                            expires=expires,
                            reason=off_reason,
                            host=plugins.configuration.DEFAULT_HOST_BLOCK,
                        )
        await asyncio.sleep(15)
