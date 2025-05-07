import requests
import pandas as pd
import osmnx as ox
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import geopandas as gpd
from shapely.geometry import Point

# Step 2: Acquire Hospital Locations using Overpass API
# Overpass API endpoint
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Overpass QL query for active hospitals in Marikina City
overpass_query = """
[out:json][timeout:25];
area["name"="Marikina"]["boundary"="administrative"]["admin_level"="6"]->.searchArea;
(
  node["amenity"="hospital"]["disused"!="yes"]["closed"!="yes"](area.searchArea);
  way["amenity"="hospital"]["disused"!="yes"]["closed"!="yes"](area.searchArea);
  relation["amenity"="hospital"]["disused"!="yes"]["closed"!="yes"](area.searchArea);
);
out center;
"""

# Send the request with error handling
try:
    response = requests.get(OVERPASS_URL, params={'data': overpass_query})
    response.raise_for_status()
    data = response.json()
except requests.RequestException as e:
    print(f"Error fetching hospital data: {e}")
    exit()

# Parse results
hospitals = []
for element in data['elements']:
    name = element['tags'].get('name', 'Unnamed')
    lat = element.get('lat') or element.get('center', {}).get('lat')
    lon = element.get('lon') or element.get('center', {}).get('lon')
    if lat and lon:
        hospitals.append({'name': name, 'latitude': lat, 'longitude': lon})

# Create DataFrame and save
hospitals_df = pd.DataFrame(hospitals)
if hospitals_df.empty:
    print("No hospitals found.")
    exit()
print("Hospital Locations:")
print(hospitals_df)
hospitals_df.to_csv("marikina_hospitals.csv", index=False)

# Load the road network graph from Step 1
try:
    G = ox.load_graphml("marikina_road_network.graphml")
except Exception as e:
    print(f"Error loading graph: {e}")
    exit()

# Snap hospitals to nearest nodes in the graph
hospital_nodes = []
for _, row in hospitals_df.iterrows():
    lat, lon = row['latitude'], row['longitude']
    try:
        nearest_node = ox.distance.nearest_nodes(G, lon, lat)
        if nearest_node in G.nodes:
            hospital_nodes.append({
                'name': row['name'],
                'latitude': lat,
                'longitude': lon,
                'node_id': nearest_node
            })
        else:
            print(f"Warning: Hospital '{row['name']}' maps to node {nearest_node} outside graph.")
    except Exception as e:
        print(f"Error snapping hospital '{row['name']}': {e}")

# Create DataFrame for snapped nodes and save
hospital_nodes_df = pd.DataFrame(hospital_nodes)
if hospital_nodes_df.empty:
    print("No hospitals could be snapped to the graph.")
    exit()
print("\nHospital Nodes (Snapped to Graph):")
print(hospital_nodes_df)
hospital_nodes_df.to_csv("marikina_hospital_nodes.csv", index=False)

# Validate connectivity
print("\nValidating hospital node connectivity:")
for _, row in hospital_nodes_df.iterrows():
    node_id = row['node_id']
    if node_id in G.nodes:
        print(f"Hospital '{row['name']}' mapped to node {node_id} (valid).")
    else:
        print(f"Warning: Hospital '{row['name']}' node {node_id} not in graph.")

# Plot the road network with hospital locations
fig, ax = ox.plot_graph(G, figsize=(12, 12), node_size=0, edge_linewidth=0.5, edge_color='gray', show=False, close=False)

# Convert hospital coordinates to GeoDataFrame for plotting
geometry = [Point(lon, lat) for lon, lat in zip(hospitals_df['longitude'], hospitals_df['latitude'])]
gdf_hospitals = gpd.GeoDataFrame(hospitals_df, geometry=geometry, crs="EPSG:4326")

# Plot hospitals as red markers
gdf_hospitals.plot(ax=ax, color='red', markersize=100, zorder=2, label='Hospitals')

# Add hospital labels
for x, y, name in zip(gdf_hospitals.geometry.x, gdf_hospitals.geometry.y, gdf_hospitals['name']):
    ax.annotate(name, xy=(x, y), xytext=(5, 5), textcoords="offset points", fontsize=8, color='black', zorder=3)

# Add legend and title
plt.legend()
plt.title("Marikina City Road Network with Hospital Locations")
plt.tight_layout()

# Save and show the plot
plt.savefig("marikina_hospitals_plot.png", dpi=300, bbox_inches='tight')
plt.show()

print("\nPlot saved as 'marikina_hospitals_plot.png' and displayed interactively.")