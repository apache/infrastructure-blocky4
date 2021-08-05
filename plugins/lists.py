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

import netaddr
import time
import plugins.configuration
import typing

""" Block- and Allow-list handlers """


class BlockListException(BaseException):
    def __init__(self, string: str):
        self.string = string

    def __str__(self):
        return self.string


class IPEntry(dict):
    def __init__(self, ip: str, timestamp: int, expires: int, reason: str = None, host: str = "*"):
        dict.__init__(self, ip=ip, timestamp=timestamp, expires=expires, reason=reason, host=host)
        self.network = netaddr.IPNetwork(ip)


class List:
    def __init__(self, state: "plugins.configuration.BlockyConfiguration", list_type: str = "block"):
        self.type = list_type
        self.list = []
        self.state = state

        for entry in state.sqlite.fetch("lists", type=list_type, limit=0):
            self.list.append(
                IPEntry(
                    ip=entry["ip"],
                    timestamp=0,
                    expires=entry["expires"],
                    reason=entry["reason"],
                    host=entry.get("host", "*"),
                )
            )

    def add(
        self,
        ip: typing.Union[str, IPEntry],
        timestamp: int = 0,
        expires: int = -1,
        reason: str = None,
        host: str = None,
        force: bool = False,
    ) -> None:
        """Add an IP or IP Range to the allow/block list"""
        now = int(time.time())
        if not timestamp:
            timestamp = now
        if not host:
            host = plugins.configuration.DEFAULT_BLOCK_HOST
        if isinstance(ip, str):
            entry = IPEntry(ip=ip, timestamp=timestamp, expires=expires, reason=reason, host=host)
        elif isinstance(ip, IPEntry):
            entry = ip

        # Check if IP address conflicts with an entry on the allow list
        to_remove = []
        for network in self.state.allow_list:
            if entry.network in network.network or network.network in entry.network:
                if force:
                    to_remove.append(network)
                else:
                    raise BlockListException(
                        f"IP entry {ip} conflicts with allow list entry {network.network}. "
                        "Please address this or use force=true to override."
                    )

        # Check if IP address conflicts with an entry on the block list
        for network in self.state.block_list:
            if entry.network in network.network or network.network in entry.network:
                if force:
                    to_remove.append(network)
                else:
                    raise BlockListException(
                        f"IP entry {ip} conflicts with block list entry {network.network}. "
                        "Please address this or use force=true to override."
                    )

        # If force=true and a conflict was found, remove the conflicting entry
        for entry in to_remove:
            if entry in self.state.allow_list:
                self.state.allow_list.remove(entry)
            if entry in self.state.block_list:
                self.state.block_list.remove(entry)

        # Now add the block
        self.list.append(entry)
        entry["type"] = self.type
        self.state.sqlite.insert(
            "lists",
            entry,
        )

        # Add to audit log
        self.state.sqlite.insert(
            "auditlog",
            {"ip": ip, "timestamp": int(time.time()), "event": f"IP {ip} added to the {self.type} list: {reason}"},
        )

    def remove(self, entry: typing.Union[str, IPEntry]):
        """Removes an IP/CIDR from the list"""
        if isinstance(entry, str):  # We want an IPEntry object. If given just an IP, find the object
            for x_entry in self.list:
                if x_entry["ip"] == entry:
                    entry = x_entry
                    break
        # Only try to remove if we have an entry in our list
        if entry and isinstance(entry, IPEntry) and entry in self.list:
            self.list.remove(entry)
            # Add to audit log
            self.state.sqlite.insert(
                "auditlog",
                {
                    "ip": entry["ip"],
                    "timestamp": int(time.time()),
                    "event": f"IP {entry['ip']} removed from the {self.type} list.",
                },
            )

    def __iter__(self):
        for entry in self.list:
            yield entry