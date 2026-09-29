# Informatics ITS Graph Theory IUP 
## Group 1 Assignment 4

<div align=center>

|    NRP     |           Nama              |
| :--------: |       :------------:        |
| 5025251012 | Khumaidy Syafiq El Maududy  |
| 5025251015 | Renato Kiran Arisandi       |
| 5025251016 | Keven John Gondowardojo     |
| 5025251010 | Agile Octa Agrakha Handrian |

</div>

## Algorithm Explanation

## 1. Problem Formulation

In procedurally generated dungeon crawlers, players explore an underground network of rooms interconnected by tunnels. The core gameplay rule specifies:
> *"The gameplay requires a player to clear the entire dungeon by visiting every room exactly once without reusing any tunnel."*

Therefore:
* **Rooms** correspond to vertices $V$ in an undirected graph $G = (V, E)$.
* **Tunnels** correspond to edges $E$.
* Visiting every room exactly once defines a Hamiltonian Path (open path starting at room $r_{\text{start}}$ and concluding at room $r_{\text{boss}}$) or a Hamiltonian Cycle (closed tour returning to the entrance).
* **Tunnel non-reuse property:** In any simple path where every vertex $v \in V$ is visited exactly once, no edge $(u, v)$ can ever be traversed more than once, because each intermediate vertex is entered exactly once and exited exactly once ($\text{in-degree} = 1, \text{out-degree} = 1$).

---

## 2. Procedural Dungeon Generator [`dungeon_generator.py`](dungeon_generator.py)

### 2.1 Design Objectives
1. **Solvability Guarantee (in Standard Mode):** Dungeons generated for regular gameplay must contain at least one valid clearing path.
2. **Route Diversity (Anti-Repetition):** Routes must not be too similar to each other. If every dungeon layout presents only a single obvious corridor or near-identical paths, player replayability is ruined.
3. **Flaw Injection (Testing & Validation):** Ability to generate intentionally invalid dungeons with known graph-theoretic failure modes to rigorously prove the validator.

### 2.2 Procedural Generation Pipeline
The generator builds dungeons across multiple architectural archetypes:

1. **Randomized Permutation Backbone:**
   For an $n$-room dungeon, the algorithm generates a random permutation $\pi = \langle v_1, v_2, \dots, v_n \rangle$ of $\{1, 2, \dots, n\}$ and constructs the base cycle edges $(\pi_i, \pi_{i+1})$ and $(\pi_n, \pi_1)$. This guarantees that the base graph is Hamiltonian.

2. **Architectural Archetypes:**
   * **Cluster Biomes (`cluster`):** Partitions rooms into 2–3 distinct thematic wings (e.g., Crypts, Sanctum, Armory). Rooms are chained internally within wings, and wings are bound together via **dual inter-cluster bridges**. This forces players to choose fundamentally different wing-clearing orders (e.g., clearing Wing A then Wing B vs. entering Wing B first).
   * **Labyrinth Grid (`grid_labyrinth`):** Arranges rooms onto a 2D spatial coordinate grid connected via serpentine Hamiltonian chains and vertical cross-chambers.
   * **Backbone Chords (`backbone_chords`):** Generates candidate non-adjacent chords across the cycle, shuffling and adding shortcuts based on density $\rho$.

3. **Route Diversity Measurement (Jaccard Distance):**
   To quantify how different the available routes are, we compute the average pairwise **Jaccard Distance** over the edge sets of discovered paths:
   $$d_J(P_a, P_b) = 1 - \frac{|E(P_a) \cap E(P_b)|}{|E(P_a) \cup E(P_b)|}$$
   * $d_J = 0.0$: Identical paths.
   * $d_J = 1.0$: Completely disjoint edge traversals.
   * Our procedural engine tunes chord placement to achieve $d_J \ge 0.45 - 0.65$, ensuring meaningful player agency.

---

## 3. Dungeon Validator [`dungeon_validator.py`](dungeon_validator.py)

The validator implements a multi-phase verification pipeline combining theoretical checks from the lecture slides, structural pruning, and an exact backtracking search.

