@echo off
REM Batch script to create all the charts

REM Fig 3
uv run app.py ocx-coverage .\source_taxonomy\ship_hull_taxonomy_AP218.xlsx --chart-name Fig_3 --chart-title "OCX protocol coverage of taxonomy UoFs"
REM Fig 4
uv run app.py chart .\source_taxonomy\ship_hull_taxonomy_AP218.xlsx --chart-name fig_4a --direction LR -cf reference
uv run app.py chart .\source_taxonomy\ship_hull_taxonomy_AP218.xlsx --chart-name fig_4b --direction TB -cf reference --row-id structural_parts
REM Fig 8
uv run app.py chart .\source_taxonomy\docreq_taxonomy_drawings_only.xlsx --chart-name fig_8 --direction LR -cf reference
REM Fig 9
uv run app.py doc-coverage .\source_taxonomy\docreq_taxonomy_drawings_only.xlsx .\source_taxonomy\ship_hull_taxonomy_AP218.xlsx --chart-name Fig_9 --chart-title "Taxonomy coverage of document requirements"
REM Fig 10
uv run app.py end-to-end-coverage .\source_taxonomy\docreq_taxonomy_drawings_only.xlsx .\source_taxonomy\ship_hull_taxonomy_AP218.xlsx --chart-name Fig_10 --chart-title "OCX protocol coverage per drawing"
REM Fig 12
uv run app.py model-coverage .\source_taxonomy\docreq_taxonomy_drawings_only.xlsx .\source_taxonomy\ship_hull_taxonomy_AP218.xlsx .\models\ropax.3docx --chart-name Fig_12 --chart-title "3D model coverage of DNV documentation requirements"