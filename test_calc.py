"""
Tests unitarios para la calculadora
"""
import unittest
from calc import suma, resta, multiplicacion, division


class TestCalculadora(unittest.TestCase):
    """Clase de pruebas para las funciones de la calculadora"""
    
    def test_suma_positivos(self):
        """Prueba suma de números positivos"""
        self.assertEqual(suma(5, 3), 8)
        self.assertEqual(suma(10, 20), 30)
    
    def test_suma_negativos(self):
        """Prueba suma con números negativos"""
        self.assertEqual(suma(-5, -3), -8)
        self.assertEqual(suma(-10, 5), -5)
    
    def test_suma_cero(self):
        """Prueba suma con cero"""
        self.assertEqual(suma(0, 5), 5)
        self.assertEqual(suma(5, 0), 5)
    
    def test_suma_decimales(self):
        """Prueba suma con números decimales"""
        self.assertAlmostEqual(suma(3.5, 2.5), 6.0)
        self.assertAlmostEqual(suma(1.1, 2.2), 3.3, places=1)
    
    def test_resta_positivos(self):
        """Prueba resta de números positivos"""
        self.assertEqual(resta(10, 3), 7)
        self.assertEqual(resta(5, 2), 3)
    
    def test_resta_negativos(self):
        """Prueba resta con números negativos"""
        self.assertEqual(resta(-5, -3), -2)
        self.assertEqual(resta(10, -5), 15)
    
    def test_resta_cero(self):
        """Prueba resta con cero"""
        self.assertEqual(resta(5, 0), 5)
        self.assertEqual(resta(0, 5), -5)
    
    def test_multiplicacion_positivos(self):
        """Prueba multiplicación de números positivos"""
        self.assertEqual(multiplicacion(5, 3), 15)
        self.assertEqual(multiplicacion(10, 2), 20)
    
    def test_multiplicacion_negativos(self):
        """Prueba multiplicación con números negativos"""
        self.assertEqual(multiplicacion(-5, 3), -15)
        self.assertEqual(multiplicacion(-5, -3), 15)
    
    def test_multiplicacion_por_cero(self):
        """Prueba multiplicación por cero"""
        self.assertEqual(multiplicacion(5, 0), 0)
        self.assertEqual(multiplicacion(0, 5), 0)
    
    def test_multiplicacion_por_uno(self):
        """Prueba multiplicación por uno"""
        self.assertEqual(multiplicacion(5, 1), 5)
        self.assertEqual(multiplicacion(1, 5), 5)
    
    def test_division_positivos(self):
        """Prueba división de números positivos"""
        self.assertEqual(division(10, 2), 5)
        self.assertEqual(division(15, 3), 5)
    
    def test_division_negativos(self):
        """Prueba división con números negativos"""
        self.assertEqual(division(-10, 2), -5)
        self.assertEqual(division(-10, -2), 5)
    
    def test_division_decimales(self):
        """Prueba división que resulta en decimal"""
        self.assertAlmostEqual(division(10, 3), 3.333333, places=5)
        self.assertEqual(division(5, 2), 2.5)
    
    def test_division_por_cero(self):
        """Prueba que la división por cero lance un error"""
        with self.assertRaises(ValueError) as context:
            division(10, 0)
        self.assertIn("No se puede dividir por cero", str(context.exception))
    
    def test_division_cero_por_numero(self):
        """Prueba división de cero por un número"""
        self.assertEqual(division(0, 5), 0)


if __name__ == '__main__':
    unittest.main()
