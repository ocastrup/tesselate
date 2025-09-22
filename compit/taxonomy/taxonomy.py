import graphviz
import networkx as nx
import plotly.graph_objects as go
import numpy as np
import matplotlib.pyplot as plt
from taxonomy.taxonomy_common import (AttributeFields, RancDir, TaxonomyFields,
                                      ExcludeAttributes, GraphvizColors)
from ocx_schema_parser.transformer import Transformer
from ocx_schema_parser.data_classes import OcxEnumerator
from typing import List, Tuple, Union
from collections import defaultdict
from loguru import logger

def create_graphviz_chart(dot:graphviz.Digraph, taxonomy, output_path='taxonomy_chart', filter_reference=None, max_depth=None,
                          exclude_id: bool = False, rankdir: RancDir = RancDir.TB, show_depth: bool = False,
                          color_field: TaxonomyFields = None, ocx_name:bool = False) -> bool:
    """
    Create a visual chart of the taxonomy hierarchy using graphviz.

    Args:
        dot: The graphviz Digraph object
        show_depth: Include level numbers in the chart
        ocx_name: Include the OCX element names in the chart
        color_field: Color nodes based on this field's values
        taxonomy (dict): The taxonomy dictionary
        output_path (str): The output file path (without extension)
        filter_reference (str, optional): Filter nodes by reference value
        max_depth (int, optional): Maximum depth to display in the chart
        exclude_id (bool, optional): If True, exclude labels from nodes
        rankdir (RancDir, optional): Direction of graph layout (TB, BT, LR, RL)
    """

    def get_node_color(node_key: str, color_enabled: bool, color_map: dict,
                       default_color: GraphvizColors = GraphvizColors.DEFAULT.value) -> GraphvizColors:
        """Get color for node based on node key and color map.

        Args:
            node_key (str): Key to look up color for
            color_enabled (bool): Whether coloring is enabled
            color_map (dict): Mapping of keys to colors
            default_color (GraphvizColors): Default color if no match found

        Returns:
            str: Color string to use for node
        """
        if not color_enabled or not node_key:
            return default_color
        return color_map.get(node_key, default_color)

    def url(ocx_type:str) -> str:
        """Create the DokuWiki url to ocx type."""
        logger.debug(f'Adding link to OCX wiki for type: {ocx_type}')
        if ocx_type is None or ocx_type == '':
            return ''
        if '@' in ocx_type:
            ocx_type = ocx_type.split('@')[0]
        base_url = f"https://ocxwiki.3docx.org/doku.php?id=public:schema:3.1.0:{ocx_type}"
        return base_url

    def map_color(reference:str) -> Union[str, None]:
        """Map a string ID to a color."""
        mapped_colors ={'AP215': GraphvizColors.LIGHTBLUE.value,'AP218': GraphvizColors.LIGHTGREEN.value, "Root": GraphvizColors.LIGHTYELLOW.value,}
        if reference in mapped_colors:
            return mapped_colors[reference]
        else:
            return None


    def should_include_node(node_id, current_depth=0):
        if max_depth is not None and current_depth > max_depth:
            return False
        return (filter_reference is None or
                taxonomy[node_id][TaxonomyFields.REFERENCE.value] == filter_reference)

    def should_incude_attribute(name):
        exluded = [excluded_attr.value for excluded_attr in ExcludeAttributes]
        if name in exluded:
            return False
        else:
            return True

    def get_node_depth(node_id, depth=0):
        """Calculate depth of a node by traversing up to root"""
        node = taxonomy.get(node_id)
        if not node or not node[TaxonomyFields.PARENT_ID.value]:
            return depth
        return get_node_depth(node[TaxonomyFields.PARENT_ID.value], depth + 1)

    def format_node_label(node_id, data) -> str:
        """Format node label with attributes using HTML-like syntax"""
        try:
            logger.debug(f'Formatting label for node {node_id} and data:{data}')
            label = '<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">'

            if show_depth:
                label += f'<TR><TD>{get_node_depth(node_id)}</TD></TR>'

            # Add node ID and/or label
            if exclude_id:
                if ocx_name and data.get(TaxonomyFields.MAPPING.value, ""):
                    label += f'<TR><TD><B>{data[TaxonomyFields.MAPPING.value]}</B></TD></TR>'
                else:
                    label += f'<TR><TD><B>{data.get("label", "")}</B></TD></TR>'
            else:
                if ocx_name and data.get(TaxonomyFields.MAPPING.value, ""):
                    label += f'<TR><TD><B>{data[TaxonomyFields.MAPPING.value]}</B><BR/>{node_id}</TD></TR>'
                else:
                    label += f'<TR><TD><B>{data.get(TaxonomyFields.LABEL.value, "")}</B><BR/>{node_id}</TD></TR>'

            # Only process attributes if they exist and are not empty
            attributes = data.get("attributes", {})
            if attributes and isinstance(attributes, dict) and len(attributes) > 0:
                # Sort attributes: required first, then optional
                sorted_attrs = sorted(
                    attributes.items(),
                    key=lambda item: not item[1].get(AttributeFields.REQUIRED.value, False)
                )

                # Add attributes if we have any after filtering
                if sorted_attrs:
                    label += '<TR><TD>'
                    attrs = []
                    for name, attr in sorted_attrs:
                        if should_incude_attribute(name):
                            if attr.get(AttributeFields.REQUIRED.value, False):
                                attrs.append(f'<FONT POINT-SIZE="10" COLOR="red"><B>{name}</B></FONT>')
                            else:
                                attrs.append(f'<FONT POINT-SIZE="10" COLOR="green">{name}</FONT>')
                    if attrs:
                        label += '<BR/>'.join(attrs)
                    label += '</TD></TR>'

            # Close table
            label += '</TABLE>>'
            return label

        except Exception as e:
            logger.error(f"Error formatting label for node {node_id}: {str(e)}")
            return f'<<TABLE BORDER="0"><TR><TD>{node_id}</TD></TR></TABLE>>'  # Fallback label

    # Create nodes and edges
    try:
        dot.attr('node', shape='box',
                 style='rounded,filled',
                 fillcolor=GraphvizColors.DEFAULT.value,
                 fontname='Arial',
                 margin='0.2')

        # Add nodes and edges
        for node_id, data in taxonomy.items():
            current_depth = get_node_depth(node_id)
            logger.debug(f'Adding node with id: {node_id} and depth {current_depth}')
            if should_include_node(node_id, current_depth):
                # Create formatted label with attributes
                label = format_node_label(node_id, data)
                logger.debug(f'The node has label: {label}')
                # Set the node color based on document field if enabled
                fillcolor = GraphvizColors.DEFAULT.value
                if color_field is not None and color_field.value in data:
                    fillcolor = map_color(data[color_field.value])
                    if fillcolor is None:
                        color_map = {value: color.value for value, color in zip(set(
                            data[color_field.value] for data in taxonomy.values() if data.get(color_field.value)),
                                                                                list(GraphvizColors)[
                                                                                :-1])}  # exclude DEFAULT color
                        fillcolor = get_node_color(data[color_field.value], color_enabled=True, color_map=color_map)
                        logger.debug(f'The color map is {color_map} and fill color is {fillcolor}')
                # Create node
                tooltip = data.get(TaxonomyFields.DESCRIPTION.value, '')
                tooltip = '' if tooltip is None else tooltip.replace('"', "'").replace('\n', ' ')
                logger.debug(f'The tooltip is: {tooltip}')
                dot.node(node_id, label, fillcolor=fillcolor, tooltip=tooltip,
                         URL=url(data.get(TaxonomyFields.MAPPING.value, '')), target="_blank")
                # Create edge if there's a parent and parent is within depth limit
                if data[TaxonomyFields.PARENT_ID.value] and (max_depth is None or current_depth <= max_depth):
                    dot.edge(data[TaxonomyFields.PARENT_ID.value], node_id)
    except Exception as e:
        logger.error(f"Error creating graphviz chart: {str(e)}")
        raise Exception from e


