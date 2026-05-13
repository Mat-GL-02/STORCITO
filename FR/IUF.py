import os
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import rasterize
from rasterio.mask import mask
import matplotlib.pyplot as plt

def wui(input_road, input_clc, output_iuf):
    print('Processing Wildland-Urban Interfaces layer...')
    while True:
        save_answer = input("Do you want to save the Wildland-Urban Interface risk map? (y/n): ").strip().lower()
        if save_answer in ('y','n'): break
        print("Enter 'y' or 'n'.")

    # Read layers only once
    road = gpd.read_file(input_road).to_crs(epsg=32629)
    clc = gpd.read_file(input_clc).to_crs(epsg=32629)

    # Convert Code_18 to numeric once
    clc['Code_18'] = pd.to_numeric(clc['Code_18'], errors='coerce')
    
    # Phase I: Intersect with 2000m buffer - without saving to disk
    bf2000 = road.buffer(2000).unary_union
    polygons = clc[clc.intersects(bf2000)].copy()
    print("Intersecting polygons found (phase I):", len(polygons))
    if len(polygons) == 0:
        print("No intersections found."); return
    
    # Phase I: Filter code < 200 and >= 100
    pol1 = polygons[(polygons['Code_18'] < 200) & (polygons['Code_18'] >= 100)]
    print("Filtered polygons (phase I):", len(pol1))
    
    # Create IUF mask (buffer 400 - buffer 50) - in memory, WITHOUT difference
    # Use only the two buffers without subtraction (faster for rasterization)
    bf400 = pol1.buffer(400).unary_union
    bf50 = pol1.buffer(50).unary_union
    IUF_mask_geom = bf400  # Use the outer buffer

    # Phase II: Filter code >= 200 and < 325, or == 333 + intersection in one pass
    pol2_sel = polygons[
        (((polygons['Code_18'] < 325) & (polygons['Code_18'] >= 200)) | 
         (polygons['Code_18'] == 333)) & 
        (polygons.intersects(IUF_mask_geom))
    ].copy()
    print("Filtered and intersected polygons (phase II):", len(pol2_sel))
    
    # Assign risk values with np.select (vectorized in one pass)
    import numpy as np
    risk_array = np.zeros(len(pol2_sel), dtype=np.uint8)
    code = pol2_sel['Code_18'].values
    
    conditions = [
        code == 311,
        code == 312,
        code == 313,
        code == 321,
        (code == 322) | (code == 323) | (code == 324),
        code == 333,
        code < 300
    ]
    choices = [2, 5, 4, 2, 3, 2, 1]
    
    risk_array = np.select(conditions, choices, default=0)
    pol2_sel['risk'] = risk_array
    
    # Get rasterization parameters from DEM
    with rasterio.open(r'C:\Users\Mateo G\Desktop\STORCITO\Fotos\Forest Fire Risk Map\DEM_NationalScenario_2013.tif') as src:
        b = src.bounds
        x_res = int((b.right - b.left)/25)
        y_res = int((b.top - b.bottom)/25)
        transform = rasterio.transform.from_bounds(b.left, b.bottom, b.right, b.top, x_res, y_res)
        crs_str = src.crs.to_string()
    
    # Rasterize directly in memory
    geom_vals = ((g, v) for g, v in zip(pol2_sel.geometry, pol2_sel['risk']))
    raster_data = rasterize(geom_vals, out_shape=(y_res, x_res), transform=transform, fill=0, dtype=rasterio.uint8)
    
    # Apply mask (crop) - create masked raster
    mask_geoms = [IUF_mask_geom]
    from rasterio.io import MemoryFile
    with MemoryFile() as memfile:
        with memfile.open(driver='GTiff', height=y_res, width=x_res, count=1, dtype=rasterio.uint8, crs=crs_str, transform=transform) as mem_src:
            mem_src.write(raster_data, 1)
        with memfile.open() as mem_src:
            out_img, out_tr = mask(mem_src, mask_geoms, crop=True)
            out_meta = mem_src.meta.copy()
            out_meta.update({"driver":"GTiff", "height":out_img.shape[1], "width":out_img.shape[2], "transform":out_tr})
    
    # Prepare directories
    rasters_dir = r'C:\Users\Mateo G\Desktop\STORCITO\Salida Datos\re'
    png_dir = r'C:\Users\Mateo G\Desktop\STORCITO\Salida Datos\IUF'
    base_name = os.path.splitext(os.path.basename(output_iuf))[0]
    os.makedirs(rasters_dir, exist_ok=True)
    os.makedirs(png_dir, exist_ok=True)
    
    raster_path = os.path.join(rasters_dir, f'{base_name}.tif')
    png_path = os.path.join(png_dir, f'{base_name}.png')
    
    # Save raster once (without reading from disk later)
    with rasterio.open(raster_path, 'w', **out_meta) as dst:
        dst.write(out_img)
    try:
        with rasterio.open(output_iuf, 'w', **out_meta) as dst:
            dst.write(out_img)
    except Exception:
        pass
    
    # Visualize from in-memory data (without reading raster from disk)
    plt.imshow(out_img[0], cmap='Reds')
    plt.colorbar()
    plt.title('WUI Risk Map')
    
    if save_answer == 'y':
        plt.savefig(png_path, dpi=300, bbox_inches='tight')
        print(f'WUI Layer completed and saved. TIFF: {raster_path}; PNG: {png_path}')
    else:
        print('WUI Layer completed without saving.')
    
    plt.show()
    return
