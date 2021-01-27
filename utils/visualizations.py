import matplotlib.pyplot as plt
import numpy as np
import networkx as nx
import igraph as ig


from utils.constants import DatasetType, GraphVisualizationTool, network_repository_cora_url


def get_num_nodes_from_edge_index(edge_index):
    # set extracts the unique node ids and by doing a union between source and target node ids we get all ids
    return len(set(edge_index[0]).union(set(edge_index[1])))


def convert_adj_to_edge_index(adjacency_matrix):
    assert isinstance(adjacency_matrix, np.ndarray), f'Expected NumPy array got {type(adjacency_matrix)}.'
    h, w = adjacency_matrix.shape
    assert h == w, f'Expected square shape got = {adjacency_matrix.shape}.'

    # Handles both adjacency matrices as well as connectivity masks used in softmax (check out Imp2 of the GAT model)
    # connectivity masks are equivalent to adjacency matrices they just have -np.inf instead of 0 and 0 instead of 1
    # I'm assuming non-weighted (binary) adjacency matrices here obviously and this code isn't meant to be as generic
    # as possible but a learning resource.
    active_value = 0 if np.isinf(adjacency_matrix).any() else 1

    edge_index = []
    for src_node_id in range(h):
        for trg_nod_id in range(w):
            if adjacency_matrix[src_node_id, trg_nod_id] == active_value:
                edge_index.append([src_node_id, trg_nod_id])

    return np.asarray(edge_index).transpose()  # change shape from (N,2) into (2,N)


def plot_in_out_degree_distributions(edge_index, dataset_name):
    """
        Note: It would be easy to do various kinds of powerful network analysis using igraph/networkx, etc.
        I chose to explicitly calculate only the node degree statistics here, but you can go much further if needed and
        calculate the graph diameter, number of triangles and many other concepts from the network analysis field.

    """
    assert isinstance(edge_index, np.ndarray), f'Expected NumPy array got {type(edge_index)}.'
    if edge_index.shape[0] == edge_index.shape[1]:
        edge_index = convert_adj_to_edge_index(edge_index)

    num_of_nodes = get_num_nodes_from_edge_index(edge_index)
    # Store each node's input and output degree (they're the same for undirected graphs such as Cora)
    in_degrees = np.zeros(num_of_nodes, dtype=np.int)
    out_degrees = np.zeros(num_of_nodes, dtype=np.int)

    # Edge index shape = (2, num_of_edges), the first row contains the source nodes, the second one target/sink nodes
    # Note on terminology: source nodes point to target/sink nodes
    for cnt in range(edge_index.shape[1]):
        source_node_id = edge_index[0, cnt]
        target_node_id = edge_index[1, cnt]

        out_degrees[source_node_id] += 1  # source node points towards some other node -> increment it's out degree
        in_degrees[target_node_id] += 1

    hist = np.zeros(np.max(out_degrees) + 1)
    for out_degree in out_degrees:
        hist[out_degree] += 1

    fig = plt.figure()
    fig.subplots_adjust(hspace=0.6)
    plt.subplot(311)
    plt.plot(in_degrees, color='red')
    plt.xlabel('node id'); plt.ylabel('in-degree count'); plt.title('Input degree for different node ids')

    plt.subplot(312)
    plt.plot(out_degrees, color='green')
    plt.xlabel('node id'); plt.ylabel('out-degree count'); plt.title('Out degree for different node ids')

    plt.subplot(313)
    plt.plot(hist, color='blue')
    plt.xlabel('node degree'); plt.ylabel('# nodes for the given out degree'); plt.title(f'Node out degree distribution for {dataset_name} dataset')
    plt.xticks(np.arange(0, len(hist), 5.0))
    plt.grid(True)
    plt.show()


def visualize_graph(edge_index, node_labels, dataset_name, visualization_tool=GraphVisualizationTool.IGRAPH):
    """
    Check out this blog for available graph visualization tools:
        https://towardsdatascience.com/large-graph-visualization-tools-and-approaches-2b8758a1cd59

    Basically depending on how big your graph is there may be better drawing tools than igraph.

    """
    assert isinstance(edge_index, np.ndarray), f'Expected NumPy array got {type(edge_index)}.'
    if edge_index.shape[0] == edge_index.shape[1]:
        edge_index = convert_adj_to_edge_index(edge_index)

    num_of_nodes = get_num_nodes_from_edge_index(edge_index)
    edge_index_tuples = list(zip(edge_index[0, :], edge_index[1, :]))

    # Networkx package is primarily used for network analysis, graph visualization was an afterthought in the design
    # of the package - but nonetheless you'll see it used for graph drawing as well
    if visualization_tool == GraphVisualizationTool.NETWORKX:
        nx_graph = nx.Graph()
        nx_graph.add_edges_from(edge_index_tuples)
        nx.draw_networkx(nx_graph)
        plt.show()

    elif visualization_tool == GraphVisualizationTool.IGRAPH:
        # Construct the igraph graph
        ig_graph = ig.Graph()
        ig_graph.add_vertices(num_of_nodes)
        ig_graph.add_edges(edge_index_tuples)

        # Prepare the visualization settings dictionary
        visual_style = {}

        # Defines the size of the plot and margins
        visual_style["bbox"] = (3000, 3000)
        visual_style["margin"] = 35

        # A simple heuristic, defines the edge thickness. I've chosen thickness so that it's proportional to the number
        # of shortest paths (geodesics) that go through a certain edge in our graph (edge_betweenness function)

        # line1: I use log otherwise some edges will be too thick and others not visible at all
        # edge_betweeness returns 0.5 for certain edges that's why I use np.clip as log will be negative for those edges
        # line2: Normalize so that the thickest edge is 1 otherwise edges appear too thick on the chart
        # line3: The idea here is to make the strongest edge stay stronger than others, 6 just worked, don't dwell on it

        edge_weights_raw = np.clip(np.log(ig_graph.edge_betweenness()), a_min=0, a_max=None)
        edge_weights_raw_normalized = edge_weights_raw / np.max(edge_weights_raw)
        edge_weights = [w**6 for w in edge_weights_raw_normalized]
        visual_style["edge_width"] = edge_weights  # using a constant here like 0.1 also gives nice visualizations

        # A simple heuristic for vertex size. Size ~ (degree / 2) (it gave nice results I tried log and sqrt as well)
        visual_style["vertex_size"] = [deg / 2 for deg in ig_graph.degree()]

        # This is the only part that's Cora specific as Cora has 7 labels
        if dataset_name.lower() == DatasetType.CORA.name.lower():
            label_to_color_map = {0: "red", 1: "blue", 2: "green", 3: "orange", 4: "yellow", 5: "pink", 6: "gray"}
            visual_style["vertex_color"] = [label_to_color_map[label] for label in node_labels]
        else:
            print('Feel free to add custom color scheme for your specific dataset. Using igraph default coloring.')

        # Set the layout - the way the graph is presented on a 2D chart. Graph drawing is a subfield for itself!
        # I used "Kamada Kawai" a force-directed method, this family of methods are based on physical system simulation.
        # (layout_drl also gave nice results for Cora)
        visual_style["layout"] = ig_graph.layout_kamada_kawai()

        print('Plotting results ... (it may take couple of seconds).')
        ig.plot(ig_graph, **visual_style)

        print(f'There are much better tools to visualize core like this one {network_repository_cora_url}.')
        print(f'Nonetheless tools like igraph can be useful for quick visualization.')
    else:
        raise Exception(f'Visualization tool {visualization_tool.name} not supported.')