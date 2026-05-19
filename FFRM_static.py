import sys
# Make sure the path to your modules is correct
sys.path.append(r'C:\Users\Mateo G\Desktop\STORCITO\Codigos\FR_Gal\FR')

import numpy as np
import shutil
import os
import matplotlib.pyplot as plt

# Import the necessary rasterio tools
from rasterio.fill import fillnodata
from rasterio.warp import reproject, Resampling
import rasterio

# Import personalized modules
import FR.FMT_eu as Fmt
import FR.MDT as Mdt
import FR.IUF as Wui
import FR.infra as Infra
import FR.FWI as Fwi
import FR.TWI as Twi
import FR.cropped as Cropped
from FR.ahp import normalize_matrix, calculate_weights, consistency_ratio

# ==========================================
# 1. LAYER GENERATION
# ==========================================

# ---------------------------
# 1.1. INPUT PATHS
# ---------------------------

# DTM
input_mdt = r'C:\Users\Mateo G\Desktop\STORCITO\Fotos\DTM\DTM.tif'
input_slope = r'C:\Users\Mateo G\Desktop\STORCITO\Fotos\DTM\SLOPE.tif'
input_aspect = r'C:\Users\Mateo G\Desktop\STORCITO\Fotos\DTM\ASPECT.tif'

# TWI
input_twi = r'C:\Users\Mateo G\Desktop\STORCITO\Fotos\TWI\TWI.tif'

# Fuels (FMT)
input_fmt = r'C:\Users\Mateo G\Desktop\STORCITO\Fotos\FUELS\FMT_NationalScenario_2019.tif'

# Infrastructure & WUI
input_infra = r'C:\Users\Mateo G\Desktop\STORCITO\Fotos\INFRA\galicia_entera.shp'
input_clc = r'C:\Users\Mateo G\Desktop\STORCITO\Fotos\IUF\CLC_galicia.shp'

# Meteorology (FWI)
input_fwi_folder = r'C:\Users\Mateo G\Desktop\STORCITO\Fotos\FWI'

# ---------------------------
# 1.2. OUTPUT FOLDERS
# ---------------------------

output_folder_re = r'C:\Users\Mateo G\Desktop\STORCITO\Salida Datos\re'
output_folder_cropped = r'C:\Users\Mateo G\Desktop\STORCITO\Salida Datos\Cropped'

os.makedirs(output_folder_re, exist_ok=True)
os.makedirs(output_folder_cropped, exist_ok=True)

# ---------------------------
# 1.3. BASE OUTPUT RASTERS
# ---------------------------

output_mdt   = os.path.join(output_folder_re, 'MDT.tif')
output_slope = os.path.join(output_folder_re, 'SLOPE.tif')
output_aspect= os.path.join(output_folder_re, 'ASPECT.tif')

output_twi      = os.path.join(output_folder_re, 'twi.tif')
output_twi_risk = os.path.join(output_folder_re, 'twi_risk_map.tif')

output_fmt   = os.path.join(output_folder_re, 'FMT.tif')
output_infra = os.path.join(output_folder_re, 'infra_layer.tif')
output_wui   = os.path.join(output_folder_re, 'WUI.tif')
output_fwi   = os.path.join(output_folder_re, 'FWI.tif')

# ---------------------------
# 1.4. EXECUTION CONTROL
# ---------------------------

run_mdt   = True
run_twi   = False  
run_fmt   = False
run_infra = False
run_wui   = False
run_fwi   = False

# Data for FWI avaliable from september 2021
use_fwi = True

# ---------------------------
# 1.5. LAYER GENERATION
# ---------------------------

if run_mdt:
    Mdt.mdt(
        input_mdt,
        input_slope,
        input_aspect,
        output_mdt,
        output_slope,
        output_aspect
    )

if run_twi:
    Twi.Twi(
        input_twi,
        output_twi
    )

if run_fmt:
    Fmt.fmt(
        input_fmt,
        output_fmt
    )

if run_infra:
    Infra.infrastructure(
        input_infra,
        output_infra
    )

if run_wui:
    Wui.wui(
        input_infra,
        input_clc,
        output_wui
    )

if run_fwi:
    Fwi.f_w_index(
        input_fwi_folder,
        output_fwi
    )

