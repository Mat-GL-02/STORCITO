import os
import rasterio
import numpy as np
import matplotlib.pyplot as plt

from setup import check_valid_entries
from pathlib import Path

def GCI(input_folder:str='INPUT',output_folder:str='OUTPUT',export_image:bool=False)->None:

    valids,invalids=check_valid_entries(["B03","B08"],input_folder=input_folder)
    
    if not valids:
        
        raise ValueError(f"No se encontraron entradas válidas con las bandas requeridas para calcular el TWI.\n \
                         Prueba a en la muestra {invalids[0]['fecha_inicio']}_{invalids[0]['fecha_fin']} \n \
                         \t añadiendo las bandas faltantes: {', '.join(invalids[0]['bandas_faltantes'])} ")
    
    entry_arrays_tiffs={}
    meta_ref={}

    for listado in valids:
        bands=[]
        
        for path in listado['archivos']:

            with rasterio.open(path) as src:

                if listado['fecha_inicio'] not in meta_ref:
                    meta_ref[listado['fecha_inicio']]=src.meta.copy()
                    
                bands.append(src.read(1).astype(np.float32))
        name_keys = ['fecha_inicio', 'fecha_fin', 'satelite', 'nivel']
        entry_arrays_tiffs["_".join(listado[k] for k in name_keys)]=bands
  
      
    np.seterr(divide='ignore', invalid='ignore')
    gci =[ (instance[1] / instance[0]) - 1
          for instance in entry_arrays_tiffs.values() ]
    
    if export_image:

        tiff_dir=Path(output_folder)/'GCI'/'TIFFs'
        png_dir=Path(output_folder)/'GCI'/'PNGs'

        tiff_dir.mkdir(parents=True, exist_ok=True); png_dir.mkdir(parents=True, exist_ok=True)

        for meta_i,gci_i_array,extra_info in zip(meta_ref.values(),gci,entry_arrays_tiffs.keys()):

            # Guardar GCI como .tiff y .tif (float32)
            meta_gci = meta_i.copy()
            meta_gci.update(driver='GTiff', dtype='float32', count=1)

            gci_tiff = tiff_dir/f'{extra_info}_(GCI).tiff'
            gci_tif  = tiff_dir/f'{extra_info}_(GCI).tif'

            with rasterio.open(gci_tiff, 'w', **meta_gci) as dst: 
                dst.write(gci_i_array.astype('float32'), 1)
            with rasterio.open(gci_tif,  'w', **meta_gci) as dst: 
                dst.write(gci_i_array.astype('float32'), 1)

            # Guardar PNGs en carpeta separada
            plt.figure(figsize=(8,6)); 
            plt.imshow(gci_i_array, cmap='RdYlGn'); plt.colorbar(); plt.title('GCI'); plt.tight_layout()
            plt.savefig(png_dir/f'{extra_info}_(GCI).png', dpi=300, bbox_inches='tight'); plt.close()

        print(f"Imágenes guardadas en:\n - Rasters: {tiff_dir}\n - PNGs: {png_dir}")

    # with rasterio.open(input_b8) as b8_src:
    #     nir_band = b8_src.read(1).astype('float32')
    #     meta_ref = b8_src.meta.copy()

    # with rasterio.open(input_b3) as b4_src:
    #     green_band = b4_src.read(1).astype('float32')

    # np.seterr(divide='ignore', invalid='ignore')
    # GCI = nir_band / green_band -1


    # if export_image:
    #     tiff_dir = r'..\OUTPUT\GCI'
    #     png_dir = r'..\OUTPUT\GCI\PNGs'

    #     os.makedirs(tiff_dir, exist_ok=True); os.makedirs(png_dir, exist_ok=True)

    #     # Guardar GCI como .tiff y .tif (float32)
    #     meta_gci = meta_ref.copy()

    #     meta_gci.update(driver='GTiff', dtype='float32', count=1)
    #     GCI_tiff = os.path.join(tiff_dir, 'GCI.tiff')
    #     GCI_tif  = os.path.join(tiff_dir, 'GCI.tif')

    #     with rasterio.open(GCI_tiff, 'w', **meta_gci) as dst: dst.write(GCI.astype('float32'), 1)
    #     with rasterio.open(GCI_tif,  'w', **meta_gci) as dst: dst.write(GCI.astype('float32'), 1)


    #     # Guardar PNGs en carpeta separada
    #     plt.figure(figsize=(8,6)); 
    #     plt.imshow(GCI, cmap='RdYlGn'); plt.colorbar(); plt.title('NDMI'); plt.tight_layout()
    #     plt.savefig(os.path.join(png_dir, 'GCI.png'), dpi=300, bbox_inches='tight'); plt.close()

    #     print(f"Imágenes guardadas en:\n - Rasters: {tiff_dir}\n - PNGs: {png_dir}")

    # # Mostrar las imágenes
    # plt.figure(figsize=(8,6)); 
    # plt.imshow(GCI, cmap='RdYlGn'); plt.colorbar(); plt.title('NDMI'); plt.tight_layout(); plt.show()

if __name__ == "__main__":
    GCI(export_image=True)