def visualize_taxonomy(taxonomy: dict, filter_reference:str, output_chart: str = 'taxonomy_chart',
                       show_depth: bool = False, exclude_id: bool = False,
                       max_depth=None, rankdir: RancDir = RancDir.TB,
                       color_field: TaxonomyFields = None, ocx_name:bool=False) -> bool:
    """
    Create a visual chart of the taxonomy hierarchy.
    """
    try:
        # Create a new directed graph
        dot = graphviz.Digraph(comment='Taxonomy Hierarchy')
        dot.attr(rankdir=rankdir.value)
        # Create chart using graphviz
        create_graphviz_chart(dot=dot, taxonomy=taxonomy, output_path=output_chart,
                              filter_reference=filter_reference, max_depth=max_depth, show_depth=show_depth,
                              rankdir=rankdir, color_field=color_field, exclude_id=exclude_id, ocx_name=ocx_name)
    except Exception as e:
        raise Exception from e
    # Render the graph chart to file
    try:
        dot.render(output_chart, format='svg', cleanup=True)
        return True
    except Exception as e:
        print(f"Error creating chart: {str(e)}")
        return False

def visualize_clustered_taxonomy_old(graphs: list,  output_chart: str = 'clustered_taxonomy_chart',
                       doc_type_filter=None, show_depth: bool = False,
                       max_depth=None, exclude_id: bool = False, rankdir: RancDir = RancDir.TB,
                       color_field: TaxonomyFields = None, ocx_name:bool=False) -> bool:
    """
    Create a clustered taxonomy graph from a list of graphs and render the clustered graphs to a single chart.
    """
    try:

        # Create a new compound graph
        dot = graphviz.Digraph(comment='Taxonomy Hierarchy')
        dot.attr(compound='true')

        # Create subgraphs for each taxonomy in the list
        for i, graph in enumerate(graphs):
            if i == 0:
                rankdir = RancDir.TB.value  # First graph flows top down
            else:
                rankdir = RancDir.BT.value # Second graph flows bottom up
            create_graphviz_chart(dot=dot, taxonomy=graph,
                                  filter_reference=doc_type_filter, max_depth=max_depth, show_depth=show_depth,
                                  exclude_id=exclude_id, rankdir=rankdir, color_field=color_field,
                                  ocx_name=ocx_name)
        # Add cross-hierarchy relationships
        # Only left-right relationships are supported
        for node_id, data in graphs[0].items():
                # Example: Add an edge between node_id_1 in graph 1 and node_id_2 in graph 2
                # Replace 'node_id_1' and 'node_id_2' with actual node IDs from your taxonomy
                if data[TaxonomyFields.MAPPING.value] != '' and data[TaxonomyFields.MAPPING.value] is not None:
                    target_id = data[TaxonomyFields.MAPPING.value].replace(':', '_')
                    if target_id in graphs[1]:
                        # Add an edge
                        dot.edge(node_id, target_id,
                                 color='red',  # Optional: different color for cross-hierarchy links
                                 style='dashed',  # Optional: different style
                                 constraint='false')  # Prevents the edge from affecting node ranking
                    else:
                        logger.error(f'Target ID {target_id} not found in second taxonomy.')

    except Exception as e:
        raise Exception from e
    # Render the graph chart to file
    try:
        dot.render(output_chart, format='svg', cleanup=True)
        return True
    except Exception as e:
        print(f"Error creating chart: {str(e)}")
        return False


