import re
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, classification_report

log_file_path = "iteracion_agente_gemini.txt"

# Expresiones regulares para capturar los bloques
status_regex = r"Status:\s*(Fulfilled|Not fulfilled)"
gt_regex = r"GROUND TRUTH VALUE:\s*(Fulfilled|Not Fulfilled)"

evaluations = []
current_statuses = []

with open(log_file_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        
        # Capturar las predicciones del agente en la evaluación actual
        status_match = re.search(status_regex, line, re.IGNORECASE)
        if status_match:
            # Normalizamos a minúsculas para evitar problemas de capitalización
            current_statuses.append(status_match.group(1).lower())
            
        # Cuando encontramos el Ground Truth, se cierra el bloque de esa evaluación
        gt_match = re.search(gt_regex, line, re.IGNORECASE)
        if gt_match:
            gt_value = gt_match.group(1).lower()
            
            # Asumimos que el Ground Truth aplica a los requerimientos de este bloque
            # (Si tu log asocia el GT a un requerimiento específico, se puede ajustar)
            for status in current_statuses:
                evaluations.append({
                    "y_pred": status,
                    "y_true": gt_value,
                })
            # Limpiamos para la siguiente evaluación
            current_statuses = []

# Crear DataFrame
df = pd.DataFrame(evaluations)

# Mapeo limpio para las etiquetas del gráfico
labels = ["not fulfilled", "fulfilled"]
labels_display = ["Fulfilled", "Not Fulfilled"]

# Calcular la matriz de confusión
cm = confusion_matrix(df["y_true"], df["y_pred"], labels=labels)

# --- 2. REPORTES Y ESTADÍSTICAS ---
print("=== REPORTE DE CLASIFICACIÓN ===")
print(classification_report(df["y_true"], df["y_pred"], target_names=labels_display))

# --- 3. GRAFICAR MATRIZ DE CONFUSIÓN ---
plt.figure(figsize=(6, 5))
sns.heatmap(
    cm, 
    annot=True, 
    fmt="d", 
    cmap="Blues", 
    xticklabels=labels_display, 
    yticklabels=labels_display
)
plt.title("Confusion Matrix - Evaluator AI Agent")
plt.xlabel("Evaluation Result")
plt.ylabel("Real Value")
plt.tight_layout()
plt.show()
