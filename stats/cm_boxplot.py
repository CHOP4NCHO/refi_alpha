import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

df = pd.read_csv("resultados_contiempo.csv")

df["PIPELINE_COST_USD"] = (
    df["PIPELINE_COST_USD"]
    .astype(str)
    .str.replace(",", ".", regex=False)
    .astype(float)
)

df["AGENT_COST_USD"] = (
    df["AGENT_COST_USD"]
    .astype(str)
    .str.replace(",", ".", regex=False)
    .astype(float)
)

plot_df = pd.DataFrame({
    "Method": ["Pipeline"] * len(df) + ["Agent"] * len(df),
    "Cost per Million Token USD":
        list(df["PIPELINE_COST_USD"]) +
        list(df["AGENT_COST_USD"])
})

sns.set_theme(style="whitegrid")

palette = {
    "Pipeline": "#4E79A7",  # azul
    "Agent": "#E15759"      # rojo
}

plt.figure(figsize=(8, 6))

sns.boxplot(
    data=plot_df,
    x="Method",
    y="Cost per Million Token USD",
    hue="Method",
    palette=palette,
    width=0.55,
    showmeans=True,
    meanprops={
        "marker": "D",
        "markerfacecolor": "black",
        "markeredgecolor": "black",
        "markersize": 7
    },
    legend=False
)

sns.stripplot(
    data=plot_df,
    x="Method",
    y="Cost per Million Token USD",
    hue="Method",
    palette=palette,
    jitter=0.15,
    alpha=0.65,
    size=5,
    legend=False
)

plt.title(
    "Execution Cost per Method: Pipeline vs Agent",
    fontsize=14,
    fontweight="bold"
)

plt.ylabel("Cost per Million Token USD")
plt.xlabel("Method")
plt.grid(axis="y", linestyle="--", alpha=0.4)

plt.tight_layout()

plt.savefig(
    "execution_cost_boxplot.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()