import os
os.environ['GDAL_DATA'] = r'C:\Users\alvar\anaconda3\envs\storcito\Library\share\gdal'
import sys
import time
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import rasterio

from FR.rutinas.setup import default_imshow, save_file
import numpy.typing as npt
from pathlib import Path
from rasterio.features import rasterize
from rasterio.transform import from_bounds
from shapely.geometry.base import BaseGeometry
import numpy as np

# sys.path.append(r'..\geo_auxy')


def infra_from_array(
    distance_arr: npt.NDArray,
    radii: list[int] | None = None,
    risks: list[int] | None = None
) -> npt.NDArray:
    """Classify infrastructure proximity risk from a distance array.

    Reclassifies a distance-to-infrastructure array into risk categories
    based on distance thresholds.

    Args:
        distance_arr: 2D array with distance values to nearest infrastructure (meters).
        radii: Distance thresholds in meters. Defaults to [250, 500, 750, 1000, 1250].
        risks: Risk values for each distance band. Defaults to [5, 4, 3, 2, 1].

    Returns:
        2D array (float32) with risk categories. Values beyond max radius are np.nan.

    Example:
        >>> dist = compute_distance_to_roads(roads_gdf, shape, transform)
        >>> risk = infra_from_array(dist)
    """
    if radii is None:
        radii = [250, 500, 750, 1000, 1250]
    if risks is None:
        risks = [5, 4, 3, 2, 1]

    conditions = []
    for i, r in enumerate(radii):
        if i == 0:
            conditions.append(distance_arr <= r)
        else:
            conditions.append((distance_arr > radii[i - 1]) & (distance_arr <= r))

    return np.select(conditions, risks, default=np.nan).astype(np.float32)


def infra_from_gdf(
    gdf: gpd.GeoDataFrame,
    shape: tuple[int, int],
    transform,
    radii: list[int] | None = None,
    risks: list[int] | None = None
) -> npt.NDArray:
    """Rasterize infrastructure GeoDataFrame into risk categories.

    Creates concentric buffer rings around infrastructure features and
    rasterizes them into risk values.

    Args:
        gdf: GeoDataFrame with infrastructure geometries (lines/polygons).
        shape: Output raster shape as (height, width).
        transform: Affine transform for the output raster.
        radii: Buffer radii in meters. Defaults to [250, 500, 750, 1000, 1250].
        risks: Risk values for each buffer. Defaults to [5, 4, 3, 2, 1].

    Returns:
        2D array (float32) with risk categories (1-5). Areas beyond max
        buffer distance are set to np.nan.
    """
    if radii is None:
        radii = [250, 500, 750, 1000, 1250]
    if risks is None:
        risks = [5, 4, 3, 2, 1]

    # Union all geometries
    geom_union = gdf.geometry.union_all()

    # Create risk rings
    anillos = _create_risk_rings(geom_union, radii, risks)
    anillos.crs = gdf.crs

    # Rasterize with 0 as fill, then replace with np.nan
    geoms = ((geom, val) for geom, val in zip(anillos.geometry, anillos['risk']))
    raster_data = rasterize(
        geoms,
        out_shape=shape,
        transform=transform,
        fill=0,
        dtype=np.float32,
        all_touched=True
    )

    # Replace fill value with np.nan
    raster_data[raster_data == 0] = np.nan

    return raster_data


def _create_risk_rings(geometry: BaseGeometry, radii: list[int], risks: list[int]) -> gpd.GeoDataFrame:
    """Crea anillos concéntricos de riesgo alrededor de geometría.
    
    Args:
        geometry: Geometría unificada (buffer inicial)
        radii: Lista de radios para los buffers en metros
        risks: Lista de valores de riesgo correspondientes
        
    Returns:
        GeoDataFrame con geometría de anillos y valores de riesgo
    """
    buffers = [geometry.buffer(r) for r in radii]
    anillos_data = []
    
    for i, (buff, risk) in enumerate(zip(buffers, risks)):
        # Primer anillo es el buffer completo, resto son diferencias
        anillo = buff if i == 0 else buff.difference(buffers[i-1])
        
        if not anillo.is_empty:
            anillos_data.append({'geometry': anillo, 'risk': risk})
    
    return gpd.GeoDataFrame(anillos_data)

