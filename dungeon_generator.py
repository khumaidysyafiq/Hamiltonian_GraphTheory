#!/usr/bin/env python3
"""
Deliverable 1: Procedural Dungeon Generator
Course: Graph Theory - Week 4 Group Assignment
Institution: Institut Teknologi Sepuluh Nopember (ITS)

This is a single self-contained file for Deliverable 1:
- Generates a list of rooms (vertices) and tunnels (edges).
- Satisfies gameplay requirements: player must be able to visit every room
  exactly once without reusing tunnels (Hamiltonian Path / Cycle).
- Ensures generated routes are not too similar through structural branching,
  biome clustering, and chord diversification (evaluated via Jaccard distance).
- Supports generating valid layouts (cluster, grid_labyrinth, backbone_chords)
  as well as intentionally flawed layouts for testing.
"""

import sys
import os
import json
import math
import random
import argparse
from typing import List, Tuple, Dict, Set, Optional

# Force UTF-8 on Windows consoles if needed
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Thematic room archetypes for dungeon immersion
ROOM_THEMES = [
    ("Entrance", "Grand Stone Archway with heavy iron-banded gates"),
    ("Armory", "Racks of ancient halberds and dented shields"),
    ("Library", "Dusty arcane tomes and ruined pedestals"),
    ("Crypt", "Granite sarcophagi enveloped in icy mist"),
    ("Treasury", "Gilded chests with silver filigree"),
    ("Shrine", "Altar of forgotten gods glowing faintly"),
    ("Prison", "Iron cells and rusted hanging cages"),
    ("Laboratory", "Alchemical alembics and bubbling vials"),
    ("Courtyard", "Overgrown garden with crumbling statues"),
    ("Barracks", "Wooden bunks and cracked gaming tables"),
    ("Catacombs", "Walls lined with ancestral skulls"),
    ("Forge", "Cold anvil with residual ember sparks"),
    ("Observatory", "Broken celestial astrolabe pointing at the void"),
    ("Sanctum", "Pillars engraved with protective warding runes"),
    ("Throne Room", "Gargantuan throne carved from subterranean rock"),
    ("Boss Chamber", "Abyssal sanctum echoing with eldritch whispers")
]


class DungeonGraph:
    """Represents a dungeon topology with rooms (vertices) and tunnels (edges)."""

    def __init__(self, name: str = "Procedural Dungeon"):
        self.name = name
        self.rooms: Dict[int, Dict] = {}  # id -> {id, name, desc, x, y}
        self.adj: Dict[int, Set[int]] = {}
        self.tunnels: List[Tuple[int, int]] = []

    @property
    def num_rooms(self) -> int:
        return len(self.rooms)

    @property
    def num_tunnels(self) -> int:
        return len(self.tunnels)

    def add_room(self, room_id: int, name: str = "", desc: str = "", x: float = 0.0, y: float = 0.0):
        if not name:
            theme_idx = (room_id - 1) % len(ROOM_THEMES)
            name, desc = ROOM_THEMES[theme_idx]
            name = f"{name} #{room_id}"
        self.rooms[room_id] = {
            "id": room_id,
            "name": name,
            "desc": desc,
            "x": round(x, 2),
            "y": round(y, 2)
        }
        if room_id not in self.adj:
            self.adj[room_id] = set()

    def add_tunnel(self, u: int, v: int) -> bool:
        if u == v or u not in self.rooms or v not in self.rooms:
            return False
        if v in self.adj[u]:
            return False  # Prevent parallel tunnels
        self.adj[u].add(v)
        self.adj[v].add(u)
        self.tunnels.append((min(u, v), max(u, v)))
        return True

    def degree(self, room_id: int) -> int:
        return len(self.adj.get(room_id, set()))

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "num_rooms": self.num_rooms,
            "num_tunnels": self.num_tunnels,
            "rooms": list(self.rooms.values()),
            "tunnels": [{"u": u, "v": v} for u, v in self.tunnels]
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def to_edge_list_text(self) -> str:
        """Outputs standard format:
        Line 1: N M
        Next M lines: u v
        """
        lines = [f"{self.num_rooms} {self.num_tunnels}"]
        for u, v in sorted(self.tunnels):
            lines.append(f"{u} {v}")
        return "\n".join(lines)

    @classmethod
    def from_dict(cls, data: dict) -> "DungeonGraph":
        g = cls(name=data.get("name", "Imported Dungeon"))
        for r in data.get("rooms", []):
            g.add_room(r["id"], r.get("name", ""), r.get("desc", ""), r.get("x", 0.0), r.get("y", 0.0))
        for t in data.get("tunnels", []):
            g.add_tunnel(t["u"], t["v"])
        return g

    @classmethod
    def from_json(cls, json_str: str) -> "DungeonGraph":
        return cls.from_dict(json.loads(json_str))