def visualize_clustered_taxonomy(graphs: list, output_chart: str = 'clustered_taxonomy_chart',
                                 doc_type_filter=None, show_depth: bool = False,
                                 max_depth=None, exclude_id: bool = False, rankdir: RancDir = RancDir.TB,
                                 color_field: TaxonomyFields = None, ocx_name: bool = False) -> bool:
    try:
        dot = graphviz.Digraph(comment='Taxonomy Hierarchy')
        dot.attr(compound='true')  # Remove global rankdir

        # Create invisible nodes to control positioning
        with dot.subgraph(name='root_nodes') as s:
            s.attr(rank='same')  # Force root nodes to be at same level
            for i, graph in enumerate(graphs):
                root = next(node_id for node_id, data in graph.items()
                            if not data[TaxonomyFields.PARENT_ID.value])
                s.node(f'root_{i}', style='invis')

        # Create subgraphs with different rankdir values
        for i, graph in enumerate(graphs):
            with dot.subgraph(name=f'cluster_{i}') as c:
                # Set different rankdir for each cluster
                if i == 0:
                    c.attr(rankdir=RancDir.TB.value)  # First graph flows left to right
                else:
                    c.attr(rankdir=RancDir.BT.value)  # Second graph flows right to left

                c.attr(label=f'Taxonomy {i + 1}')
                create_graphviz_chart(dot=c, taxonomy=graph,
                                      filter_reference=doc_type_filter,
                                      max_depth=max_depth,
                                      show_depth=show_depth,
                                      exclude_id=exclude_id,
                                      rankdir=RancDir.TB.value if i == 0 else RancDir.BT.value,  # Pass corresponding rankdir
                                      color_field=color_field,
                                      ocx_name=ocx_name)

                # Force root node position
                root = next(node_id for node_id, data in graph.items()
                            if not data[TaxonomyFields.PARENT_ID.value])
                dot.edge(f'root_{i}', root, style='invis')

        # Add cross-hierarchy relationships
        for node_id, data in graphs[0].items():
            if data[TaxonomyFields.MAPPING.value]:
                target_id = data[TaxonomyFields.MAPPING.value].replace(':', '_').lower()
                if target_id in graphs[1]:
                    dot.edge(node_id, target_id,
                             color='red',
                             style='dashed',
                             constraint='false')
                else:
                    logger.error(f'Target ID {target_id} not found in second taxonomy.')

        dot.render(output_chart, format='svg', cleanup=True)
        return True

    except Exception as e:
        print(f"Error creating chart: {str(e)}")
        return False



