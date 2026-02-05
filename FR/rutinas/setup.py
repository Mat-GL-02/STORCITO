import os
import shutil
import re
import rasterio
import numpy as np
import numpy.typing as npt
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes

from typing import Any, Sequence
from numpy.typing import NDArray
from pathlib import Path
from datetime import datetime as time
from collections import defaultdict
from typing import Literal, TypedDict
from itertools import batched
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from rasterio.warp import calculate_default_transform, reproject, Resampling
from datetime import datetime

NODATA_file = -9999.0

DEFAULT_PLOT={
    'figure':{'figsize':(8,6),'tight_layout':True},
    'imshow':{'cmap':'Reds'},
    'save':{'dpi':300,'bbox_inches':'tight'}
}

# Regex precompilado para parseo de nombres Sentinel-2
_SENTINEL_PATTERN = re.compile(
    r"(?P<fecha_inicio>\d{4}-\d{2}-\d{2}-\d{2}_\d{2})_"
    r"(?P<fecha_fin>\d{4}-\d{2}-\d{2}-\d{2}_\d{2})_"
    r"(?P<satelite>Sentinel-\d+)_"
    r"(?P<nivel>L\d[A-Z])_"
    r"(?P<banda>B\d+A?)_\(Raw\).tiff"
)

@dataclass(frozen=True)
class SceneEntry:
    fecha_inicio: str
    fecha_fin: str
    satelite: Literal["Sentinel-2"]
    nivel: str
    archivos: dict[str, Path]
    
    @property
    def id(self) -> str:
        return f"{self.fecha_inicio}_{self.fecha_fin}_{self.satelite}_{self.nivel}"

@dataclass
class ParsedFilename:
    fecha_inicio: datetime
    fecha_fin: datetime
    satelite: str
    nivel: str
    banda: str
    filename: str

    @property
    def id(self) -> str:
        return f"{self.fecha_inicio.strftime('%Y%m%d%H%M')}_{self.fecha_fin.strftime('%Y%m%d%H%M')}_{self.satelite}_{self.nivel}"

@dataclass
class RasterData:
    """Container for loaded raster data and metadata.

    This dataclass encapsulates all information loaded from a raster file,
    including the pixel values, geographic metadata, and nodata handling.

    Attributes:
        array: 2D array of pixel values as float32, with nodata converted to NaN.
        profile: Rasterio profile dictionary with file metadata.
        nodata: Original nodata value from the file, or None if not defined.
        nodata_mask: Boolean mask where True indicates nodata pixels.
        shape: Tuple of (height, width) in pixels.
        transform: Affine transformation matrix for georeferencing.
        crs: Coordinate Reference System of the raster.

    Example:
        >>> data = load_raster(Path("dem.tif"))
        >>> data.shape
        (1000, 1200)
        >>> data.array[data.nodata_mask].size  # Number of nodata pixels
        150
    """
    array: NDArray[np.float32]
    profile: dict
    nodata: float | None
    nodata_mask: NDArray[np.bool_]
    shape: tuple[int, int]
    transform: Any  # rasterio.Affine
    crs: Any  # rasterio.crs.CRS

def parse_filename(filename: str, date_format: str = "%Y-%m-%d-%H_%M") -> ParsedFilename:
    """Parse Sentinel-2 filename to extract metadata components.

    Extracts temporal information, satellite name, processing level, and spectral
    band from filenames following the standard Sentinel-2 naming convention.

    Args:
        filename: Filename string to parse
        date_format: Date format pattern in filename. Defaults to "%Y-%m-%d-%H_%M"

    Returns:
        ParsedFilename dataclass with fields:
            - fecha_inicio: Capture start datetime
            - fecha_fin: Capture end datetime
            - satelite: Satellite name (e.g., "Sentinel-2")
            - nivel: Processing level (e.g., "L2A", "L1C")
            - banda: Spectral band (e.g., "B04", "B08")
            - filename: Original filename

    Raises:
        ValueError: If filename does not match expected Sentinel-2 pattern

    Note:
        Currently only supports Sentinel-2 filename patterns.
    """

    #TODO: Incorporar estructurad de expresion regular para otros satelites

    match = _SENTINEL_PATTERN.match(filename)

    if match:
        return ParsedFilename(
            fecha_inicio=datetime.strptime(match.group('fecha_inicio'), date_format),
            fecha_fin=datetime.strptime(match.group('fecha_fin'), date_format),
            satelite=match.group('satelite'),
            nivel=match.group('nivel'),
            banda=match.group('banda'),
            filename=filename
            )
    else:
        raise ValueError(f"Filename '{filename}' does not match the expected pattern.")

