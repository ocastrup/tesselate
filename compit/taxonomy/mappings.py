"""Module for generating coverage reports between document requirements, taxonomy, and OCX schema."""
import re
from taxonomy.taxonomy_common import TaxonomyFields
from ocx_schema_parser.transformer import Transformer
from ocx_schema_parser.xelement import LxmlElement
from ocx_common.parser.xml_document_parser import LxmlParser
from lxml.etree import Element
from typing import List, Tuple, Union
from taxonomy.taxonomy import doc_coverage_report
from ocx_common.x_path.x_path import OcxPathBuilder, OcxPath
from ocx_common.ocx_query.query import OcxQuery
from lxml import etree
from loguru import logger
from ocx_common.lxml_wrapper.xelement import XsdElement


def get_all_descendants(node_id: str, doc_req: dict) -> List[str]:
    """Get all descendants of a node recursively"""
    descendants = []
    for child_id, data in doc_req.items():
        if data.get(TaxonomyFields.PARENT_ID.value) == node_id:
            descendants.append(child_id)
            descendants.extend(get_all_descendants(child_id, doc_req))
    return descendants


def end_to_end_coverage_report(doc_req: dict, taxonomy: dict, ocx_schema: Transformer, dimensions: List[str]) \
        -> Tuple[dict, list]:
    """Generate coverage report counting all descendants under each dimension"""
    report = {}
    total_items = 0
    total_mapped = 0

    for dim in dimensions:
        mapped_items = []
        not_mapped_items = []

        # Get all descendants under this dimension
        descendants = get_all_descendants(dim, doc_req)

        # Analyze mapping chain for each descendant
        for node_id in descendants:
            data = doc_req[node_id]
            tax_mapping = data.get(TaxonomyFields.MAPPING.value)
            if tax_mapping and tax_mapping in taxonomy:
                # Found in taxonomy, now check if it maps to OCX
                tax_node = taxonomy[tax_mapping]
                ocx_mapping = tax_node.get(TaxonomyFields.MAPPING.value)

                if ocx_mapping:
                    # Check OCX mapping validity
                    ns = ocx_schema.parser.get_namespaces()
                    ocx_elements = ocx_schema.parser.get_lookup_table()
                    enumerations = ocx_schema.get_enumerators()

                    is_valid = False
                    if '@' in ocx_mapping and not "=" in ocx_mapping:
                        # Handle enumeration mapping
                        ocx_tag = ocx_mapping.split('@')[0]
                        ocx_tag = '{' + f'{ns.get(ocx_tag.split(":")[0], "")}' + '}' + f'{ocx_tag.split(":")[1]}'
                        enum_type = (ocx_mapping.split('@')[1].split('#')[0], ocx_mapping.split('#')[1])

                        is_valid = (ocx_tag in ocx_elements and
                                    enum_type[0] in enumerations and
                                    enum_type[1] in enumerations[enum_type[0]].to_dict().get('Value', []))
                    elif '=' in ocx_mapping and '[' in ocx_mapping:
                        # Handle substitution groups
                        base_element, substitutes = ocx_mapping.split('=')
                        # Clean up the substitutes string and split into list
                        substitutes = substitutes.strip('[]').split(',')
                        substitutes = [s.strip() for s in substitutes]
                        # Check for all substitutes
                        for substitute in substitutes:
                            if not ':' in substitute:
                                logger.error(f"Invalid substitute format (missing prefix): {substitute}")
                                continue
                            ocx_tag = '{' + f'{ns.get(substitute.split(":")[0], "")}' + '}' + f'{substitute.split(":")[1]}'
                            is_valid = ocx_tag in ocx_elements
                        if is_valid:
                            mapped_items.append((node_id, tax_mapping, ocx_mapping))
                        else:
                            not_mapped_items.append((node_id, tax_mapping, "Invalid OCX mapping"))
                    else:
                        # Handle regular element mapping
                        ocx_tag = '{' + f'{ns.get(ocx_mapping.split(":")[0], "")}' + '}' + f'{ocx_mapping.split(":")[1]}'
                        is_valid = ocx_tag in ocx_elements

                    if is_valid:
                        mapped_items.append((node_id, tax_mapping, ocx_mapping))
                    else:
                        not_mapped_items.append((node_id, tax_mapping, "Invalid OCX mapping"))
                else:
                    not_mapped_items.append((node_id, tax_mapping, "No OCX mapping"))
            else:
                not_mapped_items.append((node_id, "No taxonomy mapping", ""))

        # Create report entry
        total = len(mapped_items) + len(not_mapped_items)
        coverage = (len(mapped_items) / total * 100) if total > 0 else 0.0

        # Format not_mapped_items as string
        not_mapped_details = ""
        for item in not_mapped_items:
            not_mapped_details += f"{item[0]}:{doc_req[item[0]].get(TaxonomyFields.LABEL.value)} ({item[1]} -> {item[2]}), "

        report[dim] = {
            "Dimension": f'{dim}:{doc_req[dim][TaxonomyFields.LABEL.value]}',
            "Coverage %": f"{coverage:.1f}",
            "Total items": total,
            "# mapped": len(mapped_items),
            "# not mapped": len(not_mapped_items),
            "Not mapped ids": not_mapped_details
        }

        total_items += total
        total_mapped += len(mapped_items)

    return report, [total_items, total_mapped, total_items - total_mapped]


