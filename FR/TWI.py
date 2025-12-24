import os
import rasterio

import numpy as np
import matplotlib.pyplot as plt

from pathlib import Path
from setup import check_valid_entries

def twi(input_folder:str='INPUT',output_folder:str="OUTPUT",export_image:bool=False)->None:
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
    valids,invalids=check_valid_entries(["B01","B03","B05","B06","B08","B12"],input_folder=input_folder)

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

    twi =[ 2.84 * (instance[2] - instance[3]) / (instance[1] + instance[5]) + 
          ( 1.25 * ( instance[1] - instance[0] ) - ( instance[4] - instance[0] ) ) / ( instance[4] + 1.25 *  instance[1] - 0.25 * instance[0] )  
          for instance in entry_arrays_tiffs.values() ]

    if export_image:

        tiff_dir=Path(output_folder)/'TWI'/'TIFFs'
        png_dir=Path(output_folder)/'TWI'/'PNGs'

        tiff_dir.mkdir(parents=True, exist_ok=True); png_dir.mkdir(parents=True, exist_ok=True)

        for meta_i,twi_i_array,extra_info in zip(meta_ref.values(),twi,entry_arrays_tiffs.keys()):
    
            meta_i.update(driver='GTiff', dtype='float32', count=1)
            
            twi_tiff = tiff_dir/f'{extra_info}_(TWI).tiff'
            twi_tif  = tiff_dir/f'{extra_info}_(TWI).tif'

            with rasterio.open(twi_tiff, 'w', **meta_i) as dst: 
                dst.write(twi_i_array.astype('float32'), 1)
            
            with rasterio.open(twi_tif,  'w', **meta_i) as dst: 
                dst.write(twi_i_array.astype('float32'), 1)
            
            plt.figure(figsize=(8,6)); 
            plt.imshow(twi_i_array, cmap='RdYlGn'); plt.colorbar(); plt.title('TWI'); plt.tight_layout()
            plt.savefig(png_dir/f'{extra_info}_(TWI).png', dpi=300, bbox_inches='tight'); plt.close()

        print(f"Imágenes guardadas en:\n - Rasters: {tiff_dir}\n - PNGs: {png_dir}")

if __name__ == "__main__":
    twi(export_image=True)  