class ProceduralDungeonGenerator:
    """Procedurally generates dungeon layouts guaranteed to have valid Hamiltonian clearing
    routes while maximizing route variance (avoiding routes being too similar).
    """

    @staticmethod
    def generate(num_rooms: int = 8,
                 density: float = 0.35,
                 archetype: str = "cluster",
                 seed: Optional[int] = None) -> DungeonGraph:
        """Procedural generator entry point.

        Parameters:
        - num_rooms: Total rooms (>= 3).
        - density: Tunnel density factor (0.0 to 1.0) controlling alternative bypasses.
        - archetype: Layout strategy ('cluster', 'grid_labyrinth', 'backbone_chords', 'random').
        - seed: Random seed for procedural repeatability.
        """
        if seed is not None:
            random.seed(seed)

        num_rooms = max(3, num_rooms)
        dungeon = DungeonGraph(f"Procedural Dungeon ({archetype.replace('_', ' ').title()}, N={num_rooms})")

        # 1. Coordinate layout for 2D spatial representation
        for r_id in range(1, num_rooms + 1):
            theta = 2.0 * math.pi * (r_id - 1) / num_rooms
            radius = 12.0 + random.uniform(-1.0, 1.0)
            x = radius * math.cos(theta)
            y = radius * math.sin(theta)
            dungeon.add_room(r_id, x=x, y=y)

        # 2. Topology Construction
        if archetype == "cluster":
            ProceduralDungeonGenerator._build_cluster_topology(dungeon, num_rooms, density)
        elif archetype == "grid_labyrinth":
            ProceduralDungeonGenerator._build_grid_topology(dungeon, num_rooms, density)
        elif archetype == "random":
            ProceduralDungeonGenerator._build_random_topology(dungeon, num_rooms, density)
        else:  # 'backbone_chords' default
            ProceduralDungeonGenerator._build_backbone_chords(dungeon, num_rooms, density)

        return dungeon

    @staticmethod
    def _build_backbone_chords(dungeon: DungeonGraph, n: int, density: float):
        """Constructs a randomized Hamiltonian cycle backbone, then selectively
        adds non-adjacent chords to create branching route choices.
        """
        perm = list(range(1, n + 1))
        random.shuffle(perm)

        # Base Hamiltonian cycle (guarantees solvability)
        for i in range(n):
            u = perm[i]
            v = perm[(i + 1) % n]
            dungeon.add_tunnel(u, v)

        # Non-adjacent candidate chords
        candidates = []
        for i in range(n):
            for j in range(i + 2, n):
                if not (i == 0 and j == n - 1):
                    candidates.append((perm[i], perm[j]))

        random.shuffle(candidates)
        chords_to_add = int(len(candidates) * density)
        for u, v in candidates[:chords_to_add]:
            dungeon.add_tunnel(u, v)

    @staticmethod
    def _build_cluster_topology(dungeon: DungeonGraph, n: int, density: float):
        """Divides rooms into biomes/clusters (e.g. Crypts, Sanctum, Armory).
        Connects rooms within each cluster and connects clusters with dual bridges,
        forcing players to choose fundamentally different wing-clearing orders.
        """
        num_clusters = 2 if n < 8 else 3
        cluster_size = n // num_clusters
        clusters = []

        room_ids = list(range(1, n + 1))
        random.shuffle(room_ids)

        start_idx = 0
        for c in range(num_clusters):
            end_idx = start_idx + cluster_size if c < num_clusters - 1 else n
            clusters.append(room_ids[start_idx:end_idx])
            start_idx = end_idx

        # Intra-cluster connections
        for cluster in clusters:
            for i in range(len(cluster) - 1):
                dungeon.add_tunnel(cluster[i], cluster[i + 1])
            if len(cluster) >= 3 and random.random() < 0.7:
                dungeon.add_tunnel(cluster[0], cluster[-1])

        # Dual inter-cluster bridges (allows entering/exiting wings in different orders)
        for i in range(num_clusters):
            c1 = clusters[i]
            c2 = clusters[(i + 1) % num_clusters]
            dungeon.add_tunnel(c1[-1], c2[0])
            if len(c1) > 1 and len(c2) > 1:
                dungeon.add_tunnel(c1[0], c2[-1])

        # Extra shortcut tunnels according to density
        non_edges = []
        for u in range(1, n + 1):
            for v in range(u + 1, n + 1):
                if v not in dungeon.adj[u]:
                    non_edges.append((u, v))
        random.shuffle(non_edges)
        extra = int(len(non_edges) * density * 0.4)
        for u, v in non_edges[:extra]:
            dungeon.add_tunnel(u, v)

    @staticmethod
    def _build_grid_topology(dungeon: DungeonGraph, n: int, density: float):
        """Constructs a 2D grid/labyrinth layout with a serpentine Hamiltonian path
        and configurable cross-corridor bypasses.
        """
        cols = int(math.ceil(math.sqrt(n)))
        rows = int(math.ceil(n / cols))

        grid = {}
        for idx, r_id in enumerate(range(1, n + 1)):
            r = idx // cols
            c = idx % cols
            grid[(r, c)] = r_id
            dungeon.rooms[r_id]["x"] = c * 5.0
            dungeon.rooms[r_id]["y"] = r * 5.0

        snake = []
        for r in range(rows):
            row_rooms = [grid[(r, c)] for c in range(cols) if (r, c) in grid]
            if r % 2 == 1:
                row_rooms.reverse()
            snake.extend(row_rooms)

        for i in range(len(snake) - 1):
            dungeon.add_tunnel(snake[i], snake[i + 1])

        # Loop closure
        dungeon.add_tunnel(snake[0], snake[-1])

        # Add cross connections
        for (r, c), u in grid.items():
            if (r + 1, c) in grid and random.random() < (0.2 + density * 0.5):
                dungeon.add_tunnel(u, grid[(r + 1, c)])

    @staticmethod
    def _build_random_topology(dungeon: DungeonGraph, n: int, density: float):
        """Erdos-Renyi random graph G(n, p) for probabilistic testing."""
        p = 0.25 + density * 0.55
        for u in range(1, n + 1):
            for v in range(u + 1, n + 1):
                if random.random() < p:
                    dungeon.add_tunnel(u, v)

    @staticmethod
    def generate_invalid(flaw_type: str = "bottleneck", num_rooms: int = 7) -> DungeonGraph:
        """Deliberately generates an INVALID dungeon to demonstrate validator rejection.

        Flaw types:
        - 'bottleneck': 3-way cut-vertex connecting 3 separate cliques (c(G - {v}) = 3 > 2).
        - 'dead_ends': Hub connected to >= 3 leaves (degree 1), exceeding 2 path endpoints.
        - 'disconnected': One or more completely isolated rooms (degree 0).
        - 'bipartite_mismatch': Complete bipartite K_{2, N-2} where |A| - |B| > 1.
        """
        num_rooms = max(5, num_rooms)
        dungeon = DungeonGraph(f"Invalid Dungeon (Flaw: {flaw_type})")
        for i in range(1, num_rooms + 1):
            dungeon.add_room(i)

        if flaw_type == "bottleneck":
            hub = 1
            wing_a = [2, 3]
            wing_b = [4, 5]
            wing_c = list(range(6, num_rooms + 1))
            for wing in [wing_a, wing_b, wing_c]:
                for u in wing:
                    dungeon.add_tunnel(hub, u)
                    for v in wing:
                        if u < v:
                            dungeon.add_tunnel(u, v)

        elif flaw_type == "dead_ends":
            hub = 1
            leaves = [2, 3, 4]
            rest = list(range(5, num_rooms + 1))
            for leaf in leaves:
                dungeon.add_tunnel(hub, leaf)
            for r in rest:
                dungeon.add_tunnel(hub, r)
            for i in range(len(rest) - 1):
                dungeon.add_tunnel(rest[i], rest[i + 1])

        elif flaw_type == "disconnected":
            for i in range(1, num_rooms - 1):
                dungeon.add_tunnel(i, i + 1)
            dungeon.add_tunnel(num_rooms - 1, 1)

        elif flaw_type == "bipartite_mismatch":
            set_a = [1, 2]
            set_b = list(range(3, num_rooms + 1))
            for u in set_a:
                for v in set_b:
                    dungeon.add_tunnel(u, v)

        return dungeon