print("Todas las capas base del caso estático generadas/disponibles en 're\\'.")

# ==========================================
# 2. CROP WITH BUFFER (Cropped Folder)
# ==========================================
print("\nStarting crop of layers to the study area...")
output_folder_re = r'C:\Users\Mateo G\Desktop\STORCITO\Salida Datos\re'
output_folder_cropped = r'C:\Users\Mateo G\Desktop\STORCITO\Salida Datos\Cropped'
shapefile_for_buffer = r'C:\Users\Mateo G\Desktop\STORCITO\Fotos\shapefile\Galicia.shp'
buffer_distance = 3000

Cropped.cropped(output_folder_re, output_folder_cropped, shapefile_for_buffer, buffer_distance)

# ==========================================
# 3. ALIGNMENT AND LOGICAL TREATMENT OF GAPS
# ==========================================
print("\nAligning layers and processing missing data...")

def align_raster_with_resampling(source_path, reference_path):
    with rasterio.open(source_path) as src, rasterio.open(reference_path) as ref:
        if (src.width == ref.width and src.height == ref.height and
            src.transform == ref.transform and src.crs == ref.crs):
            return src.read(1)
        src_data = src.read(1)
        aligned_data = np.zeros((ref.height, ref.width), dtype=np.float32)
        reproject(
            src_data, aligned_data,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=ref.transform,
            dst_crs=ref.crs,
            resampling=Resampling.nearest,
            src_nodata=src.nodata
        )
        return aligned_data

raster_paths = {
    "mdt":   os.path.join(output_folder_cropped, 'MDT_cropped.tif'),
    "slope": os.path.join(output_folder_cropped, 'SLOPE_cropped.tif'),
    "aspect":os.path.join(output_folder_cropped, 'ASPECT_cropped.tif'),
    "twi":   os.path.join(output_folder_cropped, 'twi_cropped.tif'),
    "ftm":   os.path.join(output_folder_cropped, 'FMT_cropped.tif'),
    "wui":   os.path.join(output_folder_cropped, 'WUI_cropped.tif'),
    "infra": os.path.join(output_folder_cropped, 'infra_layer_cropped.tif'),
    "meteo": os.path.join(output_folder_cropped, 'FWI_cropped.tif'),
}

reference_path = raster_paths['mdt']

# Load the master silhouette of Galicia: Galicia.shp (with 3000m buffer)
with rasterio.open(reference_path) as ref:
    ref_data = ref.read(1)
    master_mask = ref_data > 0

aligned_layers = {}
for key, path in raster_paths.items():
    data = align_raster_with_resampling(path, reference_path)

    # 1. Standardize what a "gap" means (convert all to np.nan temporarily)
    data_clean = np.where(data <= 0, np.nan, data)

    # 2. Logic for filling gaps based on layer type
    if key in ['meteo', 'aspect', 'twi']:
        # Gaps debidos a error (p.ej. bordes de malla). Interpolamos.
        valid_mask = ~np.isnan(data_clean)
        data_filled = fillnodata(
            data_clean,
            mask=valid_mask,
            max_search_distance=25.0,
            smoothing_iterations=0
        )
        data_filled = np.nan_to_num(data_filled, nan=0.0)
    else:
        # Gaps reales (sin WUI, sin combustible, etc.). Riesgo 0.
        data_filled = np.nan_to_num(data_clean, nan=0.0)

    # 3. Strictly cut to the master mask
    data_final = np.where(master_mask, data_filled, 0)
    aligned_layers[key] = data_final
    print(f" - Layer '{key}' processed. Dimensions: {data_final.shape}")

# ==========================================
# 4. AHP (Analytic Hierarchy Process)
# ==========================================
print("\nCalculating AHP weights and summing layers...")

# Vegetation topic
vegetation_matrix = np.array([[1]])
we_veg = calculate_weights(normalize_matrix(vegetation_matrix))
veg_topic = aligned_layers["ftm"] * we_veg[0]

# AI topic (infra + WUI)
ai_matrix = np.array([
    [1,   2],
    [1/2, 1]
])
we_ai = calculate_weights(normalize_matrix(ai_matrix))
ai_topic = sum(aligned_layers[k] * w for k, w in zip(["infra", "wui"], we_ai))