### Phase 1: Necessary Structural Checks (Fast Pruning)
Before embarking on an exponential search, the validator evaluates structural conditions that mathematically rule out Hamiltonicity:
1. **Connectedness:** Using BFS/DFS from Room 1. If $c(G) > 1$, the graph is disconnected $\implies$ **INVALID**.
2. **Dead-End (Degree 1) Bound:**
   * In any simple path, only the start room and end room can have an effective path degree of 1.
   * If a graph has **$\ge 3$ rooms with degree 1**, no Hamiltonian path can exist $\implies$ **INVALID**.
   * If a graph has **$\ge 1$ room with degree 1**, no Hamiltonian cycle can exist.
3. **Cut-Vertex / Articulation Point Bound:**
   * By graph theory: If $G$ has a Hamiltonian path, then for any subset $S \subset V$, the number of components $c(G - S) \le |S| + 1$.
   * For a single cut-vertex $v$ ($|S| = 1$), removing $v$ can produce at most 2 components ($c(G - \{v\}) \le 2$).
   * If removing room $v$ splits the dungeon into **$\ge 3$ components**, a Hamiltonian path is impossible $\implies$ **INVALID**.
4. **Bipartite Imbalance:**
   * If $G$ is bipartite with partitions $V_1, V_2$, any path alternates between partitions.
   * If $| |V_1| - |V_2| | > 1$, no Hamiltonian path can exist $\implies$ **INVALID**.

### Phase 2: Sufficient Conditions (Week 4 Lecture Alignment)
Directly referencing slides 6–11:
1. **Complete Graph ($K_n$, Slide 7):** $m = \frac{n(n-1)}{2}$. Trivially Hamiltonian ($n \ge 3$ for cycle, $n \ge 2$ for path).
2. **Dirac's Theorem (1952, Slides 8–9):**
   $$\forall v \in V, \quad \deg(v) \ge \frac{n}{2} \implies \text{Hamiltonian Cycle guaranteed}$$
3. **Ore's Theorem (1960, Slides 10–11):**
   $$\forall (u, v) \notin E, \quad \deg(u) + \deg(v) \ge n \implies \text{Hamiltonian Cycle guaranteed}$$
> **Crucial Lecture Caveat:** *Sufficiency $\ne$ Necessity.* Failing Dirac's or Ore's theorems does **not** mean the graph is non-Hamiltonian. The validator flags this clearly in the diagnostic log.

### Phase 3: Exact Path Search (Warnsdorff Backtracking)
For graphs that pass necessary checks, the validator executes a pruned depth-first search:
* **Warnsdorff's Heuristic (MRV):** At current room $u$, candidate unvisited neighbors are sorted in ascending order of their remaining unvisited degree. This steers the search toward constrained bottleneck rooms first, finding valid paths in milliseconds.
* **Output Specification:**
  * **If Valid:** Displays the full sequences of rooms and tunnels for up to $K$ discovered paths, closed cycle count, and diversity score.
  * **If Invalid:** Emits the required specification statement:
    ```
    STATEMENT: No valid path exists.
    The player cannot clear the entire dungeon by visiting every room exactly once
    without reusing any tunnel.
    ```

---

## Sample Cases

