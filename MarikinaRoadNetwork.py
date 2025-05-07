import osmnx as ox
import networkx as nx
import geopandas as gpd
import matplotlib.pyplot as plt

place_name = "Marikina, Metro Manila, Philippines"

# Download the drivable road network
try:
    G = ox.graph_from_place(place_name, network_type="drive")
except Exception as e:
    print(f"Error downloading graph: {e}")
    exit()

# Check strongly connected components
components = list(nx.strongly_connected_components(G))
print(f"Number of strongly connected components: {len(components)}")
for i, component in enumerate(components):
    subgraph = G.subgraph(component)
    print(f"Component {i}: {len(subgraph.nodes)} nodes, {len(subgraph.edges)} edges")

# Use largest strongly connected component
if not nx.is_strongly_connected(G):
    print("Graph is not strongly connected. Using largest component.")
    G = G.subgraph(max(components, key=len)).copy()

# Save the graph
ox.save_graphml(G, filepath="marikina_road_network.graphml")

# Plot and show the road network
fig, ax = ox.plot_graph(G, figsize=(12, 12), node_size=0, edge_linewidth=0.5, show=True, save=True, filepath="marikina_road_network.png")

# Verify coverage
gdf = ox.geocode_to_gdf(place_name)
city_boundary = gdf.geometry.iloc[0]
nodes = ox.graph_to_gdfs(G, edges=False)
nodes_within_boundary = nodes.geometry.within(city_boundary)
print(f"Nodes within Marikina boundary: {nodes_within_boundary.sum()} / {len(nodes)}")
print(f"Percentage of nodes within boundary: {100 * nodes_within_boundary.sum() / len(nodes):.2f}%")

# Define default speeds by road type (in km/h)
default_speeds = {
    'motorway': 80, 'trunk': 60, 'primary': 50, 'secondary': 40,
    'tertiary': 35, 'residential': 30, 'unclassified': 30
}

# Add travel time to edges
for u, v, key, data in G.edges(keys=True, data=True):
    length = data.get('length', 0)  # in meters
    if length == 0:
        continue
    highway = data.get('highway', 'unclassified')
    if isinstance(highway, list):
        highway = highway[0]
    speed = data.get('maxspeed')
    if speed:
        if isinstance(speed, str):
            try:
                speed = float(speed.split()[0])  # E.g., "30 km/h" -> 30
            except (ValueError, IndexError):
                speed = default_speeds.get(highway, 30)
        elif isinstance(speed, list):
            # Take first valid numeric value from list
            for s in speed:
                try:
                    speed = float(s)
                    break
                except (ValueError, TypeError):
                    continue
            else:  # If no valid number found
                speed = default_speeds.get(highway, 30)
        else:
            try:
                speed = float(speed)
            except (ValueError, TypeError):
                speed = default_speeds.get(highway, 30)
    else:
        speed = default_speeds.get(highway, 30)
    travel_time = (length / 1000) / (speed / 3600)  # time in seconds
    data['travel_time'] = travel_time

# Verify travel time assignment
missing_travel_time = [(u, v, key) for u, v, key, data in G.edges(keys=True, data=True) if 'travel_time' not in data]
if missing_travel_time:
    print(f"Warning: {len(missing_travel_time)} edges missing travel_time")
else:
    print("All edges have travel_time assigned.")

# Verify graph size
print(f"Nodes: {len(G.nodes)}")
print(f"Edges: {len(G.edges)}")

# Ensure the plot is displayed
plt.show()