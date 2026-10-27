from pathlib import Path


RAIZ_PROYECTO = Path(__file__).resolve().parent.parent


def obtener_ruta_del_dataset(carpeta,subcarpeta,dataset, data = "data"):

    """
    es una funcion que devuelve la ruta del dataset
    """
    
    ruta_completa = RAIZ_PROYECTO / data / carpeta / subcarpeta / dataset 
    return str(ruta_completa)



# devuelve una lista de objetos Path, ordenada por nombre
def listar_carpetas_data(data="data"):
    """Devuelve la ruta de cada carpeta que hay directamente dentro de 'data'.

    Cada carpeta corresponde a una categoría. Si se agrega una categoría nueva, aparece sola.
    Los archivos sueltos y las carpetas ocultas (que empiezan con '.') se
    ignoran.

    Args:
        data: nombre de la carpeta de datos dentro de la raíz del proyecto.

    Returns:
        Lista de objetos Path ordenada por nombre. Si la carpeta 'data' no
        existe, devuelve una lista vacía.
    """
    carpeta_data = RAIZ_PROYECTO / data
    if not carpeta_data.is_dir():
        return []
    return sorted(
        ruta for ruta in carpeta_data.iterdir()
        if ruta.is_dir() and not ruta.name.startswith(".")
    )