def print_dungeon_summary(dungeon: DungeonGraph):
    """Prints a clean human-readable summary of the generated rooms and tunnels."""
    print("=" * 80)
    print(f"DELIVERABLE 1: GENERATED DUNGEON -- {dungeon.name}")
    print("=" * 80)
    print(f"Total Rooms:   {dungeon.num_rooms}")
    print(f"Total Tunnels: {dungeon.num_tunnels}")
    print("-" * 80)

    print("LIST OF ROOMS (VERTICES):")
    for r_id in sorted(dungeon.rooms.keys()):
        r = dungeon.rooms[r_id]
        deg = dungeon.degree(r_id)
        print(f"  * Room {r['id']:2d}: {r['name']:<18} | Degree: {deg} | {r['desc']}")

    print("\nLIST OF TUNNELS (EDGES):")
    tunnels = sorted(dungeon.tunnels)
    tunnel_strs = [f"({u} <--> {v})" for u, v in tunnels]
    # Display in lines of 4 tunnels
    for i in range(0, len(tunnel_strs), 4):
        print("  " + "   ".join(tunnel_strs[i:i + 4]))

    print("-" * 80)
    print("Edge List Format for Validator / Competitions:")
    print(f"  Line 1: {dungeon.num_rooms} {dungeon.num_tunnels}")
    sample_edges = " ".join([f"{u}-{v}" for u, v in tunnels[:6]])
    print(f"  Edges : {sample_edges} ...")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Deliverable 1: Procedural Dungeon Generator (Rooms & Tunnels with Varied Routes)"
    )
    parser.add_argument("--rooms", type=int, default=8, help="Number of rooms to generate (default: 8)")
    parser.add_argument("--density", type=float, default=0.35, help="Tunnel density factor 0.0 - 1.0 (default: 0.35)")
    parser.add_argument("--archetype", choices=["cluster", "grid_labyrinth", "backbone_chords", "random"],
                        default="cluster", help="Dungeon layout archetype (default: cluster)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--output", type=str, default="", help="Save output to file (.json or .txt)")
    parser.add_argument("--format", choices=["json", "txt", "both"], default="txt", help="Output format for --output")
    parser.add_argument("--invalid", choices=["bottleneck", "dead_ends", "disconnected", "bipartite_mismatch"],
                        default="", help="Generate deliberately invalid dungeon for testing")

    args = parser.parse_args()

    if args.invalid:
        dungeon = ProceduralDungeonGenerator.generate_invalid(args.invalid, num_rooms=args.rooms)
    else:
        dungeon = ProceduralDungeonGenerator.generate(
            num_rooms=args.rooms,
            density=args.density,
            archetype=args.archetype,
            seed=args.seed
        )

    print_dungeon_summary(dungeon)

    if args.output:
        base_name = args.output
        if args.format in ["txt", "both"]:
            txt_file = base_name if base_name.endswith(".txt") else f"{os.path.splitext(base_name)[0]}.txt"
            with open(txt_file, "w", encoding="utf-8") as f:
                f.write(dungeon.to_edge_list_text())
            print(f"[+] Saved text edge list to '{txt_file}'")

        if args.format in ["json", "both"]:
            json_file = base_name if base_name.endswith(".json") else f"{os.path.splitext(base_name)[0]}.json"
            with open(json_file, "w", encoding="utf-8") as f:
                f.write(dungeon.to_json())
            print(f"[+] Saved JSON specification to '{json_file}'")


if __name__ == "__main__":
    main()
