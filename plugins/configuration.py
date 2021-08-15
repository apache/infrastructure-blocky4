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
import plugins.lists


DEFAULT_EXPIRE = 86400 * 30 * 4  # Default expiry of auto-bans = 4 months
DEFAULT_INDEX_PATTERN = "loggy-%Y-%m-%d"
DEFAULT_HOST_BLOCK = "*"  # Default hostname to block on. * means all hosts

# These IP blocks should always be allowed and never blocked, or else...
DEFAULT_ALLOW_LIST = [
    "127.0.0.1/16",
    "10.0.0.1/16",
    "::1/128",
]


class BlockyConfiguration:
    def __init__(self, yml):
        self.database_filepath = yml.get("database", "blocky.sqlite")
        self.sqlite = asfpy.sqlite.DB(self.database_filepath)
        self.default_expire_seconds = yml.get("default_expire", DEFAULT_EXPIRE)
        self.index_pattern = yml.get("index_pattern", DEFAULT_INDEX_PATTERN)
        self.elasticsearch_url = yml.get("elasticsearch_url")
        self.elasticsearch = elasticsearch.AsyncElasticsearch(hosts=[self.elasticsearch_url])
        self.http_ip = yml.get("bind_ip", "127.0.0.1")
        self.http_port = int(yml.get("bind_port", 8080))
        self.client_iptables = {}  # Uploaded iptables from blocky clients. Only kept in memory.
        self.pubsub_host = yml.get('pubsub_host')
        self.pubsub_user = yml.get('pubsub_user')
        self.pubsub_password = yml.get('pubsub_password')

        # Create table if not there yet
        new_db = False
        if not self.sqlite.table_exists("rules"):
            print(f"Database file {self.database_filepath} is empty, initializing tables")
            self.sqlite.run(plugins.db_create.CREATE_DB_RULES)
            self.sqlite.run(plugins.db_create.CREATE_DB_LISTS)
            self.sqlite.run(plugins.db_create.CREATE_DB_AUDIT)
            print(f"Database file {self.database_filepath} has been successfully initialized")
            new_db = True

        # Init and fetch existing blocks and allows
        self.block_list = plugins.lists.List(self, "block")
        self.allow_list = plugins.lists.List(self, "allow")

        # Seed new DB with default allows if needed
        if new_db:
            for entry in DEFAULT_ALLOW_LIST:
                self.allow_list.add(
                    ip=entry,
                    timestamp=0,
                    expires=-1,
                    reason="Default allowed ranges (local network)",
                    host="*",
                )

    async def test_es(self):
        i = await self.elasticsearch.info()
        es_major = int(i["version"]["number"].split(".")[0])
        assert es_major >= 7, "Blocky/4 requires ElasticSearch 7.x or higher"