def model_coverage_report(doc_req: dict, taxonomy: dict, parser: LxmlParser, dimensions: List[str]) -> Tuple[dict, list]:
    """
    Generate coverage report by checking mappings against actual XML elements in the OCX model.

    Args:
        doc_req: The document requirements dictionary
        taxonomy: The taxonomy dictionary
        parser: The OCX model XML parser
        dimensions: The list of dimension IDs to report on
    """
    try:
        report = {}
        total_items = 0
        total_mapped = 0

        # Get the root element and namespaces once
        root = parser.get_root()
        ns = parser.get_namespaces()

        for dim in dimensions:
            mapped_items = []
            not_mapped_items = []
            descendants = get_all_descendants(dim, doc_req)

            for node_id in descendants:
                data = doc_req[node_id]
                tax_mapping = data.get(TaxonomyFields.MAPPING.value)

                if tax_mapping and tax_mapping in taxonomy:
                    tax_node = taxonomy[tax_mapping]
                    ocx_mapping = tax_node.get(TaxonomyFields.MAPPING.value)

                    if ocx_mapping:

                        try:
                            is_valid = False
                            if '@' in ocx_mapping and not "=" in ocx_mapping:
                                # Handle enumeration value mapping (element@enumType#value)
                                element_name, enum_part = ocx_mapping.split('@')
                                prefix, local_name = element_name.split(':')
                                namespace = ns.get(prefix, '')  # Get the namespace for the prefix

                                # Check enumeration value if specified
                                if '#' in enum_part:
                                    enum_type, enum_value = enum_part.split('#')
                                    # Use both namespace prefix and local-name in the query
                                    # Check for enum sub-type
                                    if ':' in enum_type:
                                        enum_value, enum_sub = enum_type.split(':')
                                        # Remove whitespace in enum_sub using regex
                                        enum_sub = re.sub(r'\s+', '', enum_sub)
                                        xpath = f"//*[local-name()='{local_name}' and @*[local-name()='{enum_type}'{enum_value}: {enum_sub}']" # Ensure one whitespace before the enum_sub
                                        is_valid = len(root.xpath(xpath, namespaces=ns)) > 0
                                    else:
                                        xpath = f"//*[local-name()='{local_name}' and @*[local-name()='{enum_type}']='{enum_value}']"
                                        elements = root.xpath(xpath, namespaces=ns)
                                        is_valid = len(elements) > 0
                                        if not is_valid:
                                            logger.debug(f"No elements found for {ocx_mapping} using xpath: {xpath}")
                            elif '=' in ocx_mapping and '[' in ocx_mapping:
                                # Handle substitution groups
                                base_element, substitutes = ocx_mapping.split('=')
                                # Clean up the substitutes string and split into list
                                substitutes = substitutes.strip('[]').split(',')
                                substitutes = [s.strip() for s in substitutes]

                                # Build XPath to find any element that matches one of the substitutes
                                local_names = []
                                for substitute in substitutes:
                                    if ':' in substitute:
                                        prefix, local_name = substitute.split(':')
                                        local_names.append(local_name)
                                    else:
                                        local_names.append(substitute)

                                if local_names:
                                    # Create XPath condition to match any of the local names
                                    name_conditions = " or ".join([f"local-name()='{name}'" for name in local_names])
                                    xpath = f"//*[{name_conditions}]"
                                    is_valid = len(root.xpath(xpath, namespaces=ns)) > 0
                                else:
                                    is_valid = False
                                    logger.error(f"No valid element names found in substitution group: {ocx_mapping}")

                            else:
                                # Handle simple element mapping
                                prefix, local_name = ocx_mapping.split(':')
                                namespace = ns.get(prefix, '')
                                xpath = f"//*[local-name()='{local_name}']"
                                is_valid = len(root.xpath(xpath, namespaces=ns)) > 0

                        except Exception as e:
                            logger.error(f"Error checking mapping {ocx_mapping}: {str(e)}")
                            is_valid = False

                        if is_valid:
                            mapped_items.append((node_id, tax_mapping, ocx_mapping))
                        else:
                            not_mapped_items.append((node_id, tax_mapping, f"Element {ocx_mapping} not found in 3DOCX model"))
                    else:
                        not_mapped_items.append((node_id, tax_mapping, "No OCX mapping"))
                else:
                    not_mapped_items.append((node_id, "No taxonomy mapping", ""))

            # Create report entry
            total = len(mapped_items) + len(not_mapped_items)
            coverage = (len(mapped_items) / total * 100) if total > 0 else 0.0

            not_mapped_details = ""
            for item in not_mapped_items:
                not_mapped_details += f"{item[0]}:{doc_req[item[0]].get(TaxonomyFields.LABEL.value)} ({item[1]} -> {item[2]}), "

            report[dim] = {
                "Dimension": dim,
                "Title": f'{dim}:{doc_req[dim][TaxonomyFields.LABEL.value]}',
                "Coverage %": f"{coverage:.1f}",
                "Total items": total,
                "# mapped": len(mapped_items),
                "# not mapped": len(not_mapped_items),
                "Not mapped ids": not_mapped_details
            }

            total_items += total
            total_mapped += len(mapped_items)

        return report, [total_items, total_mapped, total_items - total_mapped]

    except Exception as e:
        logger.error(f"Error in coverage report: {str(e)}")
        return {}, [0, 0, 0]