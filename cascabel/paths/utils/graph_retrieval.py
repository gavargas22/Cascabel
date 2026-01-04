"""
Graph retrieval utilities for downloading and caching OSM road networks.

This module provides functions to download road network graphs from OpenStreetMap
for specified bounding boxes and cache them as GraphML files for faster subsequent access.
"""

import osmnx as ox
import networkx as nx
import json
from pathlib import Path
from typing import Dict, Optional, Tuple

bounding_boxes_path = Path(__file__).parent.parent / "bounding_boxes.json"


def load_bounding_boxes() -> Dict[str, Tuple[float, float, float, float]]:
    """
    Load bounding boxes from the JSON configuration file.

    Returns:
        Dictionary mapping area names to bounding box coordinates (west, south, east, north)
    """
    with open(bounding_boxes_path, 'r') as f:
        data = json.load(f)
        # Extract just the bounding_box from each crossing config
        return {k: tuple(v['bounding_box']) for k, v in data.items()}


def retrieve_graph(
    area_name: str,
    bbox: Tuple[float, float, float, float],
    network_type: str = 'drive',
    custom_filter: Optional[str] = None,
    simplify: bool = True,
    retain_all: bool = False
) -> nx.MultiDiGraph:
    """
    Retrieve road network graph from OpenStreetMap for a given bounding box.

    Args:
        area_name: Name of the area (for logging purposes)
        bbox: Bounding box as (west, south, east, north) in degrees
        network_type: Type of street network to get ('drive', 'walk', 'bike', 'all')
        custom_filter: Custom OSM filter string (overrides network_type if provided)
        simplify: If True, simplify graph topology
        retain_all: If True, retain all nodes even if not part of the main graph

    Returns:
        NetworkX MultiDiGraph representing the road network
    """
    print(f"Retrieving graph for {area_name}...")
    print(f"  Bounding box: {bbox}")
    print(f"  Network type: {network_type}")

    graph = ox.graph.graph_from_bbox(
        bbox=bbox,
        network_type=network_type,
        custom_filter=custom_filter,
        simplify=simplify,
        retain_all=retain_all
    )

    print(f"  Retrieved {len(graph.nodes)} nodes and {len(graph.edges)} edges")
    return graph


def save_graph(
    graph: nx.MultiDiGraph,
    area_name: str,
    output_dir: Optional[Path] = None
) -> Path:
    """
    Save a graph to GraphML format.

    Args:
        graph: NetworkX graph to save
        area_name: Name of the area (used in filename)
        output_dir: Directory to save the file (defaults to bounding_boxes parent dir)

    Returns:
        Path to the saved GraphML file
    """
    if output_dir is None:
        output_dir = bounding_boxes_path.parent

    filepath = output_dir / f"{area_name}_graph.graphml"
    ox.save_graphml(graph, filepath=filepath)
    print(f"  Saved graph to {filepath}")
    return filepath


def retrieve_and_cache_graph(
    area_name: str,
    bbox: Tuple[float, float, float, float],
    network_type: str = 'drive',
    custom_filter: Optional[str] = None,
    force_download: bool = False
) -> nx.MultiDiGraph:
    """
    Retrieve a graph and cache it, or load from cache if it exists.

    Args:
        area_name: Name of the area
        bbox: Bounding box as (west, south, east, north)
        network_type: Type of street network to get
        custom_filter: Custom OSM filter string
        force_download: If True, download even if cache exists

    Returns:
        NetworkX MultiDiGraph
    """
    cache_path = bounding_boxes_path.parent / f"{area_name}_graph.graphml"

    if cache_path.exists() and not force_download:
        print(f"Loading cached graph for {area_name} from {cache_path}")
        return ox.load_graphml(filepath=cache_path)

    graph = retrieve_graph(area_name, bbox, network_type, custom_filter)
    save_graph(graph, area_name)
    return graph


def retrieve_all_graphs(
    network_type: str = 'drive',
    force_download: bool = False
) -> Dict[str, nx.MultiDiGraph]:
    """
    Retrieve and cache graphs for all areas defined in bounding_boxes.json.

    Args:
        network_type: Type of street network to get ('drive', 'walk', 'bike', 'all')
        force_download: If True, re-download even if cache exists

    Returns:
        Dictionary mapping area names to their graphs
    """
    bounding_boxes = load_bounding_boxes()
    graphs = {}

    print(f"Retrieving graphs for {len(bounding_boxes)} area(s)...")
    print("=" * 60)

    for area_name, bbox in bounding_boxes.items():
        graphs[area_name] = retrieve_and_cache_graph(
            area_name,
            tuple(bbox),
            network_type=network_type,
            force_download=force_download
        )
        print("=" * 60)

    print(f"\nCompleted! Retrieved {len(graphs)} graph(s).")
    return graphs


if __name__ == "__main__":
    # When run as a script, retrieve and cache all graphs
    import argparse

    parser = argparse.ArgumentParser(
        description="Retrieve and cache OSM road network graphs for defined bounding boxes"
    )
    parser.add_argument(
        "--network-type",
        default="drive",
        choices=["drive", "walk", "bike", "all"],
        help="Type of street network to retrieve (default: drive)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if cached graphs exist"
    )
    parser.add_argument(
        "--area",
        type=str,
        help="Only retrieve graph for specific area (default: all areas)"
    )

    args = parser.parse_args()

    if args.area:
        # Retrieve single area
        bounding_boxes = load_bounding_boxes()
        if args.area not in bounding_boxes:
            print(f"Error: Area '{args.area}' not found in bounding_boxes.json")
            print(f"Available areas: {', '.join(bounding_boxes.keys())}")
            exit(1)

        retrieve_and_cache_graph(
            args.area,
            tuple(bounding_boxes[args.area]),
            network_type=args.network_type,
            force_download=args.force
        )
    else:
        # Retrieve all areas
        retrieve_all_graphs(
            network_type=args.network_type,
            force_download=args.force
        )