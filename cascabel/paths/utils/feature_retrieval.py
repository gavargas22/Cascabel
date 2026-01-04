"""
Feature retrieval utilities for downloading and caching OSM features.

This module provides functions to download geographic features (roads, buildings, etc.)
from OpenStreetMap for specified bounding boxes and cache them as pickle files.
"""

import osmnx as ox
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import geopandas as gpd
import pandas as pd

bounding_boxes_path = Path(__file__).parent.parent / "bounding_boxes.json"


def load_bounding_boxes() -> Dict[str, Tuple[float, float, float, float]]:
    """
    Load bounding boxes from the JSON configuration file.

    Returns:
        Dictionary mapping area names to bounding box coordinates (west, south, east, north)
    """
    with open(bounding_boxes_path, 'r') as f:
        data = json.load(f)
        bboxes = {}
        
        for name in data.keys():
            bboxes[name] = data[name]["bounding_box"]

        return {k: tuple(v) for k, v in bboxes.items()}

def retrieve_features(
    area_name: str,
    bbox: Tuple[float, float, float, float],
    tags: Dict[str, Any]
) -> gpd.GeoDataFrame:
    """
    Retrieve geographic features from OpenStreetMap for a given bounding box.

    Args:
        area_name: Name of the area (for logging purposes)
        bbox: Bounding box as (west, south, east, north) in degrees
        tags: Dictionary of OSM tags to filter features
              Example: {'highway': ['residential', 'primary'], 'amenity': True}

    Returns:
        GeoDataFrame containing the retrieved features
    """
    print(f"Retrieving features for {area_name}...")
    print(f"  Bounding box: {bbox}")
    print(f"  Tags: {tags}")

    features_gdf = ox.features.features_from_bbox(
        bbox=bbox,
        tags=tags
    )

    print(f"  Retrieved {len(features_gdf)} features")
    return features_gdf


def save_features(
    features_gdf: gpd.GeoDataFrame,
    area_name: str,
    output_dir: Optional[Path] = None
) -> Path:
    """
    Save features to a pickle file.

    Args:
        features_gdf: GeoDataFrame to save
        area_name: Name of the area (used in filename)
        output_dir: Directory to save the file (defaults to bounding_boxes parent dir)

    Returns:
        Path to the saved pickle file
    """
    if output_dir is None:
        output_dir = bounding_boxes_path.parent

    filepath = output_dir / f"{area_name}_features.pkl"
    features_gdf.to_pickle(filepath)
    print(f"  Saved features to {filepath}")
    return filepath


def retrieve_and_cache_features(
    area_name: str,
    bbox: Tuple[float, float, float, float],
    tags: Dict[str, Any],
    force_download: bool = False
) -> gpd.GeoDataFrame:
    """
    Retrieve features and cache them, or load from cache if it exists.

    Args:
        area_name: Name of the area
        bbox: Bounding box as (west, south, east, north)
        tags: Dictionary of OSM tags to filter features
        force_download: If True, download even if cache exists

    Returns:
        GeoDataFrame containing the features
    """
    cache_path = bounding_boxes_path.parent / f"{area_name}_features.pkl"

    if cache_path.exists() and not force_download:
        print(f"Loading cached features for {area_name} from {cache_path}")
        return pd.read_pickle(cache_path)

    features_gdf = retrieve_features(area_name, bbox, tags)
    save_features(features_gdf, area_name)
    return features_gdf


def retrieve_all_features(
    tags: Optional[Dict[str, Any]] = None,
    force_download: bool = False
) -> Dict[str, gpd.GeoDataFrame]:
    """
    Retrieve and cache features for all areas defined in bounding_boxes.json.

    Args:
        tags: Dictionary of OSM tags to filter features. If None, uses default highway tags.
        force_download: If True, re-download even if cache exists

    Returns:
        Dictionary mapping area names to their feature GeoDataFrames
    """
    if tags is None:
        tags = {'highway': ['residential', 'primary', 'secondary', 'trunk']}

    bounding_boxes = load_bounding_boxes()
    features = {}

    print(f"Retrieving features for {len(bounding_boxes)} area(s)...")
    print("=" * 60)

    for area_name, bbox in bounding_boxes.items():
        features[area_name] = retrieve_and_cache_features(
            area_name,
            bbox,
            tags=tags,
            force_download=force_download
        )
        print("=" * 60)

    print(f"\nCompleted! Retrieved features for {len(features)} area(s).")
    return features


if __name__ == "__main__":
    # When run as a script, retrieve and cache all features
    import argparse

    parser = argparse.ArgumentParser(
        description="Retrieve and cache OSM features for defined bounding boxes"
    )
    parser.add_argument(
        "--tags",
        type=str,
        help="JSON string of tags to filter (default: highway tags)",
        default=None
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if cached features exist"
    )
    parser.add_argument(
        "--area",
        type=str,
        help="Only retrieve features for specific area (default: all areas)"
    )

    args = parser.parse_args()

    # Parse tags if provided
    if args.tags:
        tags = json.loads(args.tags)
    else:
        tags = {
            'highway': [
                'residential', 'primary', 'secondary', 'trunk'
            ],
            "border_type": ["nation"]
        }

    if args.area:
        # Retrieve single area
        bounding_boxes = load_bounding_boxes()
        if args.area not in bounding_boxes:
            print(f"Error: Area '{args.area}' not found in bounding_boxes.json")
            print(f"Available areas: {', '.join(bounding_boxes.keys())}")
            exit(1)

        retrieve_and_cache_features(
            args.area,
            bounding_boxes[args.area],
            tags=tags,
            force_download=args.force
        )
    else:
        # Retrieve all areas
        retrieve_all_features(
            tags=tags,
            force_download=args.force
        )