### Case 1: Valid Solvable Dungeon (`cluster` Archetype, $N=6$)
```text
Executed command: python dungeon.py --file sample_valid_dungeon.txt --validate
======================================================================================
DUNGEON VALIDATOR REPORT -- 'Graph-6Rooms'
======================================================================================
Topology Specs: 6 Rooms, 8 Tunnels
--------------------------------------------------------------------------------------
Phase 1: Necessary Structural Checks
  * Connectivity: [PASSED] Single connected component
  * Dead-end and Cut-vertex bounds: [PASSED] No fatal structural bottlenecks

Phase 2: Sufficient Conditions (Lecture Slide Checks)
  * Complete Graph (K_6): No
  * Dirac's Theorem (deg(v) >= n/2 for all v): Failed (Sufficiency check only; graph may still be Hamiltonian)
  * Ore's Theorem (deg(u)+deg(v) >= n for non-adj): Failed (Sufficiency check only; graph may still be Hamiltonian)

Phase 3: Route Discovery & Feasibility Statement
--------------------------------------------------------------------------------------
[VALID DUNGEON] Status: CLEARED
  -> Total Valid Paths Discovered: 24
  -> Closed Hamiltonian Cycles:    12
  -> Route Diversity Metric:        0.487 (Jaccard dissimilarity: 0.0=identical, 1.0=completely distinct)

  Sample Traversal Paths (Visiting every room exactly once):
    Path #1: Entrance #1 -> Crypt #4 -> Treasury #5 -> Armory #2 -> Library #3 -> Shrine #6
             (Room IDs: 1 -> 4 -> 5 -> 2 -> 3 -> 6)
    Path #2: Entrance #1 -> Crypt #4 -> Treasury #5 -> Armory #2 -> Shrine #6 -> Library #3
             (Room IDs: 1 -> 4 -> 5 -> 2 -> 6 -> 3)
    Path #3: Entrance #1 -> Crypt #4 -> Shrine #6 -> Library #3 -> Armory #2 -> Treasury #5
             (Room IDs: 1 -> 4 -> 6 -> 3 -> 2 -> 5)
    Path #4: Entrance #1 -> Treasury #5 -> Crypt #4 -> Shrine #6 -> Armory #2 -> Library #3
             (Room IDs: 1 -> 5 -> 4 -> 6 -> 2 -> 3)
    Path #5: Entrance #1 -> Treasury #5 -> Crypt #4 -> Shrine #6 -> Library #3 -> Armory #2
             (Room IDs: 1 -> 5 -> 4 -> 6 -> 3 -> 2)
--------------------------------------------------------------------------------------
Execution Time: 1.33 ms
======================================================================================
```

---

### Case 2: Valid Dense Dungeon Satisfying Ore's Theorem ($N=7$)
```text
Executed command: python dungeon.py --generate --rooms 7 --density 0.5 --archetype backbone_chords --seed 77
======================================================================================
DUNGEON VALIDATOR REPORT -- 'Procedural Dungeon (Backbone Chords, N=7)'
======================================================================================
Topology Specs: 7 Rooms, 14 Tunnels
--------------------------------------------------------------------------------------
Phase 1: Necessary Structural Checks
  * Connectivity: [PASSED] Single connected component
  * Dead-end and Cut-vertex bounds: [PASSED] No fatal structural bottlenecks

Phase 2: Sufficient Conditions (Lecture Slide Checks)
  * Complete Graph (K_7): No
  * Dirac's Theorem (deg(v) >= n/2 for all v): Failed (Sufficiency check only; graph may still be Hamiltonian)
  * Ore's Theorem (deg(u)+deg(v) >= n for non-adj): PASSED (Hamiltonian Cycle Guaranteed)

Phase 3: Route Discovery & Feasibility Statement
--------------------------------------------------------------------------------------
[VALID DUNGEON] Status: CLEARED
  -> Total Valid Paths Discovered: 50
  -> Closed Hamiltonian Cycles:    42
  -> Route Diversity Metric:        0.622 (Jaccard dissimilarity: 0.0=identical, 1.0=completely distinct)

  Sample Traversal Paths (Visiting every room exactly once):
    Path #1: Entrance #1 -> Shrine #6 -> Armory #2 -> Treasury #5 -> Library #3 -> Crypt #4 -> Prison #7
             (Room IDs: 1 -> 6 -> 2 -> 5 -> 3 -> 4 -> 7)
    Path #2: Entrance #1 -> Shrine #6 -> Armory #2 -> Treasury #5 -> Library #3 -> Prison #7 -> Crypt #4
             (Room IDs: 1 -> 6 -> 2 -> 5 -> 3 -> 7 -> 4)
    Path #3: Entrance #1 -> Shrine #6 -> Armory #2 -> Treasury #5 -> Prison #7 -> Library #3 -> Crypt #4
             (Room IDs: 1 -> 6 -> 2 -> 5 -> 7 -> 3 -> 4)
--------------------------------------------------------------------------------------
Execution Time: 1.21 ms
======================================================================================
```