def infrastructure(input_infra: str|Path,
                   output_folder: str|Path = Path('OUTPUT'),
                   ref_raster: str|Path = Path(r'REFERENCE\MDT\DEM_NationalScenario_2013.tif'),
                   epsg: int = 32629,
                   export_image: bool = False,
                   show_plots: bool = False,
                   simplify: bool = False,
                   tolerance: int = 10) -> npt.NDArray:
    """Calculate infrastructure proximity risk from roads and railways.

    Creates concentric buffer rings around infrastructure features and assigns
    decreasing risk values (5 to 1) based on distance (250m to 1250m).

    Args:
        input_infra: Path to infrastructure shapefile (roads/railways)
        output_folder: Output directory for results. Defaults to 'OUTPUT'
        ref_raster: Reference raster for extent and resolution. Defaults to DEM
        epsg: Target CRS EPSG code. Defaults to 32629 (UTM 29N)
        export_image: Whether to save results as GeoTIFF/PNG. Defaults to False
        show_plots: Whether to display matplotlib plots. Defaults to False
        simplify: Whether to simplify geometries for performance. Defaults to False
        tolerance: Simplification tolerance in meters. Defaults to 10

    Returns:
        Rasterized risk array with values 0-5 (0=no infrastructure nearby)

    Raises:
        FileNotFoundError: If input shapefile or reference raster not found
    """
    
    # Validar y convertir paths

    input_infra = Path(input_infra)
    output_folder = Path(output_folder)
    ref_raster = Path(ref_raster)
    
    # Validar existencia de archivos
    if not input_infra.exists():
        raise FileNotFoundError(f"Archivo de infraestructura no encontrado: {input_infra}")
    if not ref_raster.exists():
        raise FileNotFoundError(f"Raster de referencia no encontrado: {ref_raster}")
    
    # Leer y reproyectar infraestructuras
    road = gpd.read_file(input_infra).to_crs(epsg=epsg)
    
    # Simplificar geometrías si se solicita
    if simplify:
        road['geometry'] = road.geometry.simplify(tolerance=tolerance)

    
    # Unión de todas las infraestructuras en una geometría única
    road_union = road.geometry.union_all()
    
    # Crear anillos de riesgo concéntricos
    radii = [250, 500, 750, 1000, 1250]
    risks = [5, 4, 3, 2, 1]
    anillos = _create_risk_rings(road_union, radii, risks)
    anillos.crs = road.crs
    
    # Obtener parámetros de rasterización del raster de referencia
    with rasterio.open(ref_raster) as src:
        bounds = src.bounds
        x_min, y_min, x_max, y_max = bounds.left, bounds.bottom, bounds.right, bounds.top
    
    x_res = int((x_max - x_min) / 25)
    y_res = int((y_max - y_min) / 25)
    transform = from_bounds(x_min, y_min, x_max, y_max, x_res, y_res)

    
    # 6. Rasterizar

    geoms = ((geom, val) for geom, val in zip(anillos.geometry, anillos['risk']))
    raster_data = rasterize(
        geoms, 
        out_shape=(y_res, x_res), 
        transform=transform, 
        fill=0, 
        dtype=rasterio.uint8,
        all_touched=True
    )
    
    # Configuración de metadatos para guardar
    meta_info = {
        'driver': 'GTiff', 
        'height': y_res, 
        'width': x_res, 
        'count': 1,
        'dtype': rasterio.uint8, 
        'crs': anillos.crs, 
        'transform': transform,
        'compress': 'lzw'
    }
    

    # Visualizar resultado
    fig1, ax1 = default_imshow(raster_data, 'Roads and Railways Risk Map', {'label': 'Risk'})
    fig1.set_size_inches((12, 8))

    if show_plots:
        plt.show()
    
    # Guardar archivos si se solicita
    if export_image:

        save_file(raster_data, meta_info, input_infra.stem, output_folder, 'INFRA Risk_Map',extensions=['tif','png'] ,fig=fig1, meta_intact=True)
    
    return raster_data



if __name__=='__main__':
    
    import cProfile
    import pstats

    with cProfile.Profile() as profile:
        infrastructure(r'INPUT\infraestructuras_gal.shp',
            export_image=False)

    results = pstats.Stats(profile)
    results.sort_stats(pstats.SortKey.TIME)
    results.print_stats(20)

