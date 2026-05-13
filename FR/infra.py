import os
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import rasterio
from rasterio.features import rasterize

def infrastructure(input_infra, output_infra):
    print('Processing Infrastructure Layer...')
    while True:
        save_answer = input("Do you want to save the infrastructure risk map? (y/n): ").strip().lower()
        if save_answer in ('y','n'): break
        print("Please enter 'y' or 'n'.")

    road = gpd.read_file(input_infra)
    road_re = road.to_crs(epsg=32629)

    # Create multirings (concentric rings without overlap)
    radii = [250, 500, 750, 1000, 1250]
    risks = [5, 4, 3, 2, 1]
    
    ring_data = []
    prev_buffer = None
    
    for outer_r, risk in zip(radii, risks):
        outer_buffer = road_re.buffer(outer_r).unary_union
        
        if prev_buffer is None:
            # First ring: 0 to 250m
            ring = outer_buffer
        else:
            # Subsequent rings: difference between outer and inner buffers
            ring = outer_buffer.difference(prev_buffer)
        
        if not ring.is_empty:
            ring_data.append({'geometry': ring, 'risk': risk})
        
        prev_buffer = outer_buffer
    
    rings = gpd.GeoDataFrame(ring_data, crs=road_re.crs)

    # Obtain limits and rasterization parameters
    archivo_raster = r'C:\Users\Mateo G\Desktop\STORCITO\Fotos\MDT\DEM_NationalScenario_2013.tif'
    with rasterio.open(archivo_raster) as src:
        bounds = src.bounds
        x_min, y_min, x_max, y_max = bounds.left, bounds.bottom, bounds.right, bounds.top

    x_res = int((x_max - x_min) / 25)
    y_res = int((y_max - y_min) / 25)
    transform = rasterio.transform.from_bounds(x_min, y_min, x_max, y_max, x_res, y_res)

    # Rasterize directly in memory
    geoms = ((geom, val) for geom, val in zip(rings.geometry, rings['risk']))
    raster_data = rasterize(geoms, out_shape=(y_res, x_res), transform=transform, fill=0, dtype=rasterio.uint8)

    # Prepare directories and paths
    rasters_dir = r'C:\Users\Mateo G\Desktop\STORCITO\Salida Datos\re'
    png_dir = r'C:\Users\Mateo G\Desktop\STORCITO\Salida Datos\INFRA'
    base_name = os.path.splitext(os.path.basename(output_infra))[0]
    raster_path = os.path.join(rasters_dir, f'{base_name}.tif')
    png_path = os.path.join(png_dir, f'{base_name}.png')
    
    if save_answer == 'y':
        os.makedirs(rasters_dir, exist_ok=True)
        os.makedirs(png_dir, exist_ok=True)

    # Save rasters once
    with rasterio.open(raster_path, 'w', driver='GTiff', height=y_res, width=x_res, count=1,
                       dtype=rasterio.uint8, crs=rings.crs.to_string(), transform=transform) as dst:
        dst.write(raster_data, 1)
    
    # Save also in output_infra for compatibility
    try:
        with rasterio.open(output_infra, 'w', driver='GTiff', height=y_res, width=x_res, count=1,
                           dtype=rasterio.uint8, crs=rings.crs.to_string(), transform=transform) as dst:
            dst.write(raster_data, 1)
    except Exception:
        pass

    # Visualize and save PNG if requested
    plt.imshow(raster_data, cmap='Reds')
    plt.colorbar()
    plt.title('Infrastructure Risk Map')
    
    if save_answer == 'y':
        plt.savefig(png_path, dpi=300, bbox_inches='tight')
        print(f'Infrastructure Layer completed and saved. TIFF: {raster_path}; PNG: {png_path}')
    else:
        print('Infrastructure Layer completed without saving.')
    
    plt.show()
    return
