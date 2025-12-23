import os
import rasterio
import numpy as np
import matplotlib.pyplot as plt

def twi(input_b1:str,input_b3,input_b5:str,input_b6:str,input_b8:str,input_b12:str,export_image:bool=False)->None:
    """Calcula el TWI

    Args:
        input_b1 (str): _description_
        input_b3 (_type_): _description_
        input_b5 (str): _description_
        input_b6 (str): _description_
        input_b8 (str): _description_
        input_b12 (str): _description_
        export_image (bool, optional): _description_. Defaults to False.
    """

    with rasterio.open(input_b1) as b8_src:
        band_1 = b8_src.read(1).astype('float32')
        meta_ref = b8_src.meta.copy()

    with rasterio.open(input_b3) as b4_src:
        band_3 = b4_src.read(1).astype('float32')
    
    with rasterio.open(input_b5) as b4_src:
        band_5 = b4_src.read(1).astype('float32')

    with rasterio.open(input_b6) as b4_src:
        band_6 = b4_src.read(1).astype('float32')

    with rasterio.open(input_b6) as b4_src:
        band_8 = b4_src.read(1).astype('float32')

    with rasterio.open(input_b12) as b4_src:
        band_12 = b4_src.read(1).astype('float32')



    np.seterr(divide='ignore', invalid='ignore')
    twi = 2.84 * (band_5 - band_6) / (band_3 + band_12) + ( 1.25 * ( band_3 - band_1 ) - ( band_8 - band_1 ) ) / ( band_8 + 1.25 *  band_3 - 0.25 * band_1 )  

    # Preguntar si guardar imágenes (TIFF/TIF en una carpeta, PNG en otra)

    if export_image:
        tiff_dir = r'..\OUTPUT\TWI'
        png_dir = r'..\OUTPUT\TWI\PNGs'

        os.makedirs(tiff_dir, exist_ok=True); os.makedirs(png_dir, exist_ok=True)

        # Guardar TWI como .tiff y .tif (float32)
        meta_twi = meta_ref.copy()

        meta_twi.update(driver='GTiff', dtype='float32', count=1)
        twi_tiff = os.path.join(tiff_dir, 'twi.tiff')
        twi_tif  = os.path.join(tiff_dir, 'twi.tif')

        with rasterio.open(twi_tiff, 'w', **meta_twi) as dst: dst.write(twi.astype('float32'), 1)
        with rasterio.open(twi_tif,  'w', **meta_twi) as dst: dst.write(twi.astype('float32'), 1)

        # Guardar reclasificado como .tiff y .tif (int32)
        meta_recl = meta_ref.copy(); meta_recl.update(driver='GTiff', dtype='int32', count=1)


        # Guardar PNGs en carpeta separada
        plt.figure(figsize=(8,6)); 
        plt.imshow(twi, cmap='RdYlGn'); plt.colorbar(); plt.title('TWI'); plt.tight_layout()
        plt.savefig(os.path.join(png_dir, 'twi.png'), dpi=300, bbox_inches='tight'); plt.close()


        print(f"Imágenes guardadas en:\n - Rasters: {tiff_dir}\n - PNGs: {png_dir}")

    # Mostrar las imágenes siempre (independientemente de la elección)
    plt.figure(figsize=(8,6)); 
    plt.imshow(twi, cmap='RdYlGn'); plt.colorbar(); plt.title('TWI'); plt.tight_layout(); plt.show()