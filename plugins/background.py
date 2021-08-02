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
import typing
import netaddr
import time
import plugins.configuration
import datetime


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

    q = elasticsearch_dsl.Search(using=config.elasticsearch)
    q = q.filter("range", timestamp={"gte": f"now-{duration}"})

    # Make a list of the past three days' index names:
    d = datetime.datetime.utcnow()
    t = []
    for i in range(0,3):
        t.append(d.strftime(config.index_pattern))
        d -= datetime.timedelta(days=1)
    threes = ",".join(t)

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
        q.aggs.bucket("requests_per_ip", elasticsearch_dsl.A("terms", field="client_ip.keyword", size=no_hits))
    elif aggtype == "bytes":
        q.aggs.bucket(
            "requests_per_ip",
            elasticsearch_dsl.A("terms", field="client_ip.keyword", size=no_hits, order={"bytes_sum": "desc"}),
        ).metric("bytes_sum", "sum", field="bytes")

    resp = await config.elasticsearch.search(index=threes, body=q.to_dict(), size=0)
    top_ips = []
    if 'aggregations' not in resp:
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
        self.description = ruledict['description']
        self.aggtype = ruledict['aggtype']
        self.limit = ruledict['limit']
        self.duration = ruledict['duration']
        self.filters = [x.strip() for x in ruledict['filters'].split("\n") if x.strip()]

    async def list_offenders(self, config: plugins.configuration.BlockyConfiguration):
        """Find top clients by $metric, see if they cross the limit..."""
        offenders = []
        candidates = await find_top_clients(config, aggtype=self.aggtype, duration=self.duration, filters=self.filters)
        for candidate in candidates:
            if candidate[1] >= self.limit:
                offenders.append(candidate)
        return offenders


async def run(config: plugins.configuration.BlockyConfiguration):

    # Search forever, sleep a little in between
    while True:
        for rule in config.sqlite.fetch("rules", limit=0):
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
                            isinstance(allowed_ip, netaddr.IPNetwork)
                            and off_ip_na in allowed_ip
                            or isinstance(allowed_ip, netaddr.IPAddress)
                            and off_ip_na == allowed_ip
                        ):
                            #  print(f"IP {off_ip} is on the allow list, ignoring...")
                            ignore_ip = True
                            break
                    for blocked_ip in config.block_list:
                        if (
                            isinstance(blocked_ip, netaddr.IPNetwork)
                            and off_ip_na in blocked_ip
                            or isinstance(blocked_ip, netaddr.IPAddress)
                            and off_ip_na == blocked_ip
                        ):
                            #  print(f"IP {off_ip} is already blocked, ignoring...")
                            ignore_ip = True
                            break
                    if not ignore_ip:
                        off_reason = f"{rule['description']} ({off_limit} >= {rule['limit']})"
                        print(f"Found new offender, {off_ip}: {off_reason}")
                        config.block_list.append(off_ip_na)
                        config.sqlite.insert(
                            "blocklist",
                            {
                                "ip": off_ip,
                                "timestamp": int(time.time()),
                                "expires": int(time.time()) + config.default_expire_seconds,
                                "reason": off_reason,
                            },
                        )
                        config.sqlite.insert(
                            "auditlog",
                            {"ip": off_ip, "timestamp": int(time.time()), "event": f"Banned IP {off_ip}: {off_reason}"},
                        )
                        # TODO: push_to_pubsub()
        #  TODO: expire outdated bans
        await asyncio.sleep(15)
