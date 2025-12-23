import os
import rasterio
import numpy as np
import matplotlib.pyplot as plt

def GCI(input_b8:str,input_b3:str,export_image:bool=False)->None:
    """_summary_

    Args:
        input_b8 (str): _description_
        input_b3 (str): _description_
        export_image (bool, optional): _description_. Defaults to False.
    """

    with rasterio.open(input_b8) as b8_src:
        nir_band = b8_src.read(1).astype('float32')
        meta_ref = b8_src.meta.copy()

    with rasterio.open(input_b3) as b4_src:
        green_band = b4_src.read(1).astype('float32')

    np.seterr(divide='ignore', invalid='ignore')
    GCI = nir_band / green_band -1


    if export_image:
        tiff_dir = r'..\OUTPUT\GCI'
        png_dir = r'..\OUTPUT\GCI\PNGs'

        os.makedirs(tiff_dir, exist_ok=True); os.makedirs(png_dir, exist_ok=True)

        # Guardar GCI como .tiff y .tif (float32)
        meta_gci = meta_ref.copy()

        meta_gci.update(driver='GTiff', dtype='float32', count=1)
        GCI_tiff = os.path.join(tiff_dir, 'GCI.tiff')
        GCI_tif  = os.path.join(tiff_dir, 'GCI.tif')

        with rasterio.open(GCI_tiff, 'w', **meta_gci) as dst: dst.write(GCI.astype('float32'), 1)
        with rasterio.open(GCI_tif,  'w', **meta_gci) as dst: dst.write(GCI.astype('float32'), 1)


        # Guardar PNGs en carpeta separada
        plt.figure(figsize=(8,6)); 
        plt.imshow(GCI, cmap='RdYlGn'); plt.colorbar(); plt.title('NDMI'); plt.tight_layout()
        plt.savefig(os.path.join(png_dir, 'GCI.png'), dpi=300, bbox_inches='tight'); plt.close()

        print(f"Imágenes guardadas en:\n - Rasters: {tiff_dir}\n - PNGs: {png_dir}")

    # Mostrar las imágenes
    plt.figure(figsize=(8,6)); 
    plt.imshow(GCI, cmap='RdYlGn'); plt.colorbar(); plt.title('NDMI'); plt.tight_layout(); plt.show()