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
import operator

""" block/allow list viewing endpoint for Blocky/4"""


async def process(state: plugins.configuration.BlockyConfiguration, request, formdata: dict) -> dict:
    short = formdata.get('short', False)
    allow_items = [x for x in state.allow_list]
    block_items = [x for x in state.block_list]
    total_blocks = len(block_items)
    total_allows = len(allow_items)
    if short:  # For not showing all 27482487 items, for front page
        if short in ["block", "all", "true"]:
            block_items = sorted(block_items, reverse=True, key=operator.itemgetter("timestamp"))[:25]
        if short in ["allow", "all", "true"]:
            allow_items = sorted(allow_items, reverse=True, key=operator.itemgetter("timestamp"))[:25]
    return {
        "total_block": total_blocks,
        "total_allow": total_allows,
        "allow": allow_items,
        "block": block_items,
    }


def register(config: plugins.configuration.BlockyConfiguration):
    return ahapi.endpoint(process)