def visualize_with_plotly(graphs: list, output_file: str = 'taxonomy'):
    output_file += '.html'
    G = nx.DiGraph()

    # Add nodes and edges
    for i, graph in enumerate(graphs):
        for node_id, data in graph.items():
            G.add_node(node_id, group=i, label=data[TaxonomyFields.LABEL.value])
            if data[TaxonomyFields.PARENT_ID.value]:
                G.add_edge(data[TaxonomyFields.PARENT_ID.value], node_id)

    # Add mappings
    for node_id, data in graphs[0].items():
        if data[TaxonomyFields.MAPPING.value]:
            target_id = data[TaxonomyFields.MAPPING.value].replace(':', '_')
            if target_id in graphs[1]:
                G.add_edge(node_id, target_id, edge_type='mapping')

    # Calculate layout
    pos = nx.spring_layout(G, k=1 / np.sqrt(len(G.nodes())), iterations=50)

    # Create Plotly figure
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode='lines'))

    # Add nodes colored by group
    for i in range(len(graphs)):
        node_x = [pos[node][0] for node in G.nodes() if G.nodes[node]['group'] == i]
        node_y = [pos[node][1] for node in G.nodes() if G.nodes[node]['group'] == i]
        fig.add_trace(go.Scatter(x=node_x, y=node_y, mode='markers+text'))

    fig.write_html(output_file)

