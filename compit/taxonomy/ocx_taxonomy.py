"""Module to handle OCX taxonomy generation and manipulation."""
from typing import Union, Iterator
from ocx_schema_parser.transformer import Transformer
from ocx_schema_parser.elements import OcxGlobalElement, OcxSchemaChild, OcxSchemaAttribute
from pathlib import Path
from loguru import logger
from ocx_schema_parser.xelement import LxmlElement

from taxonomy.taxonomy_common import ExcludeNodes, camel_to_snake, AttributeFields, TaxonomyFields, camel_to_sentence

logger.enable('ocx_schema_parser')


class OcxTaxonomy:
    """Class to represent the OCX Taxonomy."""

    def __init__(self, taxonomy: dict = None, attributes: list = None):
        self.transformer = Transformer()
        self.taxonomy = taxonomy if taxonomy is not None else {}
        self.taxonomy_attributes = attributes if attributes is not None else []

    def get_transformer(self) -> Transformer:
        """Get the OCX transformer."""
        return self.transformer

    def transform_schema_from_url(self, folder: Path, url:str, ) -> bool:
        """Load and transform the OCX schema from the url."""
        if self.transformer.transform_schema_from_url(url, folder):
            logger.info(f"Successfully loaded OCX schema from {url}")
            return True
        else:
            logger.error(f"Failed to parse OCX schema from {url}")
            return False


    def get_global_element_from_name(self, name:str) -> Union[OcxGlobalElement, None]:
        """Get the global element from its name."""
        if self.transformer.is_transformed() is not True:
            logger.error("The schema has not been transformed yet.")
            return None
        element = self.transformer.get_ocx_element_from_type(name)
        if isinstance(element, OcxGlobalElement):
            return element
        else:
            logger.error(f"The element {name} is not a global element.")
            return None

    def iter_children(self, element: OcxGlobalElement, filter:bool = False,
                      filter_type:str = "ocx:Quantity_T") -> Iterator[OcxSchemaChild] :
        """Iterate over the children of the element."""
        if self.transformer.is_transformed() is not True:
            logger.error("The schema has not been transformed yet.")
            pass
        for child in element.get_children():
            if filter and child.type == filter_type:
                yield child
            else:
                yield child

    def add_node(self, element:Union[OcxGlobalElement, OcxSchemaChild], taxonomy_id:str, parent_id:str):
        """Add a node to the taxonomy."""

         # Add attributes if any
        for attribute in element.get_attributes():
            self.add_attribute(element=attribute, id=taxonomy_id)
        # Add the node
        node = {
            TaxonomyFields.PARENT_ID.value: parent_id,
            TaxonomyFields.LABEL.value: camel_to_sentence(element.get_name()),
            TaxonomyFields.DESCRIPTION.value: element.get_annotation(),
            TaxonomyFields.MAPPING.value: f'{element.get_prefix()}:{element.get_name()}',
            TaxonomyFields.EXAMPLE.value: "",  # Placeholder for example
            TaxonomyFields.REFERENCE.value: "",  # Placeholder for reference
            # TaxonomyFields.MANDATORY.value: element.get_cardinality()
        }
        logger.debug(f"Adding node: {taxonomy_id} under parent: {parent_id}")
        self.taxonomy[taxonomy_id] = node
        return

    def add_attribute(self, element:OcxSchemaAttribute, id:str,):
        """Add taxonomy attributes."""
        attr = {
            AttributeFields.ID.value: id,
            AttributeFields.ATTRIBUTE_NAME.value: element.name,
            AttributeFields.DESCRIPTION.value: element.description,
            AttributeFields.OCX_NAME.value: f'{element.prefix}:{element.name}',
            AttributeFields.REQUIRED.value: True if element.use == "req." else False,
            AttributeFields.DATA_TYPE.value: 'enum' if 'Restriction of type xs:string' in element.type else 'string',
        }
        logger.debug(f"Adding attribute: {attr.get(AttributeFields.OCX_NAME.value)} under parent: {id}")
        self.taxonomy_attributes.append(attr)



    def build_taxonomy_from_ocx_name(self, parent_id: str, ocx_name: str, full_graph:bool=False,): # Todo: Fix missing units
        """Build the taxonomy starting from the ocx_name."""
        element = self.get_global_element_from_name(ocx_name)
        if element is None:
            logger.error(f"Element {ocx_name} not found.")
            return
        if full_graph:
            taxonomy_id = self.create_unique_taxonomy_id(name=element.get_name(), parent_id=parent_id,)
        else:
            taxonomy_id = f'{element.get_prefix()}_{element.get_name().lower()}'
        self.add_node(element, taxonomy_id=taxonomy_id, parent_id=parent_id,)
        self._build_taxonomy_recursive(element, parent_id=taxonomy_id, full_graph=full_graph)

    def _build_taxonomy_recursive(self, element: OcxGlobalElement, parent_id: str, full_graph:bool):
        """Recursively build the taxonomy."""
        for child in self.iter_children(element):
            child_element = self.get_global_element_from_name(f'{LxmlElement.namespace_prefix(child.type)}:{child.name}')
            if child_element and child_element.get_name() not in [ExcludeNodes.DESIGNVIEW.value]:
                if full_graph:
                    taxonomy_id = self.create_unique_taxonomy_id(name=child_element.get_name(), parent_id=parent_id)
                else:
                    taxonomy_id = f'{child_element.get_prefix()}_{child_element.get_name().lower()}'
                self.add_node(child_element, taxonomy_id=taxonomy_id,parent_id=parent_id, )
                self._build_taxonomy_recursive(child_element, parent_id=taxonomy_id, full_graph=full_graph)

    def save_taxonomy_to_excel(self, file_path: Path, sheet_name: str = "taxonomy") -> bool:
        """Save the taxonomy to an Excel file."""
        import pandas as pd
        try:
            # Save taxonomy nodes
            df = pd.DataFrame.from_dict(self.taxonomy, orient='index')
            df.index.name = TaxonomyFields.ID.value
            df.reset_index(inplace=True)
            with pd.ExcelWriter(file_path, engine='openpyxl', mode='w') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            logger.info(f"Taxonomy saved to {file_path} in sheet {sheet_name}")

            # save attributes to a separate sheet
            if self.taxonomy_attributes:
                df_attr = pd.DataFrame(self.taxonomy_attributes)
                # df_attr.index.name = AttributeFields.ID.value
                # df_attr.reset_index(inplace=True)
                with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                    df_attr.to_excel(writer, sheet_name="attributes", index=False)
                logger.info(f"Attributes saved to {file_path} in sheet 'attributes'")
            return True
        except Exception as e:
            logger.error(f"Failed to save taxonomy to Excel: {e}")
            return False

    def build_full_taxonomy_and_save_to_file(self,exel_file:Path, full_graph:bool=False):
        """Build the full taxonomy starting from the ocx:Vessel."""
        self.build_taxonomy_from_ocx_name(parent_id="", ocx_name="ocx:ocxXML",full_graph=full_graph) # parent_id of root is blank
        self.save_taxonomy_to_excel(file_path=exel_file, sheet_name="taxonomy")


    def create_unique_taxonomy_id(self, name:str, parent_id:str) -> str:
        """Return a unique id"""
        id = camel_to_snake(name)
        if id in self.taxonomy:
            unique_id = f'{parent_id}_{camel_to_snake(name)}'
            logger.info(f"Creating unique id for {name}: {unique_id}.")
        else:
            unique_id = id
            logger.info(f"Creating id for {name}: {unique_id}.")
        return unique_id