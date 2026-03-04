#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LinkValidator - Validation system for cross-shard references
Migrated from link_validator.py (buralux/dsm).
"""


class LinkValidator:
    def __init__(self, shards_directory="memory/shards"):
        self.shards_dir = shards_directory
        self.allowed_shards = [
            "shard_projects",
            "shard_insights",
            "shard_people",
            "shard_technical",
            "shard_strategy"
        ]
        self.max_refs_per_transaction = 3
        self.max_cycle_depth = 2

    def validate_link(self, from_shard_id, to_shard_id):
        """Validates a cross-shard reference. Returns (is_valid, message)."""
        if from_shard_id not in self.allowed_shards:
            return False, f"Source shard '{from_shard_id}' is not allowed"
        if to_shard_id not in self.allowed_shards:
            return False, f"Target shard '{to_shard_id}' does not exist"
        if from_shard_id == to_shard_id:
            return False, "Self-reference not allowed"
        cycle = self._would_create_cycle(from_shard_id, to_shard_id, visited=set(), depth=0)
        if cycle.get("cycle", False):
            return False, f"Reference would create a cycle (depth: {cycle['depth']})"
        return True, "Valid cross-shard reference"

    def _would_create_cycle(self, from_shard, to_shard, visited, depth):
        if depth > self.max_cycle_depth:
            return {"cycle": False, "depth": depth}
        if to_shard in visited:
            return {"cycle": True, "depth": depth}
        visited.add(to_shard)
        return {"cycle": False, "depth": depth + 1}
