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

# This is the main entry point for Blocky/4

import asyncio
import yaml
import plugins.configuration
import plugins.background
import ahapi


async def main(loop: asyncio.BaseEventLoop):
    yml = yaml.safe_load(open("blocky4.yaml", "r"))
    config = plugins.configuration.BlockyConfiguration(yml)
    loop.create_task(plugins.background.run(config))
    httpserver = ahapi.simple(
        static_dir="webui",
        bind_ip=config.http_ip,
        bind_port=config.http_port,
        state=config,
        max_upload=4 * 1024 * 1024,  # 4MB ≃ 20,000 iptables entries from a client
    )
    loop.create_task(httpserver.loop())
    while True:
        await asyncio.sleep(10)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))
