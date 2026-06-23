import re
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Cambia esto por la ruta de tu archivo
log_file_path = "../tools.log.txt"

# Expresiones regulares para extraer los bloques clave
tool_start_regex = r"\[TOOL_START\] Invoke: (\w+)\((.*)\)"
tool_success_regex = r"\[TOOL_SUCCESS\] Payload stats: (\d+) lines, (\d+) chars\."
tool_time_regex = r"\[TOOL_TIME\] Completed in ([\d\.]+) seconds\."

data = []

with open(log_file_path, "r", encoding="utf-8") as f:
    content = f.read()
    
    # Buscamos cada invocación completa mapeando bloques TOOL_START
    # Nota: Este enfoque asume que los bloques se ejecutan en orden secuencial por hilo
    lines = content.split('\n')
    current_tool = None
    
    for line in lines:
        start_match = re.search(tool_start_regex, line)
        if start_match:
            current_tool = {
                "tool_name": start_match.group(1),
                "arguments": start_match.group(2),
                "lines_returned": 0,
                "chars_returned": 0,
                "execution_time": 0.0
            }
            continue
            
        if current_tool:
            success_match = re.search(tool_success_regex, line)
            if success_match:
                current_tool["lines_returned"] = int(success_match.group(1))
                current_tool["chars_returned"] = int(success_match.group(2))
                continue
                
            time_match = re.search(tool_time_regex, line)
            if time_match:
                current_tool["execution_time"] = float(time_match.group(1))
                data.append(current_tool)
                current_tool = None

# Convertir a un DataFrame de Pandas
df = pd.DataFrame(data)

# --- 1. SECCIÓN DE AUDITORÍA ---
print("=== AUDITORÍA GLOBAL DE TOOLS ===")
print(f"Total de llamadas registradas: {len(df)}\n")

# Agrupación estadística
summary = df.groupby("tool_name").agg(
    frecuencia=("tool_name", "count"),
    tiempo_promedio_seg=("execution_time", "mean"),
    tiempo_max_seg=("execution_time", "max"),
    lineas_promedio=("lines_returned", "mean")
).reset_index()

print(summary.to_string(index=False))