def ocx_coverage_report(source:dict, target:Transformer, dimensions:List[str]) -> Tuple[dict,list]:
    """
    Generate a coverage report of the mapping from source to target.
    """
    total_nodes = len(source)
    mapped = defaultdict(list)
    not_mapped = defaultdict(list)
    # Traverse all children of a dimension and collect mappings
    # Get all global OCX names
    ocx_elements = target.parser.get_lookup_table()
    enumerations = target.get_enumerators()
    # Get the schema namespaces
    ns = target.parser.get_namespaces()
    for dim in dimensions:
        # Get all children of this dimension recursively
        def get_children(node_id):
            children = []
            for child_id, child_data in source.items():
                if child_data[TaxonomyFields.PARENT_ID.value] == node_id:
                    children.append(child_id)
                    children.extend(get_children(child_id))
            return children

        # Get all nodes under this dimension
        dimension_nodes = get_children(dim)
        logger.debug(f'Found {len(dimension_nodes)} children for dimension {dim}.')
        # dimension_nodes.append(dim)  # Include the dimension itself

        # Check mappings for all nodes under this dimension
        for node_id in dimension_nodes:
            tags = []
            if source[node_id].get(TaxonomyFields.MAPPING.value):
                mapped_id = source[node_id][TaxonomyFields.MAPPING.value]
                enum_type = None
                if '@' in mapped_id:
                    ocx_tag = mapped_id.split('@')[0]
                    ocx_tag = '{' + f'{ns.get(ocx_tag.split(':')[0], '')}' + '}' + f'{ocx_tag.split(":")[1]}'
                    enum_type = (mapped_id.split('@')[1].split('#')[0], mapped_id.split('#')[1])
                    logger.debug(f'Node {node_id} ({source[node_id][TaxonomyFields.LABEL.value]}) has enumeration type {enum_type}.')

                # Handle substituition groups
                elif '=' in mapped_id and '[' in mapped_id:
                    # Handle substitution groups
                    base_element, substitutes = mapped_id.split('=')
                    # Clean up the substitutes string and split into list
                    substitutes = substitutes.strip('[]').split(',')
                    substitutes = [s.strip() for s in substitutes]
                    for substitute in substitutes:
                        if ':' in substitute:
                            tags.append('{' + f'{ns.get(substitute.split(":")[0], "")}' + '}' + f'{substitute.split(":")[1]}')
                        else:
                            tags.append(substitute)
                else:
                    ocx_tag = '{'+ f'{ns.get(mapped_id.split(':')[0],'')}' + '}' +f'{mapped_id.split(":")[1]}'
                if ocx_tag in ocx_elements and not enum_type and len(tags) == 0:
                    mapped[dim].append(ocx_tag)
                elif ocx_tag in ocx_elements and enum_type and enum_type[0] in enumerations and enum_type[1] in enumerations[enum_type[0]].to_dict().get('Value', []):
                    mapped[dim].append(ocx_tag)
                elif len(tags) > 0:
                    found = False
                    for tag in tags:
                        if tag in ocx_elements:
                            mapped[dim].append(tag)
                            found = True
                    if not found:
                        logger.warning(f'Node {node_id} ({source[node_id][TaxonomyFields.LABEL.value]}) mapping {tags} not found in target.')
                        not_mapped[dim].append(node_id)
                else:
                    logger.warning(f'Node {node_id} ({source[node_id][TaxonomyFields.LABEL.value]}) mapping {ocx_tag} not found in target.')
                    not_mapped[dim].append(node_id)
            else:
                not_mapped[dim].append(node_id)
                logger.info(f'Node {node_id} ({source[node_id][TaxonomyFields.LABEL.value]}) has no mapping.')

# Create the report dict
    report = {}
    total = 0
    total_mapped = 0
    total_not_mapped = 0
    for dim in dimensions:
        not_mapped_children = ''
        for child in not_mapped[dim]:
            not_mapped_children += f'{child}, '
        report[dim] = {
            'Dimension' : f'{dim}',
            'Label': source[dim][TaxonomyFields.LABEL.value],
            'Coverage %': f'{(len(mapped[dim]) / (len(mapped[dim]) + len(not_mapped[dim])) * 100):.1f}' if (len(
                mapped[dim]) + len(not_mapped[dim])) > 0 else '0.0',
            'Total items': len(mapped[dim]) + len(not_mapped[dim]),
            '# mapped': len(mapped[dim]),
            '# not mapped': len(not_mapped[dim]),
            'Not mapped ids': not_mapped_children,
        }
        total += len(mapped[dim]) + len(not_mapped[dim])
        total_mapped +=  len(mapped[dim])
        total_not_mapped += len(not_mapped[dim])

    return report, [total, total_mapped, total_not_mapped]





