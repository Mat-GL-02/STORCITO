"""
Raster cropping utilities using shapefile masks with buffer support.
"""

from pathlib import Path

import geopandas as gpd
import rasterio
from rasterio.mask import mask
from shapely.geometry import mapping


def create_buffered_mask(
    input_shapefile: str | Path,
    buffer_distance: float,
    output_shapefile: str | Path,
    target_epsg: int = 32629
) -> Path:
    """
    Creates a mask with a buffer around geometries in a shapefile.

    Args:
        input_shapefile: Path to the input shapefile.
        buffer_distance: Buffer distance (in target CRS units, typically meters).
        output_shapefile: Path where the buffered shapefile will be saved.
        target_epsg: EPSG code for the target CRS (default: 32629 - UTM zone 29N).

    Returns:
        Path to the created buffered shapefile.
    """
    output_path = Path(output_shapefile)

    gdf = gpd.read_file(input_shapefile)
    gdf_projected = gdf.to_crs(epsg=target_epsg)
    gdf_projected['geometry'] = gdf_projected['geometry'].buffer(buffer_distance)
    gdf_projected.to_file(output_path)

    print(f"Buffered mask created: {output_path}")
    return output_path


def crop_tiff_with_mask(
    input_tiff: str | Path,
    output_tiff: str | Path,
    mask_shapefile: str | Path
) -> bool:
    """
    Crops a TIFF file based on a shapefile mask.
    Automatically reprojects the shapefile if CRS doesn't match.

    Args:
        input_tiff: Path to the input TIFF file.
        output_tiff: Path where the cropped TIFF will be saved.
        mask_shapefile: Path to the shapefile used for cropping.

    Returns:
        True if successful, False otherwise.
    """
    with rasterio.open(input_tiff) as src:
        raster_crs = src.crs

        gdf = gpd.read_file(mask_shapefile)

        if gdf.crs != raster_crs:
            print(f"  Reprojecting shapefile from {gdf.crs} to {raster_crs}...")
            gdf = gdf.to_crs(raster_crs)

        shapes = [mapping(geom) for geom in gdf.geometry]

        try:
            out_image, out_transform = mask(src, shapes, crop=True)
        except ValueError as e:
            print(f"  Crop error (incompatible CRS or no intersection): {e}")
            print(f"    Skipping file...")
            return False

        out_meta = src.meta.copy()
        out_meta.update({
            'driver': 'GTiff',
            'height': out_image.shape[1],
            'width': out_image.shape[2],
            'transform': out_transform
        })

        with rasterio.open(output_tiff, 'w', **out_meta) as dst:
            for band_idx in range(out_image.shape[0]):
                dst.write(out_image[band_idx], band_idx + 1)

        print(f"Cropped file saved: {output_tiff}")
        return True


def batch_crop_tiffs(
    input_folder: str | Path,
    output_folder: str | Path,
    shapefile_path: str | Path,
    buffer_distance: float,
    output_suffix: str = "_cropped"
) -> list[Path]:
    """
    Processes all TIFF files in a folder, creating a buffered mask from a shapefile
    and cropping each image with that mask.

    Args:
        input_folder: Folder containing input TIFF files.
        output_folder: Folder where cropped TIFF files will be saved.
        shapefile_path: Shapefile used to create the buffer mask.
        buffer_distance: Buffer distance (in CRS units).
        output_suffix: Suffix added to output filenames (default: "_cropped").

    Returns:
        List of paths to successfully cropped files.
    """
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)

    buffered_mask_path = output_path / "buffered_mask.shp"
    create_buffered_mask(shapefile_path, buffer_distance, buffered_mask_path)

    tiff_extensions = {'.tif', '.tiff'}
    tiff_files = [f for f in input_path.iterdir() if f.suffix.lower() in tiff_extensions]

    cropped_files = []
    for tiff_file in tiff_files:
        output_name = f"{tiff_file.stem}{output_suffix}.tif"
        output_file = output_path / output_name

        print(f"Cropping: {tiff_file}")
        if crop_tiff_with_mask(tiff_file, output_file, buffered_mask_path):
            cropped_files.append(output_file)

    print(f"All files cropped and saved to: {output_path}")
    return cropped_files


def cropped(
    input_folder: str | Path,
    output_folder: str | Path,
    infra_layer: str | Path,
    distance: float
) -> list[Path]:
    """
    Main function to crop raster files using an infrastructure layer with buffer.

    Args:
        input_folder: Folder containing input TIFF files.
        output_folder: Folder where cropped files will be saved.
        infra_layer: Path to the infrastructure shapefile.
        distance: Buffer distance around the infrastructure.

    Returns:
        List of paths to cropped files.
    """
    return batch_crop_tiffs(input_folder, output_folder, infra_layer, distance)
