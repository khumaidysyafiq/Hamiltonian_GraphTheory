#!/usr/bin/env python3
"""
Deliverable 2: Dungeon Validator (Hamiltonian Tour Checker)
Course: Graph Theory - Week 4 Group Assignment
Institution: Institut Teknologi Sepuluh Nopember (ITS)

This is a single self-contained file for Deliverable 2:
- Validates whether a given dungeon allows a player to clear all rooms
  by visiting every room exactly once without reusing any tunnel.
- Evaluates lecture-based Sufficient Conditions:
  * Complete Graph check (Slide 7)
  * Dirac's Theorem: deg(v) >= n/2 for all v (Slides 8-9)
  * Ore's Theorem: deg(u) + deg(v) >= n for all non-adjacent pairs (Slides 10-11)
- Evaluates Necessary Structural Conditions for early pruning:
  * Connectedness check (c(G) = 1)
  * Dead-end leaf bound (<= 2 rooms with degree 1 for path; 0 for cycle)
  * Articulation cut-vertex bound (c(G - {v}) <= 2)
  * Bipartite partition balance (||A| - |B|| <= 1)
- Executes an exact backtracking search with Warnsdorff's heuristic.
- Outputs discovered clearing path(s), or emits:
  "STATEMENT: No valid path exists.
   The player cannot clear the entire dungeon by visiting every room exactly once
   without reusing any tunnel."
"""

import sys
import os
import json
import time
import argparse
from collections import deque, defaultdict
from typing import List, Tuple, Dict, Set, Optional

# Force UTF-8 on Windows consoles if needed
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


class DungeonGraph:
    """Represents a dungeon topology with rooms (vertices) and tunnels (edges)."""

    def __init__(self, name: str = "Imported Dungeon"):
        self.name = name
        self.rooms: Dict[int, Dict] = {}
        self.adj: Dict[int, Set[int]] = defaultdict(set)
        self.tunnels: List[Tuple[int, int]] = []

    @property
    def num_rooms(self) -> int:
        return len(self.rooms)

    @property
    def num_tunnels(self) -> int:
        return len(self.tunnels)

    def add_room(self, room_id: int, name: str = "", desc: str = "", x: float = 0.0, y: float = 0.0):
        if not name:
            name = f"Room #{room_id}"
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
            return False
        self.adj[u].add(v)
        self.adj[v].add(u)
        self.tunnels.append((min(u, v), max(u, v)))
        return True

    def degree(self, room_id: int) -> int:
        return len(self.adj[room_id])

    @classmethod
    def from_edge_list_text(cls, text: str, name: str = "Text Dungeon") -> "DungeonGraph":
        """Parses competitive edge list format:
        Line 1: N M
        Next M lines: u v
        """
        lines = [line.strip() for line in text.strip().splitlines() if line.strip() and not line.strip().startswith("#")]
        if not lines:
            return cls("Empty Dungeon")
        tokens = lines[0].split()
        n, m = int(tokens[0]), int(tokens[1])
        g = cls(f"{name} ({n} Rooms, {m} Tunnels)")
        for i in range(1, n + 1):
            g.add_room(i)
        for i in range(1, m + 1):
            if i < len(lines):
                parts = lines[i].split()
                if len(parts) >= 2:
                    u, v = int(parts[0]), int(parts[1])
                    g.add_tunnel(u, v)
        return g

    @classmethod
    def from_json(cls, json_str: str) -> "DungeonGraph":
        data = json.loads(json_str)
        g = cls(name=data.get("name", "JSON Dungeon"))
        for r in data.get("rooms", []):
            g.add_room(r["id"], r.get("name", ""), r.get("desc", ""), r.get("x", 0.0), r.get("y", 0.0))
        for t in data.get("tunnels", []):
            g.add_tunnel(t["u"], t["v"])
        return g


