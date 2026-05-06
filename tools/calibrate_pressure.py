# calibrar.py
# Corre con: python3 calibrar.py
# Pega los coeficientes resultantes en bp_final_v3.py
import numpy as np

# Agrega cada nueva medicion como un elemento mas en cada lista
# Usar siempre valores CRUDOS (los que imprime "Crudo: sys=X dia=Y")
calculado_sys = [141, 162, 150, 139]
real_sys      = [110, 124, 131, 115]

calculado_dia = [90,  87,  95,  85]
real_dia      = [79,  82,  87,  84]

calculado_hr  = [86,  106, 97,  88]
real_hr       = [86,  110, 93,  89]

# Regresion lineal: real = escala * crudo + offset
coef_sys = np.polyfit(calculado_sys, real_sys, 1)
coef_dia = np.polyfit(calculado_dia, real_dia, 1)
coef_hr  = np.polyfit(calculado_hr,  real_hr,  1)

print("=" * 50)
print("COEFICIENTES — pegar en bp_final_v3.py")
print("=" * 50)
print(f"SYS_ESCALA = {coef_sys[0]:.4f}")
print(f"SYS_OFFSET = {coef_sys[1]:.2f}")
print(f"DIA_ESCALA = {coef_dia[0]:.4f}")
print(f"DIA_OFFSET = {coef_dia[1]:.2f}")
print(f"FC_ESCALA = {coef_hr[0]:.4f}")

print("=" * 50)
print("VERIFICACION")
print("=" * 50)
errores_sys = []; errores_dia = []; errores_hr = []

for i in range(len(real_sys)):
    sc = calculado_sys[i] * coef_sys[0] + coef_sys[1]
    dc = calculado_dia[i] * coef_dia[0] + coef_dia[1]
    hc = calculado_hr[i]  * coef_hr[0]  + coef_hr[1]
    es = sc - real_sys[i]
    ed = dc - real_dia[i]
    eh = hc - real_hr[i]
    errores_sys.append(abs(es))
    errores_dia.append(abs(ed))
    errores_hr.append(abs(eh))
    print(f"Medicion {i+1}:")
    print(f"  SYS  real={real_sys[i]:3d}  crudo={calculado_sys[i]:3d}  corregido={sc:5.1f}  error={es:+.1f} mmHg")
    print(f"  DIA  real={real_dia[i]:3d}  crudo={calculado_dia[i]:3d}  corregido={dc:5.1f}  error={ed:+.1f} mmHg")
    print(f"  FC   real={real_hr[i]:3d}   crudo={calculado_hr[i]:3d}   corregido={hc:5.1f}  error={eh:+.1f} bpm")
    print()

mae_sys = np.mean(errores_sys)
mae_dia = np.mean(errores_dia)
mae_hr  = np.mean(errores_hr)

print("=" * 50)
print("ERROR MEDIO ABSOLUTO (MAE)")
print("=" * 50)
print(f"  Sistolica:  {mae_sys:.1f} mmHg  {'OK' if mae_sys <= 5 else 'Necesitas mas mediciones'}")
print(f"  Diastolica: {mae_dia:.1f} mmHg  {'OK' if mae_dia <= 5 else 'Necesitas mas mediciones'}")
print(f"  FC:         {mae_hr:.1f} bpm")
print()
print("Referencia clinica AAMI/ISO 81060-2: MAE <= 5 mmHg")
print(f"Mediciones disponibles: {len(real_sys)} (minimo recomendado: 10+)")