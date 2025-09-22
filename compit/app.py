import typer
from pathlib import Path
from typing import Optional, List

from openpyxl import Workbook
from ocx_common.parser.xml_document_parser import LxmlParser
from taxonomy.taxonomy import (visualize_clustered_taxonomy, visualize_taxonomy, visualize_with_plotly,
                               ocx_coverage_report, create_coverage_chart_mpl, doc_coverage_report,)
from taxonomy.mappings import end_to_end_coverage_report, model_coverage_report
from taxonomy.load_taxonomy import load_taxonomy, print_taxonomy, load_multiple_graphs
from taxonomy.validation import validate_taxonomy
from taxonomy.taxonomy_common import RancDir, TaxonomyFields
from taxonomy.ship_taxonomy import create_ship_pbs, write_excel
from taxonomy.ocx_taxonomy import OcxTaxonomy
from loguru import logger
from rich.table import Table
from rich.console import Console
# Remove all existing handlers
logger.remove()
# Add handler with INFO as minimum level
logger.add(sink=lambda msg: print(msg), level="DEBUG")

logger.enable("taxonomy")


def rich_table(table:dict, title:str='Table')-> None:
    rich_table = Table(title=title)
    # Columns
    right_justify = [2,3,4,5]
    dimensions = [key for key in table.keys()]
    headings = [*list(table.get(dimensions[0]).keys())]
    for i, col in enumerate(headings):
        if i in right_justify:
            rich_table.add_column(str(col), style="cyan", justify="right")
        else:
            rich_table.add_column(str(col), style="cyan", justify="left")
    #Rows
    for dim,data in table.items():
        rich_table.add_row(*[str(f"{data[col]:>10}") if str(data[col]).isalpha() else str(f"{data[col]}") for col in headings ])
    # Print table
    console = Console()
    console.print(rich_table)
def save_table_to_excel(table:dict, output_file:Path):

    wb = Workbook()
    ws = wb.active
    ws.title = "Coverage Report"
    # Write header
    dimensions = [key for key in table.keys()]
    headings = [*list(table.get(dimensions[0]).keys())]
    ws.append(headings)
    # Write data rows
    for dim, data in table.items():
        ws.append([data[col] for col in headings])
    # Save workbook
    wb.save(output_file)
    logger.info(f"Coverage report saved to {output_file}")

def print_schema_table(schema_dict: dict) -> None:
    """
    Print schema information in a formatted table using Rich.

    Args:
        schema_dict (dict): Dictionary containing schema information
    """
    table = Table(title="Schema Information")

    # Add columns
    table.add_column("Namespace", style="cyan")
    table.add_column("Version", style="magenta")
    table.add_column("Prefix", style="green")
    table.add_column("Elements", justify="right", style="blue")
    table.add_column("Complex Types", justify="right", style="blue")
    table.add_column("Simple Types", justify="right", style="blue")
    table.add_column("Attr Groups", justify="right", style="blue")
    table.add_column("Attributes", justify="right", style="blue")
    table.add_column("Enums", justify="right", style="blue")

    # Add rows
    for namespace, data in schema_dict.items():
        table.add_row(
            namespace,
            str(data['Version'][0]),
            str(data['Prefix'][0]),
            str(data['element'][0]),
            str(data['complexType'][0]),
            str(data['simpleType'][0]),
            str(data['attributeGroup'][0]),
            str(data['attribute'][0]),
            str(data['enumeration'][0])
        )

    # Print table
    console = Console()
    console.print(table)

app = typer.Typer()

@app.command()
def pbs(
    excel_file: Path = typer.Argument(
        "ship_pbs.xlsx",
        help="Path to the ship taxonomy output Excel file",
        exists=False,
        dir_okay=True,
    ),
    sheet: Optional[str] = typer.Option('psb', "--sheet", "-s", help="Sheet name")
) -> None:
    """
    Create the ship breakdown structure.
    """
    typer.echo(f"Creating shp product breakdown structure: {excel_file}")

    pbs = create_ship_pbs()
    write_excel(xlsx_bytes=pbs, xlsx_file=str(excel_file.resolve()))

    typer.echo("✅ Created PBS structure!")


