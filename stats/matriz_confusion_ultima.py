import csv
import re
import matplotlib.pyplot as plt
import numpy as np

def cargar_csv(ruta_archivo):
    """
    Lee el archivo CSV y retorna un conjunto con los requerimientos.
    Ignora espacios extraños y saltos de línea para facilitar el cruce.
    """
    requerimientos = set()
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            
            # Buscar el índice de la columna que contiene los requerimientos
            req_idx = -1
            for i, h in enumerate(headers):
                if 'REQUERIMIENTO_FUNCIONAL' in h.strip():
                    req_idx = i
                    break
            
            # Si no se encuentra por nombre, asumimos que es la tercera columna (índice 2)
            if req_idx == -1:
                req_idx = 2
                
            for row in reader:
                if len(row) > req_idx:
                    # Limpiamos el texto
                    req_texto = " ".join(row[req_idx].strip().split())
                    requerimientos.add(req_texto)
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo {ruta_archivo}")
    
    return requerimientos

def simplificar_texto(texto):
    """Elimina puntuación y pasa a minúsculas para comparaciones más robustas."""
    return re.sub(r'[^\w]', '', texto).lower()

def main():
    # 1. Cargar el Ground Truth desde los CSV
    positives = cargar_csv('positive.csv')
    negatives = cargar_csv('negative.csv')
    
    # 2. Leer el log de resultados
    try:
        with open('../iteracion_AGENTE_tiempo.txt', 'r', encoding='utf-8') as f:
            log_content = f.read()
    except FileNotFoundError:
        print("Error: No se encontró el archivo iteracion_f_local.txt")
        return

    # 3. Extraer las predicciones usando RegEx
    # Captura lo que está entre "Reviewed Requirement:" y "==========================" 
    # y luego captura el "Status:"
    patron = r"Reviewed Requirement:\s*(.*?)\s*\n==========================\nStatus:\s*(Fulfilled|Not fulfilled)"
    predicciones = re.findall(patron, log_content, re.DOTALL)
    
    # Variables de la matriz de confusión
    TP = 0  # True Positives: Era Fulfilled y predijo Fulfilled
    TN = 0  # True Negatives: Era Not fulfilled y predijo Not fulfilled
    FP = 0  # False Positives: Era Not fulfilled pero predijo Fulfilled
    FN = 0  # False Negatives: Era Fulfilled pero predijo Not fulfilled
    
    no_encontrados = []

    # 4. Cruzar predicciones con el Ground Truth de los CSVs
    for req, status_predicho in predicciones:
        req_limpio = " ".join(req.strip().split())
        req_simple = simplificar_texto(req_limpio)
        
        status_real = None
        
        # Buscar en positivos
        if any(simplificar_texto(p) == req_simple for p in positives):
            status_real = 'Fulfilled'
        # Buscar en negativos
        elif any(simplificar_texto(n) == req_simple for n in negatives):
            status_real = 'Not fulfilled'
            
        # Calcular matriz
        if status_real == 'Fulfilled':
            if status_predicho == 'Fulfilled':
                TP += 1
            else:
                FN += 1
        elif status_real == 'Not fulfilled':
            if status_predicho == 'Not fulfilled':
                TN += 1
            else:
                FP += 1
        else:
            no_encontrados.append(req_limpio)

    # 5. Imprimir resultados
    print("\n" + "="*50)
    print(" " * 12 + "MATRIZ DE CONFUSIÓN")
    print("="*50)
    print(f"Verdaderos Positivos (TP) : {TP}")
    print(f"Falsos Positivos     (FP) : {FP}")
    print(f"Verdaderos Negativos (TN) : {TN}")
    print(f"Falsos Negativos     (FN) : {FN}")
    print("-" * 50)
    
    print("\nFormato de Tabla:")
    print("                       | Predicción: Fulfilled | Predicción: Not fulfilled")
    print("--------------------------------------------------------------------------")
    print(f"Ground Truth: Positive | {TP:<21} | {FN:<25}")
    print(f"Ground Truth: Negative | {FP:<21} | {TN:<25}")
    print("--------------------------------------------------------------------------")
    
    if no_encontrados:
        print(f"\n[ADVERTENCIA] {len(no_encontrados)} requerimientos evaluados no se encontraron en tus CSV:")
        for r in no_encontrados:
            print(f" - {r}")

    guardar_matriz_confusion(TP, FP, TN, FN)

def guardar_matriz_confusion(TP, FP, TN, FN, archivo_salida="matriz_confusion.png"):
    """
    Guarda la matriz de confusión como imagen PNG.
    """

    matriz = np.array([
        [TP, FN],
        [FP, TN]
    ])

    fig, ax = plt.subplots(figsize=(8, 5))

    # Heatmap
    im = ax.imshow(matriz)

    # Etiquetas
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])

    ax.set_xticklabels(["Evaluation: Fulfilled", "Evaluation: Not Fulfilled"])
    ax.set_yticklabels(["Real Value: Fulfilled", "Real Value: Not Fulfilled"])

    # Valores dentro de las celdas
    umbral = matriz.max() / 2

    for i in range(2):
        for j in range(2):
            color_texto = "white" if matriz[i, j] < umbral else "black"

            ax.text(
                j,
                i,
                str(matriz[i, j]),
                ha="center",
                va="center",
                fontsize=16,
                fontweight="bold",
                color=color_texto
            )

    ax.set_title("Confusion Matrix: Evaluator | Agent Mode")
    fig.colorbar(im)

    plt.tight_layout()
    plt.savefig(archivo_salida, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"\nImagen guardada en: {archivo_salida}")
    


main()

