"""
RSS Feed Integration for CBP Wait Time Data
============================================

Fetches and parses CBP RSS feeds for real-time border wait time data.
Used to inform time-varying arrival and service rates in the simulation.
"""

import feedparser
from datetime import datetime, timedelta
from typing import List, Optional
from dataclasses import dataclass
import re


@dataclass
class BorderWaitTime:
    """Represents a border wait time entry from CBP RSS feed."""

    port_name: str
    border_name: str
    crossing_name: str
    port_number: str
    border: str  # 'US-Mexico Border', 'US-Canada Border'
    direction: str  # 'northbound', 'southbound'
    date: datetime
    delay_minutes: int
    lanes_open: int
    update_time: datetime

    @property
    def is_us_mexico_border(self) -> bool:
        """Check if this is US-Mexico border."""
        return "mexico" in self.border.lower()

    @property
    def is_southbound(self) -> bool:
        """Check if this is southbound traffic."""
        return self.direction.lower() == "southbound"


class CBPFeedParser:
    """
    Parser for CBP (Customs and Border Protection) RSS feeds.

    Fetches real-time border wait time data from CBP's RSS feeds.
    """

    # CBP RSS feed URLs
    FEED_URLS = {
        "us_mexico_border": "https://bwt.cbp.gov/api/bwtRss/rss",
        "us_canada_border": "https://bwt.cbp.gov/api/bwtRss/rss/canada",
    }

    def __init__(self, cache_duration_minutes: int = 15):
        """
        Initialize the CBP feed parser.

        Args:
            cache_duration_minutes: How long to cache feed data
        """
        self.cache_duration = timedelta(minutes=cache_duration_minutes)
        self._last_fetch = {}
        self._cached_data = {}

    def fetch_border_wait_times(
        self, border: str = "us_mexico"
    ) -> List[BorderWaitTime]:
        """
        Fetch current border wait times from CBP RSS feed.

        Args:
            border: 'us_mexico' or 'us_canada'

        Returns:
            List of BorderWaitTime objects
        """
        # Map short names to feed keys
        border_map = {"us_mexico": "us_mexico_border", "us_canada": "us_canada_border"}

        feed_key = border_map.get(border, border)
        if feed_key not in self.FEED_URLS:
            raise ValueError(
                f"Unknown border: {border}. Must be 'us_mexico' or 'us_canada'"
            )

        # Check cache
        now = datetime.now()
        if (
            feed_key in self._last_fetch
            and now - self._last_fetch[feed_key] < self.cache_duration
            and feed_key in self._cached_data
        ):
            return self._cached_data[feed_key]

        try:
            # Fetch RSS feed
            url = self.FEED_URLS[feed_key]
            feed = feedparser.parse(url)

            wait_times = []
            for entry in feed.entries:
                wait_time = self._parse_feed_entry(entry)
                if wait_time:
                    wait_times.append(wait_time)

            # Cache the results
            self._last_fetch[feed_key] = now
            self._cached_data[feed_key] = wait_times

            return wait_times

        except Exception as e:
            print(f"Error fetching CBP feed for {border}: {e}")
            # Return cached data if available
            if feed_key in self._cached_data:
                return self._cached_data[feed_key]
            return []

    def _parse_feed_entry(self, entry) -> Optional[BorderWaitTime]:
        """
        Parse a single RSS feed entry into a BorderWaitTime object.

        Args:
            entry: feedparser entry object

        Returns:
            BorderWaitTime object or None if parsing fails
        """
        try:
            # Extract data from entry title and description
            title = entry.title
            description = entry.get("description", "")

            # Parse title format: "Port Name - Border Name - Direction"
            # Example: "San Ysidro - US-Mexico Border - southbound"
            title_parts = [part.strip() for part in title.split("-")]
            if len(title_parts) < 3:
                return None

            port_name = title_parts[0]
            border_name = title_parts[1]
            direction = title_parts[2].lower()

            # Extract port number and other details from description
            port_number = self._extract_port_number(description)
            delay_minutes = self._extract_delay(description)
            lanes_open = self._extract_lanes(description)

            # Parse update time
            update_time = self._parse_update_time(entry)

            return BorderWaitTime(
                port_name=port_name,
                border_name=border_name,
                crossing_name=port_name,  # Assuming same as port name
                port_number=port_number,
                border=border_name,
                direction=direction,
                date=update_time,
                delay_minutes=delay_minutes,
                lanes_open=lanes_open,
                update_time=update_time,
            )

        except Exception as e:
            print(f"Error parsing feed entry '{entry.title}': {e}")
            return None

    def _extract_port_number(self, description: str) -> str:
        """Extract port number from description."""
        # Look for patterns like "Port: 250401" or similar
        match = re.search(r"Port:\s*(\d+)", description, re.IGNORECASE)
        return match.group(1) if match else ""

    def _extract_delay(self, description: str) -> int:
        """Extract delay in minutes from description."""
        # Look for patterns like "Delay: 30 minutes" or "30 minute delay"
        match = re.search(r"Delay:\s*(\d+)\s*minute", description, re.IGNORECASE)
        if match:
            return int(match.group(1))

        # Try alternative patterns
        match = re.search(r"(\d+)\s*minute.*delay", description, re.IGNORECASE)
        if match:
            return int(match.group(1))

        return 0  # No delay or unknown

    def _extract_lanes(self, description: str) -> int:
        """Extract number of lanes open from description."""
        # Look for patterns like "Lanes: 5" or "5 lanes open"
        match = re.search(r"Lanes?:\s*(\d+)", description, re.IGNORECASE)
        if match:
            return int(match.group(1))

        match = re.search(r"(\d+)\s*lane", description, re.IGNORECASE)
        if match:
            return int(match.group(1))

        return 1  # Default to 1 lane

    def _parse_update_time(self, entry) -> datetime:
        """Parse the update time from RSS entry."""
        # Try published_parsed first
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            return datetime(*entry.published_parsed[:6])

        # Try updated_parsed
        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            return datetime(*entry.updated_parsed[:6])

        # Fallback to current time
        return datetime.now()

    def get_average_wait_time(
        self, border: str = "us_mexico", direction: str = "southbound"
    ) -> float:
        """
        Get average wait time for a specific border and direction.

        Args:
            border: 'us_mexico' or 'us_canada'
            direction: 'northbound' or 'southbound'

        Returns:
            Average delay in minutes
        """
        wait_times = self.fetch_border_wait_times(border)
        relevant_times = [
            wt.delay_minutes
            for wt in wait_times
            if wt.direction.lower() == direction.lower()
        ]

        if not relevant_times:
            return 0.0

        return sum(relevant_times) / len(relevant_times)

    def get_port_wait_time(
        self, port_name: str, border: str = "us_mexico"
    ) -> Optional[int]:
        """
        Get wait time for a specific port.

        Args:
            port_name: Name of the border port
            border: 'us_mexico' or 'us_canada'

        Returns:
            Delay in minutes or None if not found
        """
        wait_times = self.fetch_border_wait_times(border)
        for wt in wait_times:
            if wt.port_name.lower() == port_name.lower():
                return wt.delay_minutes
        return None


# Global instance for easy access
cbp_parser = CBPFeedParser()
