"""Connectors: pluggable sources with fixture-backed implementations.

The Connector protocol is what a real deployment would implement against
Gmail/Calendar/Slack APIs. Fixtures stand in so the loop is testable today;
swapping in live connectors changes no agent code.
"""
import json
from abc import ABC, abstractmethod


class Connector(ABC):
    @abstractmethod
    def fetch_new(self):
        """Return a list of new items since last fetch."""


class FixtureConnector(Connector):
    def __init__(self, path, cursor=0):
        self.path = path
        with open(path) as f:
            self.items = json.load(f)
        self.cursor = cursor

    def fetch_new(self):
        new = self.items[self.cursor:]
        self.cursor = len(self.items)
        return new


def load_fixtures(base):
    return {
        "inbox": FixtureConnector(f"{base}/inbox.json"),
        "calendar": FixtureConnector(f"{base}/calendar.json"),
        "slack": FixtureConnector(f"{base}/slack.json"),
    }