@app.command()
def validate(
    excel_file: Path = typer.Argument(
        "taxonomy.xlsx",
        help="Path to the taxonomy Excel file",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    sheet: Optional[str] = typer.Option('taxonomy', "--sheet", "-s", help="Sheet name"),
    spell_check: bool = typer.Option(True, "--spell-check/--no-spell-check", "-sc/-nsc",
                                         help="Enable or disable spell checking")
    ) -> None:
    """
    Validate taxonomy Excel file for ID uniqueness, parent references, and cycles.
    """
    typer.echo(f"Validating taxonomy file: {excel_file}")

    errors = validate_taxonomy(excel_file, sheet_name=sheet, spell_check=spell_check)
    if errors:
        typer.echo("❌ Validation errors found:", err=True)
        for error in errors:
            typer.echo(f"  • {error}", err=True)
        raise typer.Exit(code=1)

    typer.echo("✅ Taxonomy is valid!")

@app.command()
def ocx_graph(
    url: str = typer.Argument(
        "https://3docx.org/fileadmin//ocx_schema//V310//OCX_Schema.xsd",
        help="URL to OCX schema version",
    ),
    schema_folder: Optional[Path] = typer.Option(
        "./schemas",
        help="Path to the schema download folder. "
             "The script will create it if it does not exist and download the schema files.",
        exists=True,
        dir_okay=True,),
    output: Optional[Path] = typer.Option(default='ocx_graph.xlsx',
                                             help="Save the OCX graph to an Excel file"),
    full_graph: bool = typer.Option(False, "--full/--no-full", "-f/-nf",
                              help="Build the full OCX graph hierarchy")
) -> None:
    """
    Create a graph of the OCX schema and save it to Excel.
    """
    typer.echo(f"Reading OCX schema from: {url}")

    try:
        ocx_taxonomy = OcxTaxonomy()
        ocx_taxonomy.transform_schema_from_url(url=url, folder=schema_folder)
        transformer = ocx_taxonomy.get_transformer()
        if transformer.is_transformed():
            typer.echo("✅ OCX Schema loaded and transformed successfully!")
            print_schema_table(transformer.parser.tbl_summary(short=True))
            # Build the taxonmy and save to file
            ocx_taxonomy.build_full_taxonomy_and_save_to_file(exel_file=output, full_graph=full_graph)
    except Exception as e:
        typer.echo(f"❌ Error loading taxonomy: {str(e)}", err=True)
        raise typer.Exit(code=1)

@app.command()
def tree(
    excel_file: Path = typer.Argument(
        "taxonomy.xlsx",
        help="Path to the taxonomy Excel file",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    drawings_only: bool = typer.Option(False, "--drawings", "-d", help="Show only drawings"),
    max_depth: Optional[int] = typer.Option(None, "--depth", "-l", help="Maximum depth level to display"),
    sheet: Optional[str] = typer.Option('taxonomy', "--sheet", "-s", help="Sheet name")

) -> None:
    """
    Display the taxonomy hierarchy in a tree structure.
    """
    typer.echo(f"Loading taxonomy from: {excel_file}")

    try:
        taxonomy = load_taxonomy(excel_file, sheet_name=sheet)
        print_taxonomy(
            taxonomy=taxonomy,
            doc_type_filter="Drawing" if drawings_only else None,
            max_depth=max_depth,
            current_depth=0  # Add initial depth
        )
    except Exception as e:
        typer.echo(f"❌ Error loading taxonomy: {str(e)}", err=True)
        raise typer.Exit(code=1)

@app.command()
def chart(
    excel_file: Path = typer.Argument(
        "taxonomy.xlsx",
        help="Path to the taxonomy Excel file",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    drawings_only: bool = typer.Option(False, "--drawings", "-d", help="Show only drawings"),
    show_depth: bool = typer.Option(False,   "--show-depth", "-sd", help="Include level numbers in chart"),
    sheet: Optional[str] = typer.Option('taxonomy', "--sheet", "-s", help="Sheet name"),
    row_id: Optional[str] = typer.Option(None, "--row-id", "-i",
                                help="Row ID to visualize (optional)"),
    exclude_id: bool = typer.Option(True, "--exclude-id/--include-id", "-ie/-ii", help="Exclude labels from chart"),
    color_field: TaxonomyFields = typer.Option(None, "--color-field", "-cf",
                                               help="Color graph nodes based on this fields values. Default is None "),
    depth: Optional[int] = typer.Option(None, "--depth", "-l",
                                            help="Maximum depth level to display"),
    direction: RancDir = typer.Option(RancDir.RL, help="Graph direction (TB, BT, LR, RL)"),
    ocx_name: bool = typer.Option(False, "--ocx-name/--no-ocx-name", "-on/-nn", help="Add the OCX element names to the chart"),
    chart_name: Optional[str] = typer.Option(default='taxonomy_chart',
                                             help="The name of the chart without file extension"),
    chart_folder: Optional[Path] = typer.Option(default='./charts',
                                                help="The name of the chart without file extension",
                                                dir_okay=True,
                                                ),

) -> None:
    """Generate a visual chart of the taxonomy hierarchy."""
    try:
        taxonomy = load_taxonomy(excel_path=excel_file, sheet_name=sheet, sub_graph=row_id, )
        typer.echo(f"✅ Taxonomy loaded successfully from {excel_file} (Sheet: {sheet})")
        output = chart_folder / chart_name
        if visualize_taxonomy(taxonomy=taxonomy, output_chart=str(output), show_depth=show_depth,
                              filter_reference="Drawing" if drawings_only else None,
                              max_depth=depth, exclude_id=exclude_id, rankdir=direction, color_field=color_field,
                              ocx_name=ocx_name):
            typer.echo(f"✅ Taxonomy chart created successfully using graphviz: Chart file: {output}")


    except Exception as e:
        typer.echo(message=f"❌ Error: {str(e)}", err=True)
        raise typer.Exit(1)

@app.command()
def cluster(
    excel_files: List[Path] = typer.Argument(
        help="List of Excel files with taxonomy data",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    drawings_only: bool = typer.Option(False, "--drawings", "-d", help="Show only drawings"),
    show_depth: bool = typer.Option(False,   "--show-depth", "-sd", help="Include level numbers in chart"),
    sheet: Optional[str] = typer.Option('taxonomy', "--sheet", "-s", help="Sheet name"),
    row_id: Optional[str] = typer.Option(None, "--row-id", "-i",
                                help="Row ID to visualize (optional)"),
    exclude_id: bool = typer.Option(True, "--exclude-id/--include-id", "-ie/-ii", help="Exclude labels from chart"),
    color_field: TaxonomyFields = typer.Option(None, "--color-field", "-cf",
                                               help="Color graph nodes based on this fields values. Default is None "),
    output: Optional[str] = typer.Option(default='taxonomy_chart',
                                help="Output file name for the chart without extension"),
    depth: Optional[int] = typer.Option(None, "--depth", "-l",
                                            help="Maximum depth level to display"),
    direction: RancDir = typer.Option(RancDir.RL, help="Graph direction (TB, BT, LR, RL)"),
    ocx_name: bool = typer.Option(False, "--ocx-name/--no-ocx-name", "-on/-nn", help="Add the OCX element names to the chart"),
    sub_graphs: Optional[List[str]] = typer.Option(None, "--sub-graphs", "-sg", help="List of row IDs to visualize as sub-graphs"),
) -> None:
    """Generate clustered graphs from several Excel files."""
    try:
        graphs = load_multiple_graphs(files=excel_files, sub_graphs=sub_graphs,sheet_name=sheet,)
        typer.echo(f"✅ Taxonomy loaded successfully from {excel_files} (Sheet: {sheet})")
        if visualize_clustered_taxonomy(graphs=graphs, output_chart=output, show_depth=show_depth,
                              doc_type_filter="Drawing" if drawings_only else None,
                              max_depth=depth, exclude_id=exclude_id, rankdir=direction, color_field=color_field,
                              ocx_name=ocx_name):
            typer.echo(f"✅ Taxonomy chart created successfully using graphviz: Chart file: {output}")


    except Exception as e:
        typer.echo(message=f"❌ Error: {str(e)}", err=True)
        raise typer.Exit(1)


@app.command()
def plotly(
    excel_files: List[Path] = typer.Argument(
        help="List of Excel files with taxonomy data",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    output: Optional[str] = typer.Option(default='taxonomy_chart',
                                             help="Output file name for the chart without extension"),

) -> None:
    """Generate interactive plotly charts from several Excel files."""
    try:
        graphs = load_multiple_graphs(files=excel_files)
        typer.echo(f"✅ Taxonomy loaded successfully from {excel_files}")
        visualize_with_plotly(graphs=graphs, output_file=output)
    except Exception as e:
        typer.echo(message=f"❌ Error: {str(e)}", err=True)
        raise typer.Exit(1)

@app.command()
def ocx_coverage(
    source: Path = typer.Argument(
        help="Source taxonomy with mappings",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    url: Optional[str] = typer.Option(
        "https://3docx.org/fileadmin//ocx_schema//V310//OCX_Schema.xsd",
        help="URL to OCX schema version",
    ),
    schema_folder: Optional[Path] = typer.Option(
        "./schemas",
        help="Path to the schema download folder. "
             "The script will create it if it does not exist and download the schema files.",
        exists=True,
        dir_okay=True,
    ),
    dimensions:List[str] =typer.Option(help="List of dimension fields to consider for coverage",

                                         default=["cargoes", "design_loads", "library_reference",
                                                  "location_concepts", "product_structures", "shapes",
                                                  "ship_general_characteristics", "ship_material_properties",
                                                  "ship_measures", "spaces", "structural_features", "structural_parts",
                                                  "structural_systems", "welds"]),
    chart_name: Optional[str] = typer.Option(default='ocx_shema_coverage_chart',
                                              help="The name of the chart without file extension"),
    chart_folder: Optional[Path] = typer.Option(default='./charts',
                                                 help="The name of the chart without file extension",
                                                dir_okay=True,
                                                ),
        chart_title: Optional[str] = typer.Option(default='OCX protocol coverage of taxonomy Uofs',
                                                  help="The title of the chart"),

        save_report: bool = typer.Option(True, "--save-report/--no-report", "-sr/-nr",
                                         help="Save the coverage report to an Excel file")

) -> None:
    """Report mapping coverage."""
    try:
        graph = load_taxonomy(excel_path=source)
        typer.echo(f"✅ Taxonomy loaded successfully from {source}")
        # Load OCX schema as target
        typer.echo(f"Reading OCX schema from: {url}")
        parser = OcxTaxonomy()
        parser.transform_schema_from_url(url=url, folder=schema_folder)
        transformer = parser.get_transformer()
        report, aggregated = ocx_coverage_report(source=graph, target=transformer, dimensions=dimensions)
        rich_table(report)
        typer.echo(f'Total: {aggregated[0]}, Mapped: {aggregated[1]}, Not mapped: {aggregated[2]}, Coverage: {(aggregated[1]/aggregated[0])*100:.2f}%')
        # Create the coverage chart
        output_file = str(chart_folder / f"{chart_name}.png")
        create_coverage_chart_mpl(data=report, title=chart_title,output_file=output_file)
        typer.echo(f"✅ Coverage chart created successfully: {output_file}")
        if save_report:
            excel_file = chart_folder / f"{chart_name}.xlsx"
            save_table_to_excel(table=report, output_file=excel_file)
            typer.echo(f"✅ Coverage report saved to file: {excel_file}")
    except Exception as e:
        typer.echo(message=f"❌ Error: {str(e)}", err=True)
        raise typer.Exit(1)

@app.command()
def doc_coverage(
    source: Path = typer.Argument(
        help="Source taxonomy with mappings",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    target: Path = typer.Argument(
        help="Source taxonomy with mappings",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
        chart_name: Optional[str] = typer.Option(default='docreq_coverage_chart',
                                                 help="The name of the chart without file extension"),
        chart_folder: Optional[Path] = typer.Option(default='./charts',
                                                    help="The folder to save the chart to",
                                                    dir_okay=True,
                                                    ),
        chart_title: Optional[str] = typer.Option(default='DocReq taxonmomy coverage per drawing',
                                                  help="The title of the chart"),

        dimensions:List[str] =typer.Option(help="List of dimension fields to consider for coverage",
                                       default=["H050","H020", "H030", "H040", "H041", "H052", "H053", "H060", "H061", "H062",
                                                "H070", "H120", "H133", "H134", "H210", "H220", "H230",
                                                #"H050.01", "H050.02", "H050.03", "H050.04", "H050.05", "H050.06", "H050.07","H050.08"
                                                ]),
        save_report: bool = typer.Option(True, "--save-report/--no-report", "-sr/-nr",
                                     help="Save the coverage report to an Excel file"),

) -> None:
    """Report mapping coverage."""
    try:
        graphs = load_multiple_graphs(files=[source, target])
        typer.echo(f"✅ Taxonomy loaded successfully from {source}")
        report, aggregated = doc_coverage_report(source=graphs[0], target=graphs[1], dimensions=dimensions)
        rich_table(report)
        typer.echo(f'Total: {aggregated[0]}, Mapped: {aggregated[1]}, Not mapped: {aggregated[2]}, Coverage: {(aggregated[1]/aggregated[0])*100:.2f}%')
        # Create the coverage chart
        output_file = str(chart_folder / f"{chart_name}.png")
        create_coverage_chart_mpl(data=report, title=chart_title,output_file=output_file)
        typer.echo(f"✅ Coverage chart created successfully:{output_file}.png")
        # Save the report to Excel
        if save_report:
            excel_file = chart_folder / f"{chart_name}.xlsx"
            save_table_to_excel(table=report, output_file=excel_file)
            typer.echo(f"✅ Coverage report saved to file: {excel_file}")
    except Exception as e:
        typer.echo(message=f"❌ Error: {str(e)}", err=True)
        raise typer.Exit(1)

@app.command()
def end_to_end_coverage(
    doc_req: Path = typer.Argument(
        help="DocReq with mappings to taxonomy",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    taxonomy: Path = typer.Argument(
        help="Source taxonomy with mappings to OCX",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    url: Optional[str] = typer.Option(
        "https://3docx.org/fileadmin//ocx_schema//V310//OCX_Schema.xsd",
        help="URL to OCX schema version",
    ),
    schema_folder: Optional[Path] = typer.Option(
        "./schemas",
        help="Path to the schema download folder. "
             "The script will create it if it does not exist and download the schema files.",
        exists=True,
        dir_okay=True,
    ),
    dimensions:List[str] =typer.Option(help="List of dimension fields to consider for coverage",
                                       default=["H050", "H020", "H030", "H040", "H041", "H052", "H053", "H060", "H061",
                                                "H062",
                                                "H070", "H120", "H133", "H134", "H210", "H220", "H230",
                                                # "H050.01", "H050.02", "H050.03", "H050.04", "H050.05", "H050.06", "H050.07","H050.08"
                                                ]),
        chart_name: Optional[str] = typer.Option(default='end_to_end_coverage_chart',
                                                 help="The name of the chart without file extension"),
        chart_folder: Optional[Path] = typer.Option(default='./charts',
                                                    help="The name of the chart without file extension",
                                                    dir_okay=True,
                                                    ),
        chart_title: Optional[str] = typer.Option(default='OCX protocol coverage per drawing',
                    help="The title of the chart"),
        save_report: bool = typer.Option(True, "--save-report/--no-report", "-sr/-nr",
                                         help="Save the coverage report to an Excel file")

) -> None:
    """Report mapping coverage."""
    try:
        graphs = load_multiple_graphs(files=[doc_req, taxonomy])
        typer.echo(f"✅ Taxonomy loaded successfully from {[doc_req, taxonomy]}")
        typer.echo(f"Reading OCX schema from: {url}")
        parser = OcxTaxonomy()
        parser.transform_schema_from_url(url=url, folder=schema_folder)
        transformer = parser.get_transformer()
        report, aggregated = end_to_end_coverage_report(doc_req=graphs[0], taxonomy=graphs[1], ocx_schema=transformer, dimensions=dimensions)
        rich_table(report)
        typer.echo(f'Total: {aggregated[0]}, Mapped: {aggregated[1]}, Not mapped: {aggregated[2]}, Coverage: {(aggregated[1]/aggregated[0])*100:.2f}%')
        # Create the coverage chart
        output_file = str(chart_folder / f"{chart_name}.png")
        create_coverage_chart_mpl(data=report, title=chart_title,output_file=output_file,axis_label='Dimension')
        typer.echo(f"✅ Coverage chart created successfully: {output_file}")
        # Save the report to Excel
        if save_report:
            excel_file = chart_folder / f"{chart_name}.xlsx"
            save_table_to_excel(table=report, output_file=excel_file)
            typer.echo(f"✅ Coverage report saved to file: {excel_file}")
    except Exception as e:
        typer.echo(message=f"❌ Error: {str(e)}", err=True)
        raise typer.Exit(1)


@app.command()
def model_coverage(
    doc_req: Path = typer.Argument(
        help="DocReq with mappings to taxonomy",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    taxonomy: Path = typer.Argument(
        help="Source taxonomy with mappings to OCX",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    ocx_model: Path = typer.Argument(
        help="Path to the local 3D OCX model file",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    dimensions:List[str] =typer.Option(help="List of dimension fields to consider for coverage",
                                       default=["H050", "H020", "H030", "H040", "H041", "H052", "H053", "H060", "H061",
                                                "H062",
                                                "H070", "H120", "H133", "H134", "H210", "H220", "H230",
                                                # "H050.01", "H050.02", "H050.03", "H050.04", "H050.05", "H050.06", "H050.07","H050.08"
                                                ]),
    chart_name: Optional[str] = typer.Option(default='ocx_3Dmodel_coverage_chart',
                                             help="The name of the chart without file extension"),
    chart_folder: Optional[Path] = typer.Option(default='./charts',
                                                help="The name of the chart without file extension",
                                                dir_okay=True,
                                                ),
    chart_title: Optional[str] = typer.Option(default='3D model coverage per drawing',
                                                  help="The title of the chart"),
    save_report: bool = typer.Option(True, "--save-report/--no-report", "-sr/-nr",
                                         help="Save the coverage report to an Excel file")

) -> None:
    """3D model DoCReq coverage."""
    try:
        graphs = load_multiple_graphs(files=[doc_req, taxonomy])
        typer.echo(f"✅ Taxonomy loaded successfully from {[doc_req, taxonomy]}")
        parser = LxmlParser()
        parser.parse(str(ocx_model.absolute()))
        report, aggregated = model_coverage_report(doc_req=graphs[0], taxonomy=graphs[1], parser=parser, dimensions=dimensions)
        rich_table(report)
        typer.echo(f'Total: {aggregated[0]}, Mapped: {aggregated[1]}, Not mapped: {aggregated[2]}, Coverage: {(aggregated[1]/aggregated[0])*100:.2f}%')
        # Create the coverage chart
        output_file = chart_folder / f"{chart_name}.png"
        create_coverage_chart_mpl(data=report, axis_label="Title", title=chart_title,output_file=str(output_file))
        typer.echo(f"✅ Coverage chart created successfully: {output_file}")
        if save_report:
            excel_file = chart_folder / f"{chart_name}.xlsx"
            save_table_to_excel(table=report, output_file=excel_file)
            typer.echo(f"✅ Coverage report saved to file: {excel_file}")
    except Exception as e:
        typer.echo(message=f"❌ Error: {str(e)}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()