class DungeonValidator:
    """Validates whether a dungeon allows a player to clear all rooms exactly once
    without reusing any tunnel.
    """

    @staticmethod
    def validate(dungeon: DungeonGraph,
                 find_all_paths: bool = True,
                 max_paths_to_display: int = 5,
                 verbose: bool = True) -> Dict:
        n = dungeon.num_rooms
        m = dungeon.num_tunnels

        report = {
            "num_rooms": n,
            "num_tunnels": m,
            "is_connected": False,
            "dirac_theorem": False,
            "ore_theorem": False,
            "is_complete": False,
            "necessary_fails": [],
            "hamiltonian_path_exists": False,
            "hamiltonian_cycle_exists": False,
            "paths": [],
            "cycles": [],
            "route_diversity_score": 0.0,
            "execution_time_ms": 0.0,
            "summary_statement": ""
        }

        t_start = time.perf_counter()

        if n == 0:
            report["summary_statement"] = "No valid path exists: Dungeon contains 0 rooms."
            return report
        if n == 1:
            report["hamiltonian_path_exists"] = True
            report["paths"] = [[1]]
            report["summary_statement"] = "Valid path exists (Single room cleared immediately)."
            return report

        # 1. Connectedness Check (BFS)
        start_node = next(iter(dungeon.rooms.keys()))
        visited = set([start_node])
        queue = deque([start_node])
        while queue:
            curr = queue.popleft()
            for neighbor in dungeon.adj[curr]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        report["is_connected"] = (len(visited) == n)
        if not report["is_connected"]:
            unvisited_rooms = set(dungeon.rooms.keys()) - visited
            report["necessary_fails"].append(
                f"Graph is disconnected. Unreachable rooms from Room {start_node}: {sorted(list(unvisited_rooms))}"
            )

        # 2. Degree & Dead-End Bounds
        dead_ends = [r for r, neighbors in dungeon.adj.items() if len(neighbors) == 1]
        isolated = [r for r, neighbors in dungeon.adj.items() if len(neighbors) == 0]

        if isolated:
            report["necessary_fails"].append(f"Isolated rooms with degree 0 detected: {isolated}")

        if len(dead_ends) > 2:
            report["necessary_fails"].append(
                f"Dead-end bound violated: {len(dead_ends)} rooms have degree 1 (Rooms: {dead_ends}). "
                "A simple path has at most 2 endpoints; traversing all rooms without reuse is impossible."
            )

        # 3. Cut-Vertex Articulation Bound (c(G - {v}) <= 2)
        cut_vertices = DungeonValidator._find_cut_vertices(dungeon)
        for cv in cut_vertices:
            comp_count = DungeonValidator._count_components_without(dungeon, cv)
            if comp_count > 2:
                report["necessary_fails"].append(
                    f"Cut-vertex bottleneck at Room {cv}: removing it splits dungeon into {comp_count} "
                    "disconnected components. Theorem dictates c(G - {v}) <= 2 for any Hamiltonian path."
                )

        # 4. Bipartite Size Parity
        is_bipartite, partitions = DungeonValidator._check_bipartite(dungeon)
        if is_bipartite:
            diff = abs(len(partitions[0]) - len(partitions[1]))
            if diff > 1:
                report["necessary_fails"].append(
                    f"Bipartite mismatch: Dungeon is bipartite with partitions of size {len(partitions[0])} "
                    f"and {len(partitions[1])} (difference {diff} > 1). Traversing all rooms is impossible."
                )

        # Fail early on fatal structural violations
        if report["necessary_fails"]:
            report["hamiltonian_path_exists"] = False
            report["hamiltonian_cycle_exists"] = False
            report["summary_statement"] = (
                "No valid path exists: Dungeon topology violates fundamental structural constraints."
            )
            report["execution_time_ms"] = (time.perf_counter() - t_start) * 1000
            if verbose:
                DungeonValidator._print_report(dungeon, report)
            return report

        # Step 2: Sufficient Conditions (Lecture Alignment)
        if m == n * (n - 1) // 2:
            report["is_complete"] = True

        if n >= 3:
            min_deg = min(len(dungeon.adj[v]) for v in dungeon.adj)
            if min_deg >= n / 2.0:
                report["dirac_theorem"] = True

            ore_satisfied = True
            for u in dungeon.rooms:
                for v in dungeon.rooms:
                    if u < v and v not in dungeon.adj[u]:
                        if len(dungeon.adj[u]) + len(dungeon.adj[v]) < n:
                            ore_satisfied = False
                            break
                if not ore_satisfied:
                    break
            report["ore_theorem"] = ore_satisfied

        # Step 3: Exact Path Search (Warnsdorff's Backtracking)
        paths, cycles = DungeonValidator._search_hamiltonian(dungeon, find_all=find_all_paths, limit=50)

        report["paths"] = paths
        report["cycles"] = cycles
        report["hamiltonian_path_exists"] = len(paths) > 0
        report["hamiltonian_cycle_exists"] = len(cycles) > 0

        # Step 4: Route Diversity Metric (Jaccard Distance)
        if len(paths) >= 2:
            report["route_diversity_score"] = DungeonValidator._calculate_diversity(paths)
        else:
            report["route_diversity_score"] = 0.0

        if report["hamiltonian_path_exists"]:
            report["summary_statement"] = (
                f"Valid dungeon: Successfully found {len(paths)} unique clearing path(s) "
                f"({len(cycles)} closed cycle(s)). Player can clear all rooms without reusing tunnels."
            )
        else:
            report["summary_statement"] = (
                "No valid path exists: Exhaustive search confirmed no Hamiltonian sequence covers all rooms."
            )

        report["execution_time_ms"] = (time.perf_counter() - t_start) * 1000

        if verbose:
            DungeonValidator._print_report(dungeon, report, max_paths_to_display)

        return report

    @staticmethod
    def _find_cut_vertices(dungeon: DungeonGraph) -> Set[int]:
        tin, low = {}, {}
        timer = 0
        cut_vertices = set()

        def dfs(u: int, p: int = -1):
            nonlocal timer
            tin[u] = low[u] = timer
            timer += 1
            children = 0
            for to in dungeon.adj[u]:
                if to == p:
                    continue
                if to in tin:
                    low[u] = min(low[u], tin[to])
                else:
                    dfs(to, u)
                    low[u] = min(low[u], low[to])
                    if low[to] >= tin[u] and p != -1:
                        cut_vertices.add(u)
                    children += 1
            if p == -1 and children > 1:
                cut_vertices.add(u)

        for room in dungeon.rooms:
            if room not in tin:
                dfs(room)
        return cut_vertices

    @staticmethod
    def _count_components_without(dungeon: DungeonGraph, removed_room: int) -> int:
        visited = {removed_room}
        count = 0
        for r in dungeon.rooms:
            if r not in visited:
                count += 1
                queue = deque([r])
                visited.add(r)
                while queue:
                    curr = queue.popleft()
                    for nbr in dungeon.adj[curr]:
                        if nbr not in visited:
                            visited.add(nbr)
                            queue.append(nbr)
        return count

    @staticmethod
    def _check_bipartite(dungeon: DungeonGraph) -> Tuple[bool, Tuple[Set[int], Set[int]]]:
        color = {}
        for r in dungeon.rooms:
            if r not in color:
                color[r] = 0
                q = deque([r])
                while q:
                    u = q.popleft()
                    for v in dungeon.adj[u]:
                        if v not in color:
                            color[v] = 1 - color[u]
                            q.append(v)
                        elif color[v] == color[u]:
                            return False, (set(), set())
        part_0 = {r for r, c in color.items() if c == 0}
        part_1 = {r for r, c in color.items() if c == 1}
        return True, (part_0, part_1)

    @staticmethod
    def _search_hamiltonian(dungeon: DungeonGraph, find_all: bool = True, limit: int = 50):
        n = dungeon.num_rooms
        found_paths = []
        found_cycles = []
        visited = {r: False for r in dungeon.rooms}

        def backtrack(curr: int, depth: int, current_path: List[int]):
            if depth == n:
                found_paths.append(list(current_path))
                if current_path[0] in dungeon.adj[curr]:
                    found_cycles.append(list(current_path) + [current_path[0]])
                return

            if not find_all and len(found_paths) >= 1:
                return
            if len(found_paths) >= limit:
                return

            candidates = []
            for nbr in dungeon.adj[curr]:
                if not visited[nbr]:
                    deg_unvis = sum(1 for nn in dungeon.adj[nbr] if not visited[nn])
                    candidates.append((deg_unvis, nbr))

            candidates.sort(key=lambda x: x[0])

            for _, nbr in candidates:
                visited[nbr] = True
                current_path.append(nbr)
                backtrack(nbr, depth + 1, current_path)
                current_path.pop()
                visited[nbr] = False
                if len(found_paths) >= limit:
                    break

        for start_room in sorted(dungeon.rooms.keys()):
            visited[start_room] = True
            backtrack(start_room, 1, [start_room])
            visited[start_room] = False
            if len(found_paths) >= limit:
                break

        return found_paths, found_cycles

    @staticmethod
    def _calculate_diversity(paths: List[List[int]]) -> float:
        if len(paths) < 2:
            return 0.0

        def get_edges(p):
            return {tuple(sorted((p[i], p[i + 1]))) for i in range(len(p) - 1)}

        edge_sets = [get_edges(p) for p in paths[:25]]
        total_dist = 0.0
        comparisons = 0

        for i in range(len(edge_sets)):
            for j in range(i + 1, len(edge_sets)):
                s1 = edge_sets[i]
                s2 = edge_sets[j]
                inter = len(s1.intersection(s2))
                union = len(s1.union(s2))
                dist = 1.0 - (inter / union if union > 0 else 0.0)
                total_dist += dist
                comparisons += 1

        return round(total_dist / comparisons, 3) if comparisons > 0 else 0.0

    @staticmethod
    def _print_report(dungeon: DungeonGraph, report: Dict, max_paths: int = 5):
        print("=" * 86)
        print(f"DUNGEON VALIDATOR REPORT -- '{dungeon.name}'")
        print("=" * 86)
        print(f"Topology Specs: {report['num_rooms']} Rooms, {report['num_tunnels']} Tunnels")
        print("-" * 86)

        print("Phase 1: Necessary Structural Checks")
        print(f"  * Connectivity: {'[PASSED] Single connected component' if report['is_connected'] else '[FAILED] Disconnected rooms detected'}")
        if report["necessary_fails"]:
            for fail in report["necessary_fails"]:
                print(f"    ! STRUCTURAL FAILURE: {fail}")
        else:
            print("  * Dead-end and Cut-vertex bounds: [PASSED] No fatal structural bottlenecks")

        print("\nPhase 2: Sufficient Conditions (Lecture Slide Checks)")
        print(f"  * Complete Graph (K_{report['num_rooms']}): {'YES (Trivially Hamiltonian)' if report['is_complete'] else 'No'}")
        print(f"  * Dirac's Theorem (deg(v) >= n/2 for all v): {'PASSED (Hamiltonian Cycle Guaranteed)' if report['dirac_theorem'] else 'Failed (Sufficiency check only; graph may still be Hamiltonian)'}")
        print(f"  * Ore's Theorem (deg(u)+deg(v) >= n for non-adj): {'PASSED (Hamiltonian Cycle Guaranteed)' if report['ore_theorem'] else 'Failed (Sufficiency check only; graph may still be Hamiltonian)'}")

        print("\nPhase 3: Route Discovery & Feasibility Statement")
        print("-" * 86)
        if report["hamiltonian_path_exists"]:
            print(f"[VALID DUNGEON] Status: CLEARED")
            print(f"  -> Total Valid Paths Discovered: {len(report['paths'])}")
            print(f"  -> Closed Hamiltonian Cycles:    {len(report['cycles'])}")
            print(f"  -> Route Diversity Metric:        {report['route_diversity_score']} (Jaccard dissimilarity: 0.0=identical, 1.0=completely distinct)")
            print("\n  Sample Traversal Paths (Visiting every room exactly once):")
            for idx, p in enumerate(report["paths"][:max_paths], 1):
                names = [f"{dungeon.rooms[r]['name']}" for r in p]
                print(f"    Path #{idx}: {' -> '.join(names)}")
                print(f"             (Room IDs: {' -> '.join(map(str, p))})")
        else:
            print("[INVALID DUNGEON] Status: REJECTED")
            print("  STATEMENT: No valid path exists.")
            print("  The player cannot clear the entire dungeon by visiting every room exactly once")
            print("  without reusing any tunnel.")

        print("-" * 86)
        print(f"Execution Time: {report['execution_time_ms']:.2f} ms")
        print("=" * 86)