---

### Case 3: Invalid Dungeon — 3-Way Cut-Vertex Bottleneck ($N=7$)
> **Mathematical Proof of Failure:** Room 1 acts as a central bottleneck connecting 3 isolated wings. Removing Room 1 results in $c(G - \{1\}) = 3$ components. By the Articulation Component Bound Theorem, any Hamiltonian path satisfies $c(G - S) \le |S| + 1 = 2$. Since $3 > 2$, a Hamiltonian path cannot exist.
```text
Executed command: python dungeon.py --invalid bottleneck --rooms 7
======================================================================================
DUNGEON VALIDATOR REPORT -- 'Invalid Dungeon (Flaw: bottleneck)'
======================================================================================
Topology Specs: 7 Rooms, 9 Tunnels
--------------------------------------------------------------------------------------
Phase 1: Necessary Structural Checks
  * Connectivity: [PASSED] Single connected component
    ! STRUCTURAL FAILURE: Cut-vertex bottleneck at Room 1: removing it splits dungeon into 3 disconnected components. Theorem dictates c(G - {v}) <= 2 for any Hamiltonian path.

Phase 2: Sufficient Conditions (Lecture Slide Checks)
  * Complete Graph (K_7): No
  * Dirac's Theorem (deg(v) >= n/2 for all v): Failed (Sufficiency check only; graph may still be Hamiltonian)
  * Ore's Theorem (deg(u)+deg(v) >= n for non-adj): Failed (Sufficiency check only; graph may still be Hamiltonian)

Phase 3: Route Discovery & Feasibility Statement
--------------------------------------------------------------------------------------
[INVALID DUNGEON] Status: REJECTED
  STATEMENT: No valid path exists.
  The player cannot clear the entire dungeon by visiting every room exactly once
  without reusing any tunnel.
--------------------------------------------------------------------------------------
Execution Time: 0.05 ms
======================================================================================
```

---

### Case 4: Invalid Dungeon — Dead-End Bound Exceeded ($N=6$, 3 Leaves)
> **Mathematical Proof of Failure:** Rooms 2, 3, and 4 each have degree 1 (dead ends). A simple open path has exactly 2 terminal rooms (start and end). Therefore, a graph with 3 or more degree-1 vertices cannot have a Hamiltonian path.
```text
Executed command: python dungeon.py --invalid dead_ends --rooms 6
======================================================================================
DUNGEON VALIDATOR REPORT -- 'Invalid Dungeon (Flaw: dead_ends)'
======================================================================================
Topology Specs: 6 Rooms, 6 Tunnels
--------------------------------------------------------------------------------------
Phase 1: Necessary Structural Checks
  * Connectivity: [PASSED] Single connected component
    ! STRUCTURAL FAILURE: Dead-end bound violated: 3 rooms have degree 1 (Rooms: [2, 3, 4]). A simple path has at most 2 endpoints; traversing all rooms without reuse is impossible.
    ! STRUCTURAL FAILURE: Cut-vertex bottleneck at Room 1: removing it splits dungeon into 4 disconnected components. Theorem dictates c(G - {v}) <= 2 for any Hamiltonian path.

Phase 2: Sufficient Conditions (Lecture Slide Checks)
  * Complete Graph (K_6): No
  * Dirac's Theorem (deg(v) >= n/2 for all v): Failed (Sufficiency check only; graph may still be Hamiltonian)
  * Ore's Theorem (deg(u)+deg(v) >= n for non-adj): Failed (Sufficiency check only; graph may still be Hamiltonian)

Phase 3: Route Discovery & Feasibility Statement
--------------------------------------------------------------------------------------
[INVALID DUNGEON] Status: REJECTED
  STATEMENT: No valid path exists.
  The player cannot clear the entire dungeon by visiting every room exactly once
  without reusing any tunnel.
--------------------------------------------------------------------------------------
Execution Time: 0.06 ms
======================================================================================
```

---

