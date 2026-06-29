import pandas as pd
from scipy.stats import wilcoxon

# 1. Cargar el dataset nuevo
df = pd.read_csv('resultados_contiempo.csv')

# 2. Función para limpiar el formato de texto con comas a float de Python
def limpiar_columna(col):
    return col.astype(str).str.replace(',', '.').astype(float)

# Limpieza de Costos
df['PIPELINE_COST_USD'] = limpiar_columna(df['PIPELINE_COST_USD'])
df['AGENT_COST_USD'] = limpiar_columna(df['AGENT_COST_USD'])

# Limpieza de Tiempos de Respuesta
df['PIPELINE_TIME_P_REQ'] = limpiar_columna(df['PIPELINE_TIME_P_REQ'])
df['AGENT_TIME_P_REQ'] = limpiar_columna(df['AGENT_TIME_P_REQ'])


# ==========================================
# TEST 1: COSTO EN USD
# ==========================================
stat_cost, p_cost = wilcoxon(df['PIPELINE_COST_USD'], df['AGENT_COST_USD'])
mediana_cost_pip = df['PIPELINE_COST_USD'].median()
mediana_cost_age = df['AGENT_COST_USD'].median()

print("=== TEST DE WILCOXON: COSTO EN USD ===")
print(f"Mediana Costo Pipeline: USD {mediana_cost_pip:.4f}")
print(f"Mediana Costo Agent:    USD {mediana_cost_age:.4f}")
print(f"p-value (Costo):        {p_cost:.6f}")
if p_cost < 0.05:
    print("Resultado: SIGNIFICATIVO. Hay una diferencia real en los costos.")
else:
    print("Resultado: NO SIGNIFICATIVO. Los costos son estadísticamente equivalentes.")

print("\n" + "="*45 + "\n")

# ==========================================
# TEST 2: TIEMPO DE RESPUESTA
# ==========================================
stat_time, p_time = wilcoxon(df['PIPELINE_TIME_P_REQ'], df['AGENT_TIME_P_REQ'])
mediana_time_pip = df['PIPELINE_TIME_P_REQ'].median()
mediana_time_age = df['AGENT_TIME_P_REQ'].median()

print("=== TEST DE WILCOXON: TIEMPO DE RESPUESTA por requerimiento ===")
print(f"Mediana Tiempo Pipeline: {mediana_time_pip:.2f} seg")
print(f"Mediana Tiempo Agent:    {mediana_time_age:.2f} seg")
print(f"p-value (Tiempo):        {p_time:.6f}")
if p_time < 0.05:
    print("Resultado: SIGNIFICATIVO. Una arquitectura es más rápida que la otra de manera consistente.")
else:
    print("Resultado: NO SIGNIFICATIVO. La velocidad de respuesta es estadísticamente equivalente.")