def main():
    parser = argparse.ArgumentParser(
        description="Deliverable 2: Dungeon Validator (Hamiltonian Tour Checker)"
    )
    parser.add_argument("--file", type=str, default="", help="Path to dungeon file (.json or .txt)")
    parser.add_argument("--max-paths", type=int, default=5, help="Maximum sample paths to display (default: 5)")
    args = parser.parse_args()

    content = ""
    file_name = "Standard Input"
    if args.file:
        if not os.path.exists(args.file):
            print(f"[!] Error: File '{args.file}' not found.")
            sys.exit(1)
        file_name = args.file
        with open(args.file, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        # Check if piped from stdin
        if not sys.stdin.isatty():
            content = sys.stdin.read()
        else:
            print("Usage: python dungeon_validator.py --file <path_to_dungeon_file>")
            print("   or: python dungeon_generator.py --rooms 8 | python dungeon_validator.py")
            sys.exit(0)

    if not content.strip():
        print("[!] Error: Empty dungeon input.")
        sys.exit(1)

    if content.strip().startswith("{"):
        dungeon = DungeonGraph.from_json(content)
    else:
        dungeon = DungeonGraph.from_edge_list_text(content, name=file_name)

    DungeonValidator.validate(dungeon, find_all_paths=True, max_paths_to_display=args.max_paths)


if __name__ == "__main__":
    main()
