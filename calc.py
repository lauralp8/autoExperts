"""
Calculadora Simple
==================
Este módulo proporciona funciones básicas de calculadora.
"""


def suma(a, b):
    """
    Suma dos números.
    
    Args:
        a: Primer número
        b: Segundo número
    
    Returns:
        La suma de a y b
    """
    return a + b


def resta(a, b):
    """
    Resta dos números.
    
    Args:
        a: Primer número
        b: Segundo número
    
    Returns:
        La resta de a menos b
    """
    return a - b


def multiplicacion(a, b):
    """
    Multiplica dos números.
    
    Args:
        a: Primer número
        b: Segundo número
    
    Returns:
        El producto de a y b
    """
    return a * b


def division(a, b):
    """
    Divide dos números.
    
    Args:
        a: Numerador
        b: Denominador
    
    Returns:
        El cociente de a dividido por b
    
    Raises:
        ValueError: Si b es cero
    """
    if b == 0:
        raise ValueError("Error: No se puede dividir por cero")
    return a / b


if __name__ == "__main__":
    # Ejemplos de uso
    print("Ejemplos de uso de la calculadora:")
    print(f"5 + 3 = {suma(5, 3)}")
    print(f"10 - 4 = {resta(10, 4)}")
    print(f"6 * 7 = {multiplicacion(6, 7)}")
    print(f"15 / 3 = {division(15, 3)}")
    
    # Ejemplo de manejo de error
    try:
        print(f"10 / 0 = {division(10, 0)}")
    except ValueError as e:
        print(e)