def band_date_sort(file:str):
    """Generate sort key for Sentinel-2 files by satellite, band, and date.

    Args:
        file: Sentinel-2 filename to parse

    Raises:
        ValueError: If filename does not match expected pattern

    Returns:
        tuple: (satellite, band, start_date) for sorting
    """
    if info:=parse_filename(file):
        # print(info.group('banda'),info.group('fecha_inicio'))
        return (info.satelite,info.banda,info.fecha_inicio)
    else:
        raise ValueError(f"Filename '{file}' does not match expected pattern.")

def sort_time_comparative(band_folder:Path|None=None,date_format:str="%Y-%m-%d-%H_%M")->None:
    """Sort and move Sentinel-2 files into PRE_FIRE and POST_FIRE folders.

    Pairs files by band and temporal order, moving earlier captures to PRE_FIRE
    and later captures to POST_FIRE subdirectories.

    Args:
        band_folder: Directory containing TIFF files. Defaults to 'INPUT'
        date_format: Date format pattern in filenames. Defaults to "%Y-%m-%d-%H_%M"

    Raises:
        ValueError: If paired files have mismatched bands
    """

    if not band_folder:
        band_folder=Path("INPUT")

    band_folder.mkdir(parents=True, exist_ok=True)

    pre_fire_folder=band_folder/"PRE_FIRE"
    post_fire_folder=band_folder/"POST_FIRE"

    archivos= [file.name for file in band_folder.iterdir() if file.is_file()]

    if len(archivos)<2:
        return
    
    pre_fire_folder.mkdir(parents=True, exist_ok=True)
    post_fire_folder.mkdir(parents=True, exist_ok=True)

    it = sorted(archivos,key=band_date_sort)

    # print(f'Sorted files : {it}')

    for prev_fire,post_fire in batched(it,2):

        prev_data=parse_filename(prev_fire,date_format=date_format)
        post_data=parse_filename(post_fire,date_format=date_format)


        if prev_data and post_data:

            if prev_data.banda != post_data.banda:
                raise ValueError(f"Mismatched bands: \n{prev_fire} \n and \n{post_fire} do not belong to the same band.")

            shutil.move(band_folder/prev_fire,pre_fire_folder/prev_fire)
            shutil.move(band_folder/post_fire,post_fire_folder/post_fire)

def check_valid_entries(
    bands: list[str],
    input_folder: Path | str = Path("INPUT"),
    satellite: Literal["Sentinel-2"] = "Sentinel-2",
) -> tuple[list[SceneEntry], list[SceneEntry]]:
    """
    Validate and group Sentinel-2 TIFF files by temporal scene.

    Each scene is defined by (fecha_inicio, fecha_fin, satelite, nivel).
    A scene is considered complete if all required bands are present.
    """

    if satellite != "Sentinel-2":
        raise NotImplementedError(f"Satellite '{satellite}' not implemented.")

    input_path = Path(input_folder)
    if not input_path.is_dir():
        raise ValueError(f"'{input_folder}' is not a valid directory.")

    files = list(input_path.glob("*.tiff"))
    if not files:
        raise FileNotFoundError(f"No TIFF files found in '{input_folder}'.")

    scenes = defaultdict(dict)
    required_bands = set(bands)

    for path in files:
        parsed = parse_filename(path.name)

        if parsed.satelite != satellite:
            continue

        band = parsed.banda
        if band not in required_bands:
            continue

        key = (
            parsed.fecha_inicio.strftime("%Y-%m-%d-%H_%M"),
            parsed.fecha_fin.strftime("%Y-%m-%d-%H_%M"),
            parsed.satelite,
            parsed.nivel,
        )

        if band in scenes[key]:
            raise ValueError(f"Duplicate band {band} for scene {key}")

        scenes[key][band] = path

    complete, incomplete = [], []

    for (fi, ff, sat, lvl), band_map in scenes.items():
        missing = required_bands - band_map.keys()

        entry = SceneEntry(
            fecha_inicio=fi,
            fecha_fin=ff,
            satelite=sat,
            nivel=lvl,
            archivos=band_map,
        )

        (incomplete if missing else complete).append(entry)

    if not complete:
        raise ValueError(
            f"No complete scenes found for required bands {bands}"
        )

    return complete, incomplete