def create_coverage_chart_mpl(data: dict, axis_label:str="Label", title:str='Taxonomy Coverage by Category',output_file: str = 'coverage_chart.png'):
    """
    Create a horizontal bar chart showing taxonomy coverage using matplotlib.

    Args:
        title: Chart title
        data: Dictionary containing coverage data
        output_file: Output file path
    """
    # Prepare data
    labels = []
    for key, value in data.items():
        label = value.get(axis_label,"")
        if label == "" or label is None:
            label = key
        labels.append(label)
    categories = list(data.keys())
    mapped = [data[cat]['# mapped'] for cat in categories]
    not_mapped = [data[cat]['# not mapped'] for cat in categories]
    coverage = [float(data[cat]['Coverage %']) for cat in categories]

    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 8))

    # Create horizontal bars
    y_pos = range(len(categories))
    ax.barh(y_pos, mapped, height=0.8, color='green', label='Mapped')
    ax.barh(y_pos, not_mapped, height=0.8, color='red', left=mapped, label='Not Mapped')

    # Customize chart
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()  # Invert y-axis to show categories from top to bottom
    ax.set_xlabel('Number of Items')
    ax.set_title(title)
    ax.legend(loc='lower right')

    # Add coverage percentage annotations
    for i, (m, n, c) in enumerate(zip(mapped, not_mapped, coverage)):
        total = m + n
        ax.text(total + 0.5, i, f'{c}%', va='center')

        # Add count annotations inside bars
        if m > 0:
            ax.text(m / 2, i, str(m), ha='center', va='center', color='white')
        if n > 0:
            ax.text(m + n / 2, i, str(n), ha='center', va='center', color='white')

    # Adjust layout and save
    plt.tight_layout()
    plt.savefig(output_file, bbox_inches='tight', dpi=300)
    plt.close()

def doc_coverage_report(source:dict, target:dict, dimensions:List[str]) -> Tuple[dict,list]:
    """
    Generate a coverage report of the mapping from source to target.
    """
    total_nodes = len(source)
    mapped = defaultdict(list)
    not_mapped = defaultdict(list)
    # Traverse all children of a dimension and collect mappings
    # Get all global OCX names
    for dim in dimensions:
        # Get all children of this dimension recursively
        def get_children(node_id):
            children = []
            for child_id, child_data in source.items():
                if child_data[TaxonomyFields.PARENT_ID.value] == node_id:
                    children.append(child_id)
                    children.extend(get_children(child_id))
            return children

        # Get all nodes under this dimension
        dimension_nodes = get_children(dim)
        logger.debug(f'Found {len(dimension_nodes)} children for dimension {dim}.')
        # dimension_nodes.append(dim)  # Include the dimension itself

        # Check mappings for all nodes under this dimension
        for node_id in dimension_nodes:
            if source[node_id].get(TaxonomyFields.MAPPING.value):
                mapped_id = source[node_id][TaxonomyFields.MAPPING.value]
                if mapped_id in target:
                    mapped[dim].append(node_id)
                    logger.debug(f'Node {node_id} ({source[node_id][TaxonomyFields.LABEL.value]}) mapped to {mapped_id}.')
                else:
                    logger.warning(f'Node {node_id} ({source[node_id][TaxonomyFields.LABEL.value]}) mapping {mapped_id} not found in target.')
                    not_mapped[dim].append(node_id)
            else:
                not_mapped[dim].append(node_id)
                logger.info(f'Node {node_id} ({source[node_id][TaxonomyFields.LABEL.value]}) has no mapping.')

# Create the report dict
    report = {}
    total = 0
    total_mapped = 0
    total_not_mapped = 0
    for dim in dimensions:
        not_mapped_children = ''
        for child in not_mapped[dim]:
            not_mapped_children += f'{child}:{source[child].get(TaxonomyFields.LABEL.value)}, '
        report[dim] = {
            'Dimension' : f'{dim}:{source[dim][TaxonomyFields.LABEL.value]}',
            'Coverage %': f'{(len(mapped[dim]) / (len(mapped[dim]) + len(not_mapped[dim])) * 100):.1f}' if (len(
                mapped[dim]) + len(not_mapped[dim])) > 0 else '0.0',
            'Total items': len(mapped[dim]) + len(not_mapped[dim]),
            '# mapped': len(mapped[dim]),
            '# not mapped': len(not_mapped[dim]),
            'Not mapped ids': not_mapped_children,
        }
        total += len(mapped[dim]) + len(not_mapped[dim])
        total_mapped +=  len(mapped[dim])
        total_not_mapped += len(not_mapped[dim])

    return report, [total, total_mapped, total_not_mapped]