### Case 5: Invalid Dungeon — Disconnected Chambers ($N=6$)
```text
Executed command: python dungeon.py --invalid disconnected --rooms 6
======================================================================================
DUNGEON VALIDATOR REPORT -- 'Invalid Dungeon (Flaw: disconnected)'
======================================================================================
Topology Specs: 6 Rooms, 5 Tunnels
--------------------------------------------------------------------------------------
Phase 1: Necessary Structural Checks
  * Connectivity: [FAILED] Disconnected rooms detected
    ! STRUCTURAL FAILURE: Graph is disconnected. Unreachable rooms from Room 1: [6]
    ! STRUCTURAL FAILURE: Isolated rooms with degree 0 detected: [6]

Phase 2: Sufficient Conditions (Lecture Slide Checks)
  * Complete Graph (K_6): No
  * Dirac's Theorem (deg(v) >= n/2 for all v): Failed (Sufficiency check only; graph may still be Hamiltonian)
  * Ore's Theorem (deg(u)+deg(v) >= n for non-adj): Failed (Sufficiency check only; graph may still be Hamiltonian)

Phase 3: Route Discovery & Feasibility Statement
--------------------------------------------------------------------------------------
[INVALID DUNGEON] Status: REJECTED
  STATEMENT: No valid path exists.
  The player cannot clear the entire dungeon by visiting every room exactly once
  without reusing any tunnel.
--------------------------------------------------------------------------------------
Execution Time: 0.04 ms
======================================================================================
```

---

### Case 6: Invalid Dungeon — Bipartite Size Mismatch $K_{2, 5}$ ($N=7$)
> **Mathematical Proof of Failure:** The dungeon forms a bipartite graph with partition sets $A=\{1, 2\}$ and $B=\{3, 4, 5, 6, 7\}$. Any path must alternate between $A$ and $B$. The maximum number of vertices visitable starting in $B$ is $|A| + |A| + 1 = 2 \times 2 + 1 = 5 < 7$. Thus, visiting all 7 rooms without reusing tunnels is mathematically impossible.
```text
Executed command: python dungeon.py --invalid bipartite_mismatch --rooms 7
======================================================================================
DUNGEON VALIDATOR REPORT -- 'Invalid Dungeon (Flaw: bipartite_mismatch)'
======================================================================================
Topology Specs: 7 Rooms, 10 Tunnels
--------------------------------------------------------------------------------------
Phase 1: Necessary Structural Checks
  * Connectivity: [PASSED] Single connected component
    ! STRUCTURAL FAILURE: Bipartite mismatch: Dungeon is bipartite with partitions of size 2 and 5 (difference 3 > 1). Traversing all rooms is impossible.

Phase 2: Sufficient Conditions (Lecture Slide Checks)
  * Complete Graph (K_7): No
  * Dirac's Theorem (deg(v) >= n/2 for all v): Failed (Sufficiency check only; graph may still be Hamiltonian)
  * Ore's Theorem (deg(u)+deg(v) >= n for non-adj): Failed (Sufficiency check only; graph may still be Hamiltonian)

Phase 3: Route Discovery & Feasibility Statement
--------------------------------------------------------------------------------------
[INVALID DUNGEON] Status: REJECTED
  STATEMENT: No valid path exists.
  The player cannot clear the entire dungeon by visiting every room exactly once
  without reusing any tunnel.
--------------------------------------------------------------------------------------
Execution Time: 0.04 ms
======================================================================================
```

---

## AI Tools Usage Disclosure

* **AI Model / Assistant Used:** Google Gemini (Antigravity Assistant)
* **Scope of AI Assistance:**
  * Assisted in designing and formulating the procedural generation algorithms and diversity metrics (Jaccard distance over edge sets).
  * Implemented graph theoretical validation algorithms aligning directly with lecture slides (Dirac's Theorem, Ore's Theorem, articulation cut-vertex bounds, and dead-end bounds).
  * Structured the command-line interface (`--generate`, `--validate`, `--suite`, `--invalid`) and formatted benchmark logs.
* **Verification & Ownership:** All source code, algorithm proofs, complexity guarantees, and console traces have been thoroughly verified and tested by the group members.

---