# Topography topic 
topography_matrix = np.array([
    [1,   2,   3,   3],
    [1/2, 1,   2,   2],
    [1/3, 1/2, 1,   2],
    [1/3, 1/2, 1/2, 1]
])
we_topo = calculate_weights(normalize_matrix(topography_matrix))
topo_topic = sum(aligned_layers[k] * w for k, w in zip(["mdt", "slope", "aspect", "twi"], we_topo))

# ------------------------------------------
# Matriz principal: con o sin FWI según use_fwi
# ------------------------------------------
if use_fwi:
    final_layers = [topo_topic, ai_topic, veg_topic, aligned_layers["meteo"]]
    comparison_matrix = np.array([
        [1,   1/3, 3, 3],  # Topography
        [3,   1,   2, 3],    # Socioeconomics (AI)
        [1/3,   1/2, 1,   2],  # Vegetation 
        [1/3,   1/3, 1/2,   1]     # Meteorology (FWI)
    ])
else:
    final_layers = [topo_topic, ai_topic , veg_topic ]
    comparison_matrix = np.array([
        [1,   1/3, 3],   # Topography
        [3,   1,   2],     # Socioeconomics (AI)
        [1/3,   1/2, 1]      # Vegetation 
    ])

final_weights = calculate_weights(normalize_matrix(comparison_matrix))

cr = consistency_ratio(comparison_matrix, final_weights)
print(f'CR of the main matrix: {cr:.4f}')
print("The matrix is consistent." if cr < 0.1 else "The matrix is not consistent.")

# ==========================================
# 5. FINAL RISK MAP AND SAVING
# ==========================================
print("\nGenerating and classifying the final map...")
fr_map = sum(layer * weight for layer, weight in zip(final_layers, final_weights))

reference_profile = rasterio.open(reference_path).profile
reference_profile.update(dtype='float32', count=1)
output_path = r'C:\Users\Mateo G\Desktop\STORCITO\Salida Datos\mapa_final.tif'

# Temporarily save the map in floating values (continuous risk)
with rasterio.open(output_path, 'w', **reference_profile) as dst:
    dst.write(fr_map.astype('float32'), 1)

fr_final = r'C:\Users\Mateo G\Desktop\STORCITO\Salida Datos\forest_fire_risk_map.tif'
with rasterio.open(output_path) as mapa_final:
    forest_fire_final = mapa_final.read(1).astype('float32')
    fr_clasificado = np.zeros_like(forest_fire_final, dtype='int32')

    # Classification from 1 to 5
    fr_clasificado[(forest_fire_final > 0) & (forest_fire_final <= 1)] = 1
    fr_clasificado[(forest_fire_final > 1) & (forest_fire_final <= 2)] = 2
    fr_clasificado[(forest_fire_final > 2) & (forest_fire_final <= 3)] = 3
    fr_clasificado[(forest_fire_final > 3) & (forest_fire_final <= 4)] = 4
    fr_clasificado[forest_fire_final > 4] = 5

    # We reinforce the cleaning of the edges using the master mask
    fr_clasificado[~master_mask] = 0

    # We force the 0 values (outside the map) to be transparent for visualization
    plot_data = np.where(fr_clasificado == 0, np.nan, fr_clasificado)

# Show the image
plt.figure(figsize=(10, 8))
plt.imshow(plot_data, cmap='Reds', vmin=1, vmax=5)
cbar = plt.colorbar(shrink=0.8)
cbar.set_ticks([1, 2, 3, 4, 5])
cbar.set_label('Risk class')
plt.title('Forest Fire Risk Map - Galicia (Static)')
plt.tight_layout()
plt.show()

# Save the final classified map
with rasterio.open(output_path) as mapa_final:
    meta = mapa_final.profile
    meta.update(dtype='int32')
    with rasterio.open(fr_final, 'w', **meta) as dst:
        dst.write(fr_clasificado, 1)

print(f"Final map saved successfully at:\n '{fr_final}'")

# ==========================================
# 6. CLEANUP OF INTERMEDIATE FOLDER
# ==========================================
print("\nPerforming cleanup of temporary files...")
for folder in [output_folder_cropped]:
    if os.path.exists(folder):
        shutil.rmtree(folder)
        print(f" - Temporary folder deleted: {folder}")

print("\nProcess completed successfully!")
