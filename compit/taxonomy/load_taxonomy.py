"""Module to load taxonomy data into the database."""
import logging
from typing import List
from pathlib import Path

import pandas as pd
from rich.console import Console
from rich.tree import Tree

from taxonomy.ocx_taxonomy import OcxTaxonomy
from taxonomy.taxonomy_common import AttributeFields, TaxonomyFields


def get_excel_cell_ref(row_num, col_name):
    """Convert row number and column name to Excel cell reference."""
    return f"{col_name}:{row_num}"


def get_children(taxonomy, parent_id):
    """
    Get all children of a given parent ID in the taxonomy.
    """
    children = []
    for child_id, data in taxonomy.items():
        if data["parent"] == parent_id:
            children.append(child_id)
    return children


def load_taxonomy_attributes(excel_path: Path, sheet_name: str = 'attributes') -> dict:
    """
    Load attributes from Excel sheet and store them in a dictionary by taxonomy ID.
    Each taxonomy ID contains a list of attribute dictionaries with their properties.

    Args:
        excel_path (Path): Path to Excel file
        sheet_name (str): Name of sheet containing attributes

    Returns:
        dict: Dictionary of attributes by taxonomy ID
    """
    # Read the attributes sheet
    df_attributes = pd.read_excel(excel_path, sheet_name='attributes')

    # Check required columns
    required_fields = [field.value for field in AttributeFields]
    missing_fields = set(required_fields) - set(df_attributes.columns)
    if missing_fields:
        errors = [
            f"Missing required columns in header: {', '.join(missing_fields)}",
            f"Found columns: {', '.join(df_attributes.columns)}"
        ]
        raise Exception(f"Errors in attributes sheet: {', '.join(errors)}")

    # Create attributes dictionary by node ID
    attributes_by_id = {}

    for _, row in df_attributes.iterrows():
        node_id = str(row[AttributeFields.ID.value]).strip()

        # Create attribute dictionary with all fields
        attribute_dict = {
            field.value: str(row[field.value]).strip() if pd.notna(row[field.value]) else None
            for field in AttributeFields
        }
        attribute_dict['required'] = bool(row[AttributeFields.REQUIRED.value]) if (
            pd.notna(row[AttributeFields.REQUIRED.value])) else False

        # Skip if attribute name is None
        if attribute_dict['attribute_name'] is None:
            continue

        # Initialize list for taxonomy ID if not exists
        if node_id not in attributes_by_id:
            attributes_by_id[node_id] = {}

        # Store attribute using attribute name as key
        attributes_by_id[node_id][attribute_dict['attribute_name']] = attribute_dict

    return attributes_by_id


def load_taxonomy(excel_path: Path, sheet_name: str = 'taxonomy', sub_graph: str = None) -> dict:
    """
    Load taxonomy from an Excel file including document type, description, rule reference and attributes information.

    Args:
        excel_path (Path): Path to Excel file
        sheet_name (str): Name of sheet containing taxonomy
        sub_graph (str): Optional ID to extract a sub_graph of this node, its parents and children

    Returns:
        dict: Filtered taxonomy dictionary
    """
    try:
        # Read the taxonomy sheet
        df_taxonomy = pd.read_excel(excel_path, sheet_name=sheet_name)
        # Read attributes sheet
        attributes_by_id = load_taxonomy_attributes(excel_path, sheet_name='attributes')

        # Convert taxonomy DataFrame to dictionary format
        full_taxonomy = {}
        for _, row in df_taxonomy.iterrows():
            # Create the taxonomy dict with all fields
            taxonomy_dict = {
                field.value: str(row[field.value]).strip() if pd.notna(row[field.value]) else None
                for field in TaxonomyFields
            }
            row_id = str(row[TaxonomyFields.ID.value]).strip()
            taxonomy_dict['attributes'] = attributes_by_id.get(row_id, {})  # Add attributes, empty dict if none found
            full_taxonomy[row_id] = taxonomy_dict

        if not sub_graph:
            return full_taxonomy

        # Get filtered taxonomy for specific ID
        filtered_taxonomy = {}

        def add_parents(node_id):
            """Add all parent nodes recursively"""
            node = full_taxonomy.get(node_id)
            if node and node[TaxonomyFields.PARENT_ID.value]:
                parent_id = node[TaxonomyFields.PARENT_ID.value]
                if parent_id not in filtered_taxonomy and parent_id in full_taxonomy:
                    filtered_taxonomy[parent_id] = full_taxonomy[parent_id]
                    add_parents(parent_id)

        def add_children(node_id):
            """Add all child nodes recursively"""
            for child_id, data in full_taxonomy.items():
                if data[TaxonomyFields.PARENT_ID.value] == node_id:
                    if child_id not in filtered_taxonomy:
                        filtered_taxonomy[child_id] = data
                        add_children(child_id)

        # Add the filtered node itself
        if sub_graph in full_taxonomy:
            filtered_taxonomy[sub_graph] = full_taxonomy[sub_graph]
            # Add all parents
            add_parents(sub_graph)
            # Add all children
            add_children(sub_graph)
            return filtered_taxonomy
        else:
            raise Exception(f"Filter ID '{sub_graph}' not found in taxonomy")

    except Exception as e:
        raise Exception(f"Error reading Excel file: {str(e)}")


