# Tesselate
### An exploratory repo for testing tesselation and handling of mutiple nurbs pathces

### Triangle Mesh Generation 

[**Triangle**](https://www.cs.cmu.edu/~quake/triangle.html)  generates exact Delaunay triangulations, constrained Delaunay triangulations, conforming Delaunay triangulations, Voronoi diagrams, and high-quality triangular meshes developed by Jonathan Richard Shewchuk.

#### Python wrapper for Triangle

[*Triangle*](https://rufat.be/triangle/) Triangle is a python wrapper around Jonathan Richard Shewchuk’s two-dimensional quality mesh generator.

Test it by running the following script:

```python
  uv run triangle_tests.py
```

It will produce this picture:
![Triangle Mesh](triangle_test.png)

### Multiple NURBS patches

#### Mathematical foundation and pseudo code

See the full documentation here:
[**TrimmedSplineProjector**]( TrimmedSplineProjector.md)

#### Example usage

Run the python script:

```python
  uv run multi_nurbs_intersectioning.py
```
The script includes the full implementation of the pipeline and will produce this plot:
![NURBS intersection](multi_surface_patch_test.png)