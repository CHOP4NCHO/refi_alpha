import pandas as pd
import matplotlib.pyplot as plt

# ==========================
# Cargar datos
# ==========================

df = pd.read_csv("resultados_contiempo.csv")

# Convertir coma decimal a float
for col in ["PIPELINE_TIME_P_REQ", "AGENT_TIME_P_REQ"]:
    df[col] = (
        df[col]
        .astype(str)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )

# ==========================
# Crear Boxplot
# ==========================

fig, ax = plt.subplots(figsize=(8, 6))

datos = [
    df["PIPELINE_TIME_P_REQ"],
    df["AGENT_TIME_P_REQ"]
]

box = ax.boxplot(
    datos,
    patch_artist=True,
    tick_labels=["Pipeline", "Agent"]
)

# Colores
box["boxes"][0].set_facecolor("#4C72B0")
box["boxes"][1].set_facecolor("#DD8452")

# Personalizar líneas
for median in box["medians"]:
    median.set_color("black")
    median.set_linewidth(2)

# Títulos
ax.set_title(
    "Time per Requirement",
    fontsize=14,
    fontweight="bold"
)

ax.set_ylabel("Time (Segundos)")
ax.set_xlabel("Case")

ax.grid(axis="y", linestyle="--", alpha=0.5)

plt.tight_layout()

# Guardar imagen
plt.savefig(
    "boxplot_tiempo_por_requerimiento.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()