def expand_nodes(taxonomy: dict, node_ids: list) -> None:
    """
    Expand nodes in the taxonomy by adding their children.

    Args:
        taxonomy (dict): The taxonomy dictionary to expand
        node_ids (list): List of node IDs to expand
    """
    for taxonomy_id in node_ids:
        if taxonomy_id in taxonomy:
            children = get_children(taxonomy, taxonomy_id)
            for child_id in children:
                if child_id not in taxonomy:
                    # Add child node with empty fields if not already present
                    taxonomy[child_id] = {
                        "parent": taxonomy_id,
                        "label": "",
                        "doc_type": None,
                        "description": None,
                        "ocx_name": None,
                        "attributes": {}
                    }


def append_row(taxonomy: dict, row_id, row: dict) -> None:
    """
    Append a new row to the taxonomy dictionary.
    """

    taxonomy[row_id] = row


def serialize_taxonomy(taxonomy: dict, excel_path: Path, sheet_name: str = 'taxonomy') -> None:
    """
    Serialize the taxonomy dictionary back to an Excel file.
    """
    # Convert taxonomy dictionary to list of rows
    rows = []
    for node_id, data in taxonomy.items():
        row = {
            TaxonomyFields.ID.value: node_id,
            TaxonomyFields.PARENT_ID.value: data["parent"],
            TaxonomyFields.LABEL.value: data["label"],
            TaxonomyFields.REFERENCE.value: data["reference"],
            TaxonomyFields.DESCRIPTION.value: data["description"],
            TaxonomyFields.MAPPING.value: data["mapping"]
        }
        rows.append(row)

    # Create DataFrame from rows
    df = pd.DataFrame(rows)

    # Write DataFrame to Excel
    with pd.ExcelWriter(excel_path, engine='openpyxl', mode='a' if excel_path.exists() else 'w') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)


def print_taxonomy(taxonomy, parent_id=None, tree=None, doc_type_filter=None, max_depth=None, current_depth=0):
    """
    Print the taxonomy using Rich's Tree visualization with optional doc_type filtering and depth limit.
    """
    console = Console()

    def should_include_node(node_id):
        return (doc_type_filter is None or
                taxonomy[node_id]["doc_type"] == doc_type_filter)

    def has_matching_descendants(node_id, depth=0):
        if max_depth is not None and depth >= max_depth:
            return False
        if should_include_node(node_id):
            return True
        children = get_children(taxonomy, node_id)
        return any(has_matching_descendants(child, depth + 1) for child in children)

    if tree is None:
        root_nodes = [node_id for node_id, data in taxonomy.items()
                      if data["parent"] is None and has_matching_descendants(node_id)]
        if not root_nodes:
            console.print("❌ No matching nodes found in taxonomy")
            return

        main_tree = Tree("📁 Taxonomy")
        for root in sorted(root_nodes):
            if has_matching_descendants(root):
                node_tree = main_tree.add(f"[blue]{root}[/blue]: {taxonomy[root]['label']}")
                print_taxonomy(taxonomy, root, node_tree, doc_type_filter, max_depth, 1)
        console.print(main_tree)
        return

    if max_depth is not None and current_depth > max_depth:
        return

    children = get_children(taxonomy, parent_id)
    for child in sorted(children):
        if has_matching_descendants(child, current_depth):
            if should_include_node(child):
                child_tree = tree.add(f"[blue]{child}[/blue]: {taxonomy[child]['label']}")
                print_taxonomy(taxonomy, child, child_tree, doc_type_filter, max_depth, current_depth + 1)
            else:
                print_taxonomy(taxonomy, child, tree, doc_type_filter, max_depth, current_depth + 1)

def load_multiple_graphs(files: List[Path], sub_graphs:List[str]= None, sheet_name: str = 'taxonomy') -> list:
    """
    Load multiple taxonomy graphs from a list of Excel files.

    Args:
        sub_graphs: List of sub_graph IDs to filter each file
        sheet_name: The sheet name with data
        files (list): List of Path objects to Excel files

    Returns:
        list: List of taxonomy dictionaries
    """
    graphs = []
    for i, path in enumerate(files):
        if sub_graphs is not None:
            sub_graph = sub_graphs[i] if i < len(sub_graphs) else None
        else:
            sub_graph = None
        graph = load_taxonomy(path, sheet_name=sheet_name, sub_graph=sub_graph )
        graphs.append(graph)

    return graphs