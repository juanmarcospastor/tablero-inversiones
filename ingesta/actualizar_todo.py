from ingesta_operaciones import ingestar_operaciones
from ingesta_precios import ingestar_precios


def actualizar_todo():
    print("Actualizando operaciones...")
    ingestar_operaciones()
    print("Actualizando precios...")
    ingestar_precios()
    print("Actualización finalizada.")


if __name__ == "__main__":
    actualizar_todo()
