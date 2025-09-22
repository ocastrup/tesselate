from enum import Enum


class ExcludeNodes(Enum):
    """Enum to represent nodes to exclude."""
    DESIGNVIEW = "OccurrenceGroup"
class ExcludeAttributes(Enum):
    """Enum to represent nodes to exclude."""
    ID = "id"
    GUIDREF = "GUIDRef"
    NAME = "name"
    UNIT = "unit"
    NUMERICVALUE = "numericvalue"


def camel_to_snake(name: str) -> str:
    """Convert camel case to snake case."""
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def camel_to_sentence(name: str) -> str:
    """Convert camel case to sentence case."""
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1 \2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1 \2', s1).capitalize()

class RenderEngine(Enum):
    """
    Enum for render engines.
    """
    MATPLOTLIB = "matplotlib"
    PLOTLY = "plotly"
    SEABORN = "seaborn"
    GRAPHVIZ = "graphviz"


class RancDir(Enum):
    """
    Enum for graphviz rank direction.
    """
    TB = "TB"  # Top to Bottom
    BT = "BT"  # Bottom to Top
    LR = "LR"  # Left to Right
    RL = "RL"  # Right to Left


class AttributeFields(Enum):
    """
    Enum for attribute fields.
    """
    ID = "taxonomy_id"
    ATTRIBUTE_NAME = "attribute_name"
    DESCRIPTION = "description"
    REQUIRED = "required"
    DATA_TYPE = "datatype"
    OCX_NAME = "ocx_name"


class TaxonomyFields(Enum):
    """
    Enum for taxonomy fields.
    """
    ID = "taxonomy_id"
    PARENT_ID = "parent_id"
    LABEL = "label"
    DESCRIPTION = "description"
    MAPPING = "mapping"
    EXAMPLE = "example"
    REFERENCE = "reference"


class GraphvizColors(Enum):
    """
    Enum for Graphviz colors.
    """

    LIGHTBLUE = "lightblue"
    LIGHTGREEN = "lightgreen"
    LIGHTYELLOW = "lightyellow"
    LIGHTPINK = "lightpink"
    LIGHTGRAY = "lightgray"
    CORAL = "coral"
    CORNFLOWERBLUE = "cornflowerblue"
    DARKSEAGREEN = "darkseagreen"
    KHAKI = "khaki"
    PLUM = "plum"
    SALMON = "salmon"
    ORANGE = "orange"
    GOLD = "gold"
    CYAN = "cyan"
    LIGHTCORAL = "lightcoral"
    MAGENTA = "magenta"
    VIOLET = "violet"
    TURQUOISE = "turquoise"
    LAVENDER = "lavender"
    BEIGE = "beige"
    AQUA = "aqua"
    LIMEGREEN = "limegreen"
    DEFAULT = "lightblue"
