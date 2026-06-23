import pandas as pd
from scipy.stats import wilcoxon

# 1. Cargar el dataset (reemplaza 'resultados_datasets.csv' con la ruta de tu archivo)
df = pd.read_csv('resultados_datasetss.csv')

# 2. Limpieza de datos
# Como los costos vienen formateados con coma como decimal (ej. "0,006") y como texto,
# los convertimos a números flotantes reemplazando la coma por punto.
df['PIPELINE_COST_USD'] = df['PIPELINE_COST_USD'].str.replace(',', '.').astype(float)
df['AGENT_COST_USD'] = df['AGENT_COST_USD'].str.replace(',', '.').astype(float)

# 3. Aplicar el Test de Wilcoxon para muestras emparejadas
# Usamos 'wilcoxon' directamente sobre ambas columnas
stat, p_value = wilcoxon(df['PIPELINE_COST_USD'], df['AGENT_COST_USD'])

# 4. Calcular estadísticas descriptivas básicas para complementar el análisis
mediana_pipeline = df['PIPELINE_COST_USD'].median()
mediana_agent = df['AGENT_COST_USD'].median()

# 5. Desplegar los resultados
print("=== RESULTADOS DEL TEST DE WILCOXON ===")
print(f"Mediana Costo Pipeline: USD {mediana_pipeline:.4f}")
print(f"Mediana Costo Agent:    USD {mediana_agent:.4f}")
print("-" * 40)
print(f"Estadístico del test:    {stat}")
print(f"p-value:                 {p_value:.6f}")
print("-" * 40)

# Interpretación estadística (Nivel de significancia standard: alpha = 0.05)
alpha = 0.05
if p_value < alpha:
    print("Resultado: ESTADÍSTICAMENTE SIGNIFICATIVO (p < 0.05).")
    print("Existe una diferencia real y sistemática entre los costos de Pipeline y Agent.")
else:
    print("Resultado: NO SIGNIFICATIVO (p >= 0.05).")
    print("No se puede asegurar que uno sea consistentemente más caro que el otro; las variaciones podrían ser por azar.")
