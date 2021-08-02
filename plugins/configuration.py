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

# Configuration objects for Blocky/4

import asfpy.sqlite
import elasticsearch
import plugins.db_create
import netaddr


DEFAULT_EXPIRE = 86400 * 30 * 4  # Default expiry of auto-bans = 4 months
DEFAULT_INDEX_PATTERN = "loggy-%Y-%m-%d"

# These IP blocks should always be allowed and never blocked, or else...
DEFAULT_ALLOW_LIST = [
    netaddr.IPNetwork("127.0.0.1/16"),
    netaddr.IPNetwork("10.0.0.1/16"),
    netaddr.IPNetwork("::1/128"),
]


class BlockyConfiguration:
    def __init__(self, yml):
        self.database_filepath = yml.get("database", "blocky.sqlite")
        self.sqlite = asfpy.sqlite.DB(self.database_filepath)
        self.default_expire_seconds = yml.get("default_expire", DEFAULT_EXPIRE)
        self.index_pattern = yml.get("index_pattern", DEFAULT_INDEX_PATTERN)
        self.elasticsearch_url = yml.get("elasticsearch_url")
        self.elasticsearch = elasticsearch.AsyncElasticsearch(hosts=[self.elasticsearch_url])
        self.block_list = []
        self.allow_list = list(DEFAULT_ALLOW_LIST)  # Always pre-seed with the basic default
        self.http_ip = yml.get('bind_ip', '127.0.0.1')
        self.http_port = int(yml.get('bind_port', 8080))

        # Create table if not there yet
        if not self.sqlite.table_exists("rules"):
            print(f"Database file {self.database_filepath} is empty, initializing tables")
            self.sqlite.run(plugins.db_create.CREATE_DB_RULES)
            self.sqlite.run(plugins.db_create.CREATE_DB_BANS)
            self.sqlite.run(plugins.db_create.CREATE_DB_ALLOW)
            self.sqlite.run(plugins.db_create.CREATE_DB_AUDIT)
            print(f"Database file {self.database_filepath} has been successfully initialized")

        # Fetch existing blocks and allows
        for entry in self.sqlite.fetch("blocklist", limit=0):
            self.block_list.append(netaddr.IPNetwork(entry["ip"]))
        for entry in self.sqlite.fetch("allowlist", limit=0):
            self.allow_list.append(netaddr.IPNetwork(entry["ip"]))

    async def test_es(self):
        i = await self.elasticsearch.info()
        es_major = int(i["version"]["number"].split(".")[0])
        assert es_major >= 7, "Blocky/4 requires ElasticSearch 7.x or higher"
