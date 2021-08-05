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

# Definitions for SQLite tables used in Blocky/4

CREATE_DB_RULES = """
CREATE TABLE "rules" (
	"id"	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	"description"	TEXT NOT NULL,
	"aggtype"	TEXT NOT NULL,
	"limit"	INTEGER NOT NULL,
	"duration"	TEXT NOT NULL,
	"filters"	TEXT
);
"""

CREATE_DB_LISTS = """
CREATE TABLE "lists" (
	"id"	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	"type" TEXT NOT NULL,
	"ip"	TEXT NOT NULL,
	"reason"	TEXT NOT NULL,
	"timestamp"	INTEGER NOT NULL,
	"expires"	INTEGER NOT NULL,
	"host"	TEXT NOT NULL
);
"""

CREATE_DB_AUDIT = """
CREATE TABLE "auditlog" (
	"id"	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	"ip"	TEXT NOT NULL,
	"event"	TEXT NOT NULL,
	"timestamp"	INTEGER NOT NULL
);
"""

