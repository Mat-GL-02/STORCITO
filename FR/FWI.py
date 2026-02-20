import os

import netCDF4 as Nc
import numpy as np
import numpy.ma as ma
from scipy.interpolate import griddata
import matplotlib.pyplot as plt
import rutinas.FWI_Equations as Fwi
import rasterio
from rasterio.transform import from_origin


def f_w_index(folder_nc, output_fwi):

    print("Fire Weather Index Layer processing...")

    # Preguntar si guardar imágenes
    guardar = input("¿Quieres guardar las imágenes generadas? (y/n): ").strip().lower()
    guardar_imagen = (guardar == "y")

    # Rutas de guardado
    png_path = r"C:\Users\Mateo G\Desktop\STORCITO\Salida Datos\FWI\FWI.png"
    tif_path = output_fwi

    if guardar_imagen:
        os.makedirs(os.path.dirname(png_path), exist_ok=True)
        os.makedirs(os.path.dirname(tif_path), exist_ok=True)

    # --------------------------------------------------------
    # LECTURA Y ORDENACIÓN DE ARCHIVOS .NC
    # --------------------------------------------------------
    lista_nc = [
        os.path.join(folder_nc, f)
        for f in os.listdir(folder_nc) if f.endswith(".nc")
    ]
    lista_nc.sort()

    f0 = p0 = d0 = None
    grid_info = None
    FWI = None

    for i, file in enumerate(lista_nc):
        dataset = Nc.Dataset(file)

        x_coord = ma.getdata(dataset["lon"])
        y_coord = ma.getdata(dataset["lat"])

        time_var = dataset["time"]
        times = Nc.num2date(time_var[:], time_var.units)
        tiempo0 = times[0]
        dia_clave = (tiempo0.year, tiempo0.month, tiempo0.day)
        mes = tiempo0.month

        # primeras 24 horas (día del archivo)
        idx_dia = np.arange(0, 24)
        idx_mid = 12  # hora representativa ~13:00

        wind_all = ma.getdata(dataset["mod"][:])    # (96, ny, nx)
        prec_all = ma.getdata(dataset["prec"][:])   # acumulada
        rh_all = ma.getdata(dataset["rh"][:])
        temp_all = ma.getdata(dataset["temp"][:])

        wind_mid = wind_all[idx_mid]
        hum_mid = rh_all[idx_mid]
        temp_mid = temp_all[idx_mid]

        # ---- lluvia diaria a partir de acumulada ----
        # incrementos horarios: P_t - P_{t-1}
        prec_incr = np.diff(prec_all, axis=0, prepend=prec_all[0:1])
        prec_incr = np.maximum(prec_incr, 0.0)

        rain_day = prec_incr[idx_dia].sum(axis=0)

        xmin, xmax = x_coord.min(), x_coord.max()
        ymin, ymax = y_coord.min(), y_coord.max()
        x = np.linspace(xmin, xmax, 360)
        y = np.linspace(ymin, ymax, 360)
        X, Y = np.meshgrid(x, y)

        xf = x_coord.flatten()
        yf = y_coord.flatten()

        wind_m = griddata((xf, yf), (wind_mid * 3.6).flatten(), (X, Y),
                          method="nearest")
        hum_m = griddata((xf, yf), hum_mid.flatten(), (X, Y), method="nearest")
        temp_m = griddata((xf, yf),
                          (temp_mid - 273.15).flatten(), (X, Y),
                          method="nearest")
        rain_m = griddata((xf, yf), rain_day.flatten(), (X, Y),
                          method="nearest")

        if grid_info is None:
            grid_info = (xf, yf, X.shape)

        # Inicializar códigos el primer día
        if f0 is None:
            f0 = np.ones_like(hum_m) * 85.0
            p0 = np.ones_like(hum_m) * 6.0
            d0 = np.ones_like(hum_m) * 15.0

        # --------------------------------------------------------
        # CÁLCULO DIARIO DEL FWI PARA EL DÍA DEL ARCHIVO
        # --------------------------------------------------------
        f = Fwi.ffmc(temp_m, hum_m, wind_m, rain_m, f0)
        p = Fwi.dmc(temp_m, hum_m, rain_m, p0, mes)
        d = Fwi.dc(temp_m, rain_m, mes, d0)

        ISI = Fwi.isi(wind_m, f)
        BUI = Fwi.bui(p, d)
        FWI = Fwi.fwi(ISI, BUI)

        f0, p0, d0 = f, p, d

        # diagnóstico rápido
        fecha_str = f"{tiempo0.year:04d}-{tiempo0.month:02d}-{tiempo0.day:02d}"
        print(f"{fecha_str}  lluvia diaria (mm)  "
              f"min={float(np.nanmin(rain_m)):.2f}  "
              f"max={float(np.nanmax(rain_m)):.2f}")
        print(f"Día procesado: {dia_clave}. Max FFMC: {np.max(f)}")
        print(f"Max DMC: {np.max(p)}")
        print(f"Max DC: {np.max(d)}\n")

         # Elige un píxel central de Galicia, por ejemplo
        iy, ix = hum_m.shape[0] // 2, hum_m.shape[1] // 2

        print(
        f"{fecha_str}  pixel ({iy},{ix})  "
        f"rain={float(rain_m[iy, ix]):.2f}  "
        f"FFMC={float(f[iy, ix]):.2f}  "
        f"DMC={float(p[iy, ix]):.2f}  "
        f"DC={float(d[iy, ix]):.2f}"
    )

        dataset.close()

    if FWI is None:
        print("No se pudo calcular FWI (no hay datos válidos).")
        return

    # -----------------------------------------------------------------------------------
    # FWI final: invertir eje Y y preparar raster. Innecesario si se quitó lo del raster
    # -----------------------------------------------------------------------------------
    data = FWI[::-1, :]

    xf, yf, shape = grid_info
    pixel_size_x = (xf.max() - xf.min()) / (data.shape[1] - 1)
    pixel_size_y = (yf.max() - yf.min()) / (data.shape[0] - 1)
    transform = from_origin(xf.min(), yf.max(), pixel_size_x, pixel_size_y)
    crs = "EPSG:4326"

    fwi_final = data.astype("float32")
    fwi_clas = np.zeros_like(fwi_final, dtype="int32")
    fwi_clas[fwi_final <= 3] = 1
    fwi_clas[(fwi_final > 3) & (fwi_final <= 13)] = 2
    fwi_clas[(fwi_final > 13) & (fwi_final <= 23)] = 3
    fwi_clas[(fwi_final > 23) & (fwi_final <= 28)] = 4
    fwi_clas[fwi_final > 28] = 5

    meta = {
        "driver": "GTiff",
        "count": 1,
        "dtype": "int32",
        "crs": crs,
        "transform": transform,
        "width": fwi_clas.shape[1],
        "height": fwi_clas.shape[0],
        "nodata": -9999,
    }

    fig, ax = plt.subplots(figsize=(8, 6))
    img = ax.imshow(fwi_clas, cmap="Reds")
    fig.colorbar(img, ax=ax)
    ax.set_title("Fire Weather Index Risk Map")
    plt.show()

    if guardar_imagen:
        fig.savefig(png_path, dpi=300, bbox_inches="tight")
        print(f"PNG guardado en: {png_path}")

        with rasterio.open(tif_path, "w", **meta) as dst:
            dst.write(fwi_clas, 1)
        print(f"TIF guardado en: {tif_path}")

    print("Fire Weather Index Layer completed.")

