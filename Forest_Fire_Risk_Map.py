"""
Forest Fire Risk Map Generator

This script contains all the necessary functions to generate the final risk map
using the Analytic Hierarchy Process (AHP) for multi-criteria decision making.

Author: Raquel
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from osgeo import gdal
from rasterio.warp import Resampling, reproject

import FR.FHIST as Fhist
import FR.FMT_eu as Fmt
import FR.FWI as Fwi
import FR.infra as Infra
import FR.IUF as Wui
import FR.MDT as Mdt
import FR.NDVI as Ndvi
from FR.ahp import ahp_weights
from FR.cropped import cropped


# =============================================================================
# Configuration - File paths
# =============================================================================

BASE_PATH = Path(r'D:\FR_THDEG')

# MDT inputs/outputs
INPUT_MDT = BASE_PATH / 'DTM' / 'DTM.tif'
INPUT_SLOPE = BASE_PATH / 'DTM' / 'SLOPE.tif'
INPUT_ASPECT = BASE_PATH / 'DTM' / 'ASPECT.tif'
# OUTPUT_MDT = BASE_PATH / 'FR' / 'DTM.tif'
# OUTPUT_SLOPE = BASE_PATH / 'FR' / 'SLOPE.tif'
# OUTPUT_ASPECT = BASE_PATH / 'FR' / 'ASPECT.tif'

# NDVI inputs/outputs
INPUT_BAND8 = BASE_PATH / 'NDVI' / 'B8.tiff'
INPUT_BAND4 = BASE_PATH / 'NDVI' / 'B4.tiff'
# OUTPUT_NDVI = BASE_PATH / 'FR' / 'NDVI.tif'

# FHIST inputs/outputs
FOLDER_PREBURNED = Path(r'D:\FOREST FIRE RISK MAP\Forest Fire Risk Map Gal\HIST\Bandas_pre')
FOLDER_POSTBURNED = Path(r'D:\FOREST FIRE RISK MAP\Forest Fire Risk Map Gal\HIST\Bandas_post')
# OUTPUT_FHIST = Path(r'D:\FOREST FIRE RISK MAP\Forest Fire Risk Map Gal\Forest Fire Risk Map\FHIST.tif')

# FMT inputs/outputs
INPUT_FMT = BASE_PATH / 'FUELS' / 'FUELS.tif'
# OUTPUT_FMT = BASE_PATH / 'FR' / 'FMT.tif'

# Infrastructure inputs/outputs
INPUT_INFRA = BASE_PATH / 'INFRA' / 'infraestructuras_gal.shp'
# OUTPUT_INFRA = BASE_PATH / 'FR' / 'infra_layer.tif'

# WUI inputs/outputs
INPUT_CLC = BASE_PATH / 'WUI' / 'CLC_galicia.shp'
# OUTPUT_WUI = BASE_PATH / 'FR' / 'WUI.tif'

# FWI inputs/outputs
FOLDER_NC = BASE_PATH / 'FWI'
# OUTPUT_FWI = BASE_PATH / 'FR' / 'FWI.tif'

# Processing folders
FR_FOLDER = BASE_PATH / 'FR'
REPROJECTED_FOLDER = FR_FOLDER / 're'
CROPPED_FOLDER = FR_FOLDER / 'Cropped'
FINAL_OUTPUT_FOLDER = FR_FOLDER / 'FR'

# Reprojection parameters
TARGET_EPSG = 32629
TARGET_PIXEL_SIZE = 20
BUFFER_DISTANCE = 3000


# =============================================================================
# Helper functions
# =============================================================================

def align_raster_with_resampling(
    source_path: Path,
    reference_path: Path
) -> np.ndarray:
    """
    Aligns and resamples a source raster to match a reference raster.

    Args:
        source_path: Path to the source raster file.
        reference_path: Path to the reference raster file.

    Returns:
        Aligned and resampled raster data as numpy array.
    """
    with rasterio.open(source_path) as src, rasterio.open(reference_path) as ref:
        aligned_data = np.empty((ref.height, ref.width), dtype=np.float32)

        reproject(
            src.read(1),
            aligned_data,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=ref.transform,
            dst_crs=ref.crs,
            resampling=Resampling.nearest
        )

        return aligned_data


def reproject_and_resize_tiffs(
    input_folder: Path,
    output_folder: Path,
    target_epsg: int = TARGET_EPSG,
    pixel_size: int = TARGET_PIXEL_SIZE
) -> None:
    """
    Reprojects and resizes all TIFF files in a folder.

    Args:
        input_folder: Folder containing input TIFF files.
        output_folder: Folder where processed files will be saved.
        target_epsg: Target EPSG code for reprojection.
        pixel_size: Target pixel size in meters.
    """
    output_folder.mkdir(parents=True, exist_ok=True)

    tiff_files = list(input_folder.glob('*.tif'))

    for tiff_path in tiff_files:
        output_path = output_folder / tiff_path.name

        gdal.Warp(
            str(output_path),
            str(tiff_path),
            dstSRS=f'EPSG:{target_epsg}',
            xRes=pixel_size,
            yRes=pixel_size,
            resampleAlg='cubic'
        )

        print(f"Layer processed: {tiff_path.name} -> {output_path}")

    print("Reprojection and resizing completed.")


def calculate_topic_weights(
    layer_keys: list[str],
    comparison_matrix: np.ndarray,
    aligned_layers: dict[str, np.ndarray],
    check_consistency: bool = True
) -> np.ndarray:
    """
    Calculates weighted combination of layers using AHP.

    Args:
        layer_keys: List of layer names to combine.
        comparison_matrix: Pairwise comparison matrix for AHP.
        aligned_layers: Dictionary of aligned raster data.
        check_consistency: Whether to check matrix consistency.

    Returns:
        Weighted combination of layers as numpy array.
    """
    weights, cr = ahp_weights(comparison_matrix, check_consistency=check_consistency)
    print(f"  Weights: {weights}, CR: {cr:.4f}")

    result = np.zeros_like(aligned_layers[layer_keys[0]])
    for key, weight in zip(layer_keys, weights):
        result = result + aligned_layers[key] * weight
    return result


def classify_risk_map(risk_map: np.ndarray) -> np.ndarray:
    """
    Classifies continuous risk values into discrete risk categories (1-5).

    Args:
        risk_map: Continuous risk values array.

    Returns:
        Classified risk array with values 1-5.
    """
    conditions = [
        (risk_map > 0) & (risk_map <= 1),
        (risk_map > 1) & (risk_map <= 2),
        (risk_map > 2) & (risk_map <= 3),
        (risk_map > 3) & (risk_map <= 4),
        risk_map > 4
    ]
    choices = [1, 2, 3, 4, 5]

    return np.select(conditions, choices, default=0).astype(np.int32)


# =============================================================================
# Main processing pipeline
# =============================================================================

def generate_base_layers() -> None:
    """Generates all base layers required for the risk map."""

    print("Generating MDT layers...")
    Mdt.mdt(INPUT_MDT, output_folder=FR_FOLDER, export_image=True)

    print("Generating NDVI layer...")
    Ndvi.ndvi(INPUT_BAND4, INPUT_BAND8, output_folder=str(FR_FOLDER), export_image=True)

    # Uncomment when FHIST data is available
    # print("Generating FHIST layer...")
    # Fhist.fire_history(input_folder=FOLDER_PREBURNED, output_folder=FR_FOLDER, export_image=True)

    print("Generating FMT layer...")
    Fmt.fmt(INPUT_FMT, output_folder=FR_FOLDER)

    print("Generating Infrastructure layer...")
    Infra.infrastructure(INPUT_INFRA, output_folder=FR_FOLDER)

    print("Generating WUI layer...")
    Wui.wui(INPUT_INFRA, INPUT_CLC, output_folder=FR_FOLDER)

    print("Generating FWI layer...")
    Fwi.f_w_index(FOLDER_NC, output_folder=FR_FOLDER)


def process_and_crop_layers() -> None:
    """Reprojects, resizes, and crops all layers."""

    print("\nReprojecting and resizing layers...")
    reproject_and_resize_tiffs(FR_FOLDER, REPROJECTED_FOLDER)

    print("\nCropping layers around study region...")
    cropped(REPROJECTED_FOLDER, CROPPED_FOLDER, INPUT_INFRA, BUFFER_DISTANCE)


def calculate_fire_risk_map() -> tuple[np.ndarray, Path]:
    """
    Calculates the final fire risk map using AHP.

    Returns:
        Tuple of (risk map array, reference raster path).
    """
    # Define paths to cropped layers
    raster_paths = {
        "mdt": CROPPED_FOLDER / 'DTM_cropped.tif',
        "slope": CROPPED_FOLDER / 'SLOPE_cropped.tif',
        "aspect": CROPPED_FOLDER / 'ASPECT_cropped.tif',
        "ftm": CROPPED_FOLDER / 'FMT_cropped.tif',
        "ndvi": CROPPED_FOLDER / 'NDVI_cropped.tif',
        "wui": CROPPED_FOLDER / 'WUI_cropped.tif',
        "meteo": CROPPED_FOLDER / 'FWI_cropped.tif',
        "infra": CROPPED_FOLDER / 'infra_layer_cropped.tif',
        "fhist": CROPPED_FOLDER / 'FHIST_cropped.tif'
    }

    reference_path = raster_paths['mdt']

    # Align all layers to reference
    print("\nAligning layers to reference...")
    aligned_layers = {
        key: align_raster_with_resampling(path, reference_path)
        for key, path in raster_paths.items()
    }

    for key, data in aligned_layers.items():
        print(f"  {key}: {data.shape}")

    # AHP for Vegetation
    print("\nCalculating Vegetation topic weights...")
    vegetation_matrix = np.array([
        [1, 3],
        [1/3, 1]
    ])
    veg_topic = calculate_topic_weights(
        ["ftm", "ndvi"], vegetation_matrix, aligned_layers
    )

    # AHP for Anthropogenic Issues
    print("\nCalculating Anthropogenic Issues topic weights...")
    ai_matrix = np.array([
        [1, 3],
        [1/3, 1]
    ])
    ai_topic = calculate_topic_weights(
        ["infra", "wui"], ai_matrix, aligned_layers
    )

    # AHP for Topography
    print("\nCalculating Topography topic weights...")
    topography_matrix = np.array([
        [1, 2, 3],
        [1/2, 1, 2],
        [1/3, 1/2, 1]
    ])
    topo_topic = calculate_topic_weights(
        ["mdt", "slope", "aspect"], topography_matrix, aligned_layers
    )

    # Final AHP combination
    print("\nCalculating final risk map weights...")
    final_layers = [
        veg_topic,
        topo_topic,
        aligned_layers["meteo"],
        ai_topic,
        aligned_layers["fhist"]
    ]

    final_matrix = np.array([
        [1, 3, 2, 2, 5],
        [1/3, 1, 1/3, 1/3, 3],
        [1/2, 3, 1, 3, 5],
        [1/2, 3, 1/3, 1, 3],
        [1/5, 1/3, 1/5, 1/3, 1]
    ])

    final_weights, cr = ahp_weights(final_matrix, check_consistency=False)
    print(f"  Final weights: {final_weights}")
    print(f"  Consistency Ratio: {cr:.4f}")

    if cr < 0.1:
        print("  Matrix is consistent")
    else:
        print("  Matrix is NOT consistent - review comparisons")

    # Calculate final risk map
    fr_map = np.zeros_like(final_layers[0])
    for layer, weight in zip(final_layers, final_weights):
        fr_map = fr_map + layer * weight

    return fr_map, reference_path


def save_risk_map(
    risk_map: np.ndarray,
    reference_path: Path,
    output_path: Path
) -> None:
    """
    Saves the risk map to a GeoTIFF file.

    Args:
        risk_map: Risk map array to save.
        reference_path: Reference raster for georeferencing.
        output_path: Output file path.
    """
    with rasterio.open(reference_path) as ref:
        profile = ref.profile.copy()
        profile.update(dtype='float32', count=1)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(risk_map.astype('float32'), 1)

    print(f"Risk map saved: {output_path}")


def visualize_and_save_classified_map(
    input_path: Path,
    output_path: Path
) -> None:
    """
    Classifies, visualizes, and saves the final risk map.

    Args:
        input_path: Path to the continuous risk map.
        output_path: Path for the classified output.
    """
    with rasterio.open(input_path) as src:
        risk_data = src.read(1).astype('float32')
        classified = classify_risk_map(risk_data)

        # Visualize
        plt.figure(figsize=(10, 8))
        plt.imshow(classified, cmap='Reds')
        plt.colorbar(label='Risk Level')
        plt.title('Forest Fire Risk Map')
        plt.show()

        # Save classified map
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with rasterio.open(output_path, 'w', **src.profile) as dst:
            dst.write(classified, 1)

    print(f"Classified map saved: {output_path}")


# =============================================================================
# Main execution
# =============================================================================

if __name__ == "__main__":
    # Step 1: Generate base layers
    generate_base_layers()

    # Step 2: Reproject, resize, and crop
    process_and_crop_layers()

    # Step 3: Calculate fire risk map using AHP
    fr_map, reference_path = calculate_fire_risk_map()

    # Step 4: Save intermediate risk map
    intermediate_output = FR_FOLDER / 'mapa_final.tif'
    save_risk_map(fr_map, reference_path, intermediate_output)

    # Step 5: Classify and save final map
    final_output = FINAL_OUTPUT_FOLDER / 'forest_fire_risk_map.tif'
    visualize_and_save_classified_map(intermediate_output, final_output)

    print("\nForest Fire Risk Map generation completed!")
