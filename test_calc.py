"""
Tests unitarios para la calculadora.
"""
import unittest
from calc import suma, resta, multiplicacion, division


class TestCalculadora(unittest.TestCase):
    """Clase de tests para las funciones de la calculadora."""
    
    def test_suma(self):
        """Prueba la función de suma."""
        self.assertEqual(suma(2, 3), 5)
        self.assertEqual(suma(-1, 1), 0)
        self.assertEqual(suma(0, 0), 0)
        self.assertEqual(suma(-5, -3), -8)
        self.assertEqual(suma(2.5, 3.5), 6.0)
    
    def test_resta(self):
        """Prueba la función de resta."""
        self.assertEqual(resta(5, 3), 2)
        self.assertEqual(resta(1, 1), 0)
        self.assertEqual(resta(0, 5), -5)
        self.assertEqual(resta(-3, -5), 2)
        self.assertEqual(resta(10.5, 5.5), 5.0)
    
    def test_multiplicacion(self):
        """Prueba la función de multiplicación."""
        self.assertEqual(multiplicacion(2, 3), 6)
        self.assertEqual(multiplicacion(-2, 3), -6)
        self.assertEqual(multiplicacion(0, 5), 0)
        self.assertEqual(multiplicacion(-2, -3), 6)
        self.assertEqual(multiplicacion(2.5, 2), 5.0)
    
    def test_division(self):
        """Prueba la función de división."""
        self.assertEqual(division(6, 2), 3)
        self.assertEqual(division(5, 2), 2.5)
        self.assertEqual(division(-6, 2), -3)
        self.assertEqual(division(-6, -2), 3)
        self.assertEqual(division(0, 5), 0)
    
    def test_division_por_cero(self):
        """Prueba que la división por cero lance un ValueError."""
        with self.assertRaises(ValueError) as context:
            division(5, 0)
        self.assertIn("No se puede dividir por cero", str(context.exception))


if __name__ == '__main__':
    unittest.main()