def _read_single_raster(path: Path) -> tuple[np.ndarray, dict]:
    """Read a single raster file and return data with metadata."""
    with rasterio.open(path) as src:
        data = src.read(1).astype(np.float32)
        meta = src.meta.copy()
    return data, meta

def read_and_group(entries: list[SceneEntry], max_workers: int = 4) -> dict:
    """Read and group raster data by band using parallel I/O.

    Args:
        entries: List of SceneEntry objects with files to read
        max_workers: Maximum threads for parallel reading. Defaults to 4

    Returns:
        Dict with keys 'id', 'meta_ref', and each band name (e.g., 'B04', 'B08')
    """
    grouped = defaultdict(list)

    # Recopilar todas las tareas de lectura
    read_tasks = []
    for scene in entries:
        grouped["id"].append(scene.id)
        for band, path in scene.archivos.items():
            read_tasks.append((scene.id, scene.fecha_inicio, band, path))

    # Leer en paralelo
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_read_single_raster, task[3]): task for task in read_tasks}
        for future in futures:
            scene_id, fecha_inicio, band, path = futures[future]
            data, meta = future.result()
            results[(scene_id, band)] = (data, meta, fecha_inicio)

    # Organizar resultados manteniendo orden original
    meta_ref_added = set()
    for scene in entries:
        for band in scene.archivos.keys():
            data, meta, fecha_inicio = results[(scene.id, band)]
            grouped[band].append(data)

            if fecha_inicio not in meta_ref_added:
                meta_ref_added.add(fecha_inicio)
                grouped["meta_ref"].append(meta)

    return grouped

def default_imshow(array: npt.NDArray, title: str, colorbar_params: dict | None = None) -> tuple[Figure, Axes]:
    """Display array as image with colorbar using default plot settings.

    Args:
        array: 2D array to visualize
        title: Plot title
        colorbar_params: Additional colorbar parameters (e.g., {'label': 'Risk'})

    Returns:
        Tuple of (figure, axes) matplotlib objects
    """
    if colorbar_params is None:
        colorbar_params = {}
    
    fig1, ax1 = plt.subplots(**DEFAULT_PLOT['figure'])

    img1 = ax1.imshow(array, **DEFAULT_PLOT['imshow'])
    fig1.colorbar(img1, ax=ax1, **colorbar_params)
    ax1.set_title(title)

    return fig1, ax1

def load_raster(path: Path) -> RasterData:
    """Load a raster file and normalize NODATA values to NaN.

    Reads the first band of a raster file, converts it to float32, and replaces
    nodata values with NaN for consistent numerical handling.

    Args:
        path: Path to the raster file (GeoTIFF or any GDAL-supported format).

    Returns:
        RasterData object containing the array, profile, nodata mask, and
        geographic metadata (transform, CRS).

    Raises:
        rasterio.errors.RasterioIOError: If the file cannot be opened.

    Example:
        >>> dem_data = load_raster(Path("dtm_vigo.tif"))
        >>> dem_data.array.shape
        (500, 600)
        >>> np.nanmin(dem_data.array)
        12.5
    """
    with rasterio.open(path) as src:
        arr_raw = src.read(1)
        arr = arr_raw.astype(np.float32)
        profile = src.profile.copy()
        nodata = src.nodata
        shape = (src.height, src.width)
        transform = src.transform
        crs = src.crs

    if nodata is not None:
        nodata_mask = (arr_raw == nodata) | np.isclose(arr_raw, nodata, rtol=1e-5)
        arr[nodata_mask] = np.nan
    else:
        nodata_mask = np.zeros(shape, dtype=bool)

    return RasterData(
        array=arr,
        profile=profile,
        nodata=nodata,
        nodata_mask=nodata_mask,
        shape=shape,
        transform=transform,
        crs=crs
    )

