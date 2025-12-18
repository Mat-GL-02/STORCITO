import os
import rasterio
import numpy as np
import matplotlib.pyplot as plt

def fmt(ruta_entrada, ruta_salida):
    print('FTM Layer processing...')
    while True:
        if (ans := input("¿Deseas guardar las imágenes? (y/n): ").strip().lower()) in ('y','n'): break
        print("Introduce 'y' o 'n'.")

    # Leer datos una sola vez
    with rasterio.open(ruta_entrada) as src:
        fmt_eu = src.read(1).astype('float32')
        meta = src.meta.copy()

    # Diccionarios de mapeo para las conversiones
    rothermel_map = {
        1111: 4, 1112: 9, 1121: 4, 1211: 4, 1212: 9, 1221: 4, 1222: 10, 1301: 4,
        21: 5, 22: 4, 23: 4, 31: 3, 32: 3, 33: 3, 41: 3, 42: 3,
        51: 4, 52: 4, 53: 3, 61: 0, 62: 5, 7: 0
    }
    final_map = {
        1: 3, 2: 1, 3: 4, 4: 5, 5: 3, 6: 4, 7: 5, 8: 2,
        9: 3, 10: 4, 11: 4, 12: 4, 13: 5
    }

    # Aplicar conversiones directamente en memoria
    fmt_rothermel = np.zeros_like(fmt_eu, dtype='int32')
    for key, value in rothermel_map.items():
        fmt_rothermel[fmt_eu == key] = value

    fmt_final = np.zeros_like(fmt_rothermel, dtype='int32')
    for key, value in final_map.items():
        fmt_final[fmt_rothermel == key] = value

    # Directorios para guardar archivos
    rasters_dir = r'C:\Users\Mateo G\Desktop\STORCITO\Salida Datos\re'
    png_dir = r'C:\Users\Mateo G\Desktop\STORCITO\Salida Datos\FMT'
    base = os.path.splitext(os.path.basename(ruta_salida))[0]
    
    if ans == 'y':
        os.makedirs(rasters_dir, exist_ok=True)
        os.makedirs(png_dir, exist_ok=True)
        
        # Actualizar metadata
        meta.update(dtype='int32', nodata=-9999, count=1, driver='GTiff')
        
        # Guardar TIF
        raster_path = os.path.join(rasters_dir, f'{base}.tif')
        with rasterio.open(raster_path, 'w', **meta) as dst:
            dst.write(fmt_final, 1)
        print(f"FTM guardado en: {raster_path}")
        
        # Guardar PNG desde datos en memoria
        png_path = os.path.join(png_dir, f'{base}.png')
        plt.figure(figsize=(8, 6))
        plt.imshow(fmt_final, cmap='Reds')
        plt.colorbar()
        plt.title('Fuel Model Type Risk Map')
        plt.savefig(png_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"PNG guardado en: {png_path}")
    
    # Guardar también en ruta_salida para compatibilidad
    try:
        meta.update(dtype='int32', nodata=-9999, count=1, driver='GTiff')
        with rasterio.open(ruta_salida, 'w', **meta) as dst:
            dst.write(fmt_final, 1)
    except Exception:
        pass

    # Mostrar resultado final desde datos en memoria
    plt.figure(figsize=(8, 6))
    plt.imshow(fmt_final, cmap='Reds')
    plt.colorbar()
    plt.title('Fuel Model Type Risk Map')
    plt.show()

    print("FTM Layer completed.")
    return fmt_final