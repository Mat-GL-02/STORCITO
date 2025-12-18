import os
import rasterio
import numpy as np
import matplotlib.pyplot as plt

def Ndvi(input_band4, input_band8):
    print(f'NDVI Layer processing...')

    with rasterio.open(input_band8) as b8_src:
        nir_band = b8_src.read(1).astype('float32')
        meta_ref = b8_src.meta.copy()

    with rasterio.open(input_band4) as b4_src:
        red_band = b4_src.read(1).astype('float32')

    np.seterr(divide='ignore', invalid='ignore')
    ndvi = (nir_band - red_band) / (nir_band + red_band)

    # Reclasificación
    reclasificado = np.zeros_like(ndvi, dtype='int32')
    reclasificado[ndvi <= 0.27] = 5
    reclasificado[(ndvi > 0.27) & (ndvi <= 0.40)] = 4
    reclasificado[(ndvi > 0.40) & (ndvi <= 0.54)] = 3
    reclasificado[(ndvi > 0.54) & (ndvi <= 0.67)] = 2
    reclasificado[ndvi > 0.67] = 1

    # Preguntar si guardar imágenes (TIFF/TIF en una carpeta, PNG en otra)
    while True:
        choice = input("¿Deseas guardar las imágenes? (y/n): ").lower().strip()
        if choice in ('y','n'): break
        print("Entrada no válida. Introduce 'y' o 'n'")

    if choice == 'y':
        tiff_dir = r'C:\Users\Mateo G\Desktop\STORCITO\Salida Datos\re'
        png_dir = r'C:\Users\Mateo G\Desktop\STORCITO\Salida Datos\NDVI'
        os.makedirs(tiff_dir, exist_ok=True); os.makedirs(png_dir, exist_ok=True)

        # Guardar NDVI como .tiff y .tif (float32)
        meta_ndvi = meta_ref.copy()
        meta_ndvi.update(driver='GTiff', dtype='float32', count=1)
        ndvi_tiff = os.path.join(tiff_dir, 'ndvi.tiff')
        ndvi_tif  = os.path.join(tiff_dir, 'ndvi.tif')
        with rasterio.open(ndvi_tiff, 'w', **meta_ndvi) as dst: dst.write(ndvi.astype('float32'), 1)
        with rasterio.open(ndvi_tif,  'w', **meta_ndvi) as dst: dst.write(ndvi.astype('float32'), 1)

        # Guardar reclasificado como .tiff y .tif (int32)
        meta_recl = meta_ref.copy(); meta_recl.update(driver='GTiff', dtype='int32', count=1)
        recl_tiff = os.path.join(tiff_dir, 'ndvi_risk_map.tiff')
        recl_tif  = os.path.join(tiff_dir, 'ndvi_risk_map.tif')
        with rasterio.open(recl_tiff, 'w', **meta_recl) as dst: dst.write(reclasificado.astype('int32'), 1)
        with rasterio.open(recl_tif,  'w', **meta_recl) as dst: dst.write(reclasificado.astype('int32'), 1)

        # Guardar PNGs en carpeta separada
        plt.figure(figsize=(8,6)); plt.imshow(ndvi, cmap='RdYlGn'); plt.colorbar(); plt.title('NDVI'); plt.tight_layout()
        plt.savefig(os.path.join(png_dir, 'ndvi.png'), dpi=300, bbox_inches='tight'); plt.close()

        plt.figure(figsize=(8,6)); plt.imshow(reclasificado, cmap='Reds'); plt.colorbar(); plt.title('NDVI Risk Map'); plt.tight_layout()
        plt.savefig(os.path.join(png_dir, 'ndvi_risk_map.png'), dpi=300, bbox_inches='tight'); plt.close()

        print(f"Imágenes guardadas en:\n - Rasters: {tiff_dir}\n - PNGs: {png_dir}")
    else:
        print("Imágenes no guardadas")

    # Mostrar las imágenes siempre (independientemente de la elección)
    plt.figure(figsize=(8,6)); plt.imshow(ndvi, cmap='RdYlGn'); plt.colorbar(); plt.title('NDVI'); plt.tight_layout(); plt.show()
    plt.figure(figsize=(8,6)); plt.imshow(reclasificado, cmap='Reds'); plt.colorbar(); plt.title('NDVI Risk Map'); plt.tight_layout(); plt.show()

    print('NDVI Layer completed')
    return