def save_file(array: npt.NDArray, meta: dict, id_name: str | None = None, output_folder: Path|str | None = None,
              type_name: str|None = None, extensions: list[str]|str ='tif', meta_intact:bool=False,
              fig:Figure|None=None, output_path: Path|str|None = None) -> tuple[Path, ...]:
    """Save raster array to file(s) in specified formats.

    Creates organized subfolders (TIFs/, PNGs/, etc.) and saves the array
    as GeoTIFF and/or PNG depending on extensions requested.

    Args:
        array: 2D numpy array to save
        meta: Rasterio metadata dict for GeoTIFF output
        id_name: Base identifier for filename (ignored if output_path is provided)
        output_folder: Output directory path (ignored if output_path is provided)
        type_name: Optional type suffix for filename (e.g., 'NDVI', 'Risk_Map')
        extensions: File format(s) to save. Defaults to 'tif'
        meta_intact: If True, use metadata as-is; otherwise update dtype/driver
        fig: Matplotlib figure required for PNG export
        output_path: If provided, save directly to this path (skips folder/name generation)

    Returns:
        Tuple of Path objects for all saved files

    Raises:
        ValueError: If PNG extension requested without providing fig
        ValueError: If neither output_path nor (id_name + output_folder) are provided

    Examples:
        Modo estructurado (genera carpetas TIFs/, PNGs/):

        >>> save_file(ndvi_array, meta, 'scene_001', 'OUTPUT',
        ...           type_name='NDVI', extensions=['tif', 'png'], fig=fig)
        # Guarda en: OUTPUT/TIFs/scene_001_(NDVI).tif
        #            OUTPUT/PNGs/scene_001_(NDVI).png

        Modo output_path (guarda directamente sin estructura):

        >>> save_file(flow_array, profile, output_path='data/flow_vigo.tif', meta_intact=True)
        # Guarda en: data/flow_vigo.tif
    """
    if not meta:
        meta={}

    meta_i = meta.copy()
    if not meta_intact:
        meta_i.update(driver='GTiff', dtype='float32', count=1, nodata=NODATA_file)

    # Modo output_path: guardar directamente sin generar estructura
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        files_2_save = (output_path,)
    else:
        if id_name is None or output_folder is None:
            raise ValueError("Either output_path or both id_name and output_folder must be provided")

        output_folder = Path(output_folder)
        file_name = f'{id_name}_({type_name})' if type_name else f'{id_name}'

        for extension in extensions:
            ext_folder = output_folder / f'{extension.upper()}s'
            ext_folder.mkdir(parents=True, exist_ok=True)

        files_2_save = tuple([output_folder / f'{extension.upper()}' /f'{file_name}.{extension}' for extension in extensions]) if isinstance(extensions,list) else tuple([output_folder / f'{extensions.upper()}s' /f'{file_name}.{extensions}'])
    
    for file in files_2_save:

        if file.suffix=='.png':
            if not fig:
                raise ValueError("Figure must be provided to save PNG files.")

            fig.savefig(file, **DEFAULT_PLOT['save']); plt.close()

        else:

            out_array = np.where(np.isnan(array), NODATA_file, array)
            
            with rasterio.open(file, 'w', **meta_i) as dst:
                dst.write(out_array.astype('float32'), 1)

    return files_2_save

def reproject_raster(src_path:str|Path, dst_crs:str = "EPSG:32629")->tuple[np.ndarray, dict]:
    """Reproject raster to target coordinate reference system.

    Args:
        src_path: Path to source raster file
        dst_crs: Target CRS in EPSG format. Defaults to "EPSG:32629" (UTM 29N)

    Returns:
        Tuple of (reprojected_array, updated_metadata_dict)
    """
    with rasterio.open(src_path) as src:

        transform, width, height = calculate_default_transform(src.crs, dst_crs, src.width, src.height, *src.bounds)
        kwargs = src.meta.copy()
        kwargs.update({'crs': dst_crs, 'transform': transform, 'width': width, 'height': height})

        dest_array = np.empty((height, width), dtype=src.dtypes[0]) #type: ignore

        reproject(source=rasterio.band(src, 1), destination=dest_array,
                    src_transform=src.transform, src_crs=src.crs,
                    dst_transform=transform, dst_crs=dst_crs, resampling=Resampling.nearest)
        
        return dest_array, kwargs

if __name__ == "__main__":

    sort_time_comparative()