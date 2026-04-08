"""
Calculadora simple con operaciones básicas.
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
        La resta de a - b
    """
    return a - b


def multiplicacion(a, b):
    """
    Multiplica dos números.
    
    Args:
        a: Primer número
        b: Segundo número
    
    Returns:
        El producto de a * b
    """
    return a * b


def division(a, b):
    """
    Divide dos números.
    
    Args:
        a: Numerador
        b: Denominador
    
    Returns:
        El cociente de a / b
    
    Raises:
        ValueError: Si b es cero
    """
    if b == 0:
        raise ValueError("Error: No se puede dividir por cero")
    return a / b
