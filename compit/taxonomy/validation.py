"""Taxonomy validations"""
from pathlib import Path

import pandas as pd

from taxonomy.load_taxonomy import get_excel_cell_ref
from taxonomy.taxonomy_common import TaxonomyFields

# Known words to ignore in spell checking
known_words = ['draught', 'shipyard', 'shipyards', 'shipbuilding', 'shipbuild', 'shipowner',
    'moulded', 'moulded', 'keel', 'keels', 'midship', 'midships', 'forecastle',
    'forepeak', 'aftpeak', 'amidships', 'amidship', 'bulkhead', 'bulkheads',
    'bulkhead', 'bulkheads', 'fore', 'aft', 'starboard', 'port', 'bow', 'stern',
    'hatch', 'hatches', 'machinery', 'machineries', 'machinings', 'machining',
    ]
def validate_taxonomy(excel_path: Path, sheet_name: str = 'taxonomy', spell_check:bool=False) -> list:
    """
    Validate taxonomy structure including all required fields.
    """
    ids = set()
    parents = {}
    errors = []
    try:
        from spellchecker import SpellChecker
        spell = SpellChecker(language='en')
        spell.word_frequency.load_words(known_words)
    except ImportError:
        if spell_check:
            errors.append(
                "pyspellchecker not installed. Install with 'pip install pyspellchecker' or set skip_spell_check=True")
            return errors
    try:
        # Read Excel file
        df = pd.read_excel(excel_path, sheet_name=sheet_name)

        # Check required columns
        required_fields = [field.value for field in TaxonomyFields]
        missing_fields = set(required_fields) - set(df.columns)
        if missing_fields:
            errors.append(f"Missing required columns in header: {', '.join(missing_fields)}")
            errors.append(f"Found columns: {', '.join(df.columns)}")
            return errors

        # Validate rows
        for index, row in df.iterrows():
            excel_row = index + 2  # Excel row numbers start at 1, and we have a header

            try:
                # Check for empty required fields
                if pd.isna(row[TaxonomyFields.ID.value]):
                    errors.append(f"Empty value for required field !r{TaxonomyFields.ID.value} at "
                                  f"{get_excel_cell_ref(excel_row, TaxonomyFields.ID.value)}")
                    continue

                # Spell check description if available and spell checking is enabled
                if spell_check and pd.notna(row[TaxonomyFields.DESCRIPTION.value]):
                    description = str(row[TaxonomyFields.DESCRIPTION.value])
                    misspelled = [word for word in description.split()
                                  if not spell[word.strip('.,()')]and not word.isnumeric() and not word.isupper()
                                  #and not word.isdigit() and not word.isalpha()
                                  and '_' not in word and '%' not in word and '-' not in word and '/' not in word
                                  and '=' not in word and '+' not in word and '#' not in word and '&' not in word]
                    if misspelled:
                        errors.append(f"Possible spelling errors in description at "
                                      f"{get_excel_cell_ref(excel_row, TaxonomyFields.DESCRIPTION.value)}: "
                                      f"{', '.join(misspelled)}")
                # Normalize IDs by removing leading/trailing spaces
                row_id = str(row[TaxonomyFields.ID.value]).strip()
                parent_id = str(row[TaxonomyFields.PARENT_ID.value]).strip() \
                    if (pd.notna(row[TaxonomyFields.PARENT_ID.value])
                        and row[TaxonomyFields.PARENT_ID.value] != '') else None

                # Skip validation for empty parent IDs (root nodes)
                if parent_id == '':
                    parent_id = None

                if row_id in ids:
                    errors.append(
                        f"Duplicate ID '{row_id}' found at {get_excel_cell_ref(excel_row, TaxonomyFields.PARENT_ID.value)}")
                ids.add(row_id)
                parents[row_id] = parent_id

            except Exception as e:
                errors.append(f"Error reading row {excel_row}: {str(e)}")
                continue

        # Validation of structure
        if not errors:
            # Check for missing parents (only for non-root nodes)
            for child_id, parent_id in parents.items():
                if parent_id and parent_id not in ids:
                    errors.append(f"ID '{child_id}' references missing parent '{parent_id}'")

            # Detect cycles using a path-tracking approach
            def has_cycle(node_id, path=None):
                if path is None:
                    path = set()
                if node_id in path:
                    return True
                path.add(node_id)
                parent_id = parents.get(node_id)
                if parent_id is None:
                    return False
                result = has_cycle(parent_id, path)
                path.remove(node_id)
                return result

            # Check each node for cycles
            for node_id in ids:
                if has_cycle(node_id):
                    errors.append(f"Cycle detected in hierarchy involving ID '{node_id}'")

    except FileNotFoundError:
        errors.append(f"File not found: {excel_path}")
    except Exception as e:
        errors.append(f"Error reading Excel file: {str(e)}")

    return errors
