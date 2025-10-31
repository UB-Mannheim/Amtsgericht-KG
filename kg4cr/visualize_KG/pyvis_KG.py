import os
from pyvis.network import Network
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF
from urllib.parse import urlparse
from collections import defaultdict

# ---------- Helpers ----------

def clean_label(uri_or_literal):
    """Clean up URIs and literals for display"""
    if isinstance(uri_or_literal, URIRef):
        parsed = urlparse(str(uri_or_literal))
        fragment = parsed.fragment
        if fragment:
            return fragment.replace('_', ' ')
        path_parts = parsed.path.split('/')
        last_part = path_parts[-1] if path_parts[-1] else path_parts[-2]
        return last_part.replace('_', ' ')
    else:
        return str(uri_or_literal)


def get_node_type(uri, graph):
    """Determine node type dynamically from RDF type"""
    types = set()
    for obj in graph.objects(uri, RDF.type):
        types.add(clean_label(obj))
    if types:
        return ", ".join(types)
    return "Unknown"


def get_node_color(node_type):
    """Assign colors based on node type"""
    colors = {
        "Company": "#4CAF50",  # Green
        "Court": "#2196F3",    # Blue
        "Unknown": "#9E9E9E"   # Grey
    }
    if "," in node_type:  # multiple types
        for t in node_type.split(", "):
            if t in colors:
                return colors[t]
    return colors.get(node_type, "#9E9E9E")


def get_node_label(uri, graph, EX):
    """Prefer human-readable names for labels"""
    for pred in [EX.companyName, EX.courtName]:
        for obj in graph.objects(uri, pred):
            return str(obj)
    return clean_label(uri)


def get_node_info(uri, graph):
    """Tooltip with all predicates/objects of a node"""
    info = []
    for pred, obj in graph.predicate_objects(uri):
        if pred == RDF.type:
            continue
        info.append(f"{clean_label(pred)}: {obj}")
    return "<br>".join(info)


# ---------- Main Visualization ----------

def visualize_top200_courts(turtle_file_path):
    g = Graph()
    try:
        g.parse(turtle_file_path, format="turtle")
        print(f"✅ Parsed {len(g)} triples from {turtle_file_path}")
    except Exception as e:
        print(f"❌ Error parsing turtle file: {e}")
        return

    EX = Namespace("http://example.org/schema/")

    # Step 1 — Count companies per court
    court_counts = defaultdict(set)  # court_uri → set of company_uris
    for subj, pred, obj in g.triples((None, EX.registeredAt, None)):
        if (subj, RDF.type, EX.Company) in g:
            court_counts[obj].add(subj)

    # Sort by number of connected companies
    sorted_courts = sorted(court_counts.items(), key=lambda x: len(x[1]), reverse=False)
    top_courts = dict(sorted_courts[:50])

    print(f"🏛️ Found {len(court_counts)} courts, keeping top {len(top_courts)} most connected.")

    # Step 2 — Collect all relevant companies linked to those top courts
    top_companies = set()
    for companies in top_courts.values():
        top_companies.update(companies)

    # Step 3 — Filter triples to keep only relevant courts & companies
    filtered_graph = Graph()
    for s, p, o in g:
        if s in top_companies or s in top_courts or o in top_companies or o in top_courts:
            filtered_graph.add((s, p, o))

    print(f"📊 Filtered to {len(filtered_graph)} triples for visualization.")

    # Step 4 — Build interactive PyVis graph
    net = Network(height="1200px", width="100%", directed=True,
                  notebook=False, bgcolor="#222222", font_color="white")

    nodes = set()
    edges = []

    for subj, pred, obj in filtered_graph:
        if pred == RDF.type:
            nodes.add(subj)
            continue
        nodes.add(subj)
        if isinstance(obj, URIRef):
            nodes.add(obj)
            edges.append({'source': subj, 'target': obj, 'label': clean_label(pred)})

    print(f"🧩 Rendering {len(nodes)} nodes and {len(edges)} edges.")

    # Add nodes
    for node_uri in nodes:
        node_type = get_node_type(node_uri, filtered_graph)
        node_label = get_node_label(node_uri, filtered_graph, EX)
        node_info = get_node_info(node_uri, filtered_graph)
        node_color = get_node_color(node_type)

        size = 25 if "Company" in node_type else 35 if "Court" in node_type else 20
        net.add_node(
            str(node_uri),
            label=node_label,
            title=node_info,
            group=node_type,
            color=node_color,
            size=size
        )

    # Add edges
    for edge in edges:
        try:
            net.add_edge(
                str(edge['source']),
                str(edge['target']),
                label=edge['label'],
                color="#888888"
            )
        except Exception as e:
            print(f"Skipping edge: {e}")
            continue

    # Graph options
    net.set_options("""
    {
        "physics": {
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "centralGravity": 0.005,
                "springLength": 150,
                "springConstant": 0.08,
                "damping": 0.4
            },
            "minVelocity": 0.75,
            "solver": "forceAtlas2Based",
            "stabilization": {"iterations": 150}
        },
        "nodes": {
            "font": {"color": "white", "size": 12},
            "borderWidth": 2,
            "shadow": true
        },
        "edges": {
            "font": {"color": "white", "size": 10},
            "arrows": {"to": {"enabled": true, "scaleFactor": 1.2}},
            "smooth": {"type": "continuous"}
        },
        "interaction": {"hover": true, "tooltipDelay": 200}
    }
    """)

    output_file = "top200_courts_graph.html"
    net.save_graph(output_file)
    print(f"💾 Graph saved to: {os.path.abspath(output_file)}")

    try:
        import webbrowser
        webbrowser.open(f"file://{os.path.abspath(output_file)}")
    except:
        print("⚠️ Could not open browser automatically")

if __name__ == "__main__":
    turtle_file = r"C:\Users\abhijain\Documents\KG4CR\data\processed\DE_newspapers_1920_45_processed\Qlever_cleaned\DE_1920_45_comb_ontology_cleaned.ttl"
    visualize_top200_courts(turtle_file)
