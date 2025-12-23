import os
import rasterio
import numpy as np
import matplotlib.pyplot as plt

def Ndmi(input_b8:str,input_b11:str,export_image:bool=False)->None:
    """Calcula el NDMI

    Args:
        input_b8 (str): primera banda
        input_b11 (str): segunda banda
        export_image (bool, optional): se guarda copia en .png . Defaults to False.
    """

    with rasterio.open(input_b8) as b8_src:
        nir_band = b8_src.read(1).astype('float32')
        meta_ref = b8_src.meta.copy()

    with rasterio.open(input_b11) as b4_src:
        swir_band = b4_src.read(1).astype('float32')

    np.seterr(divide='ignore', invalid='ignore')
    ndmi = (nir_band - swir_band) / (nir_band + swir_band)

    # Preguntar si guardar imágenes (TIFF/TIF en una carpeta, PNG en otra)

    if export_image:
        tiff_dir = r'..\OUTPUT\NDMI'
        png_dir = r'..\OUTPUT\NDMI\PNGs'

        os.makedirs(tiff_dir, exist_ok=True); os.makedirs(png_dir, exist_ok=True)

        # Guardar NDMI como .tiff y .tif (float32)
        meta_ndmi = meta_ref.copy()

        meta_ndmi.update(driver='GTiff', dtype='float32', count=1)
        ndmi_tiff = os.path.join(tiff_dir, 'ndmi.tiff')
        ndmi_tif  = os.path.join(tiff_dir, 'ndmi.tif')

        with rasterio.open(ndmi_tiff, 'w', **meta_ndmi) as dst: dst.write(ndmi.astype('float32'), 1)
        with rasterio.open(ndmi_tif,  'w', **meta_ndmi) as dst: dst.write(ndmi.astype('float32'), 1)

        # Guardar reclasificado como .tiff y .tif (int32)
        meta_recl = meta_ref.copy(); meta_recl.update(driver='GTiff', dtype='int32', count=1)

        # Guardar PNGs en carpeta separada
        plt.figure(figsize=(8,6)); 
        plt.imshow(ndmi, cmap='RdYlGn'); plt.colorbar(); plt.title('NDMI'); plt.tight_layout()
        plt.savefig(os.path.join(png_dir, 'ndmi.png'), dpi=300, bbox_inches='tight'); plt.close()

        plt.figure(figsize=(8,6)); 
        plt.savefig(os.path.join(png_dir, 'ndvi_risk_map.png'), dpi=300, bbox_inches='tight'); plt.close()

        print(f"Imágenes guardadas en:\n - Rasters: {tiff_dir}\n - PNGs: {png_dir}")


    plt.figure(figsize=(8,6)); 
    plt.imshow(ndmi, cmap='RdYlGn'); plt.colorbar(); plt.title('NDMI'); plt.tight_layout(); plt.show()