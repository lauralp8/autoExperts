"""
Script simple para convertir un PDF a Markdown
Requiere: pip install pymupdf
"""

import fitz  # PyMuPDF


def pdf_to_markdown(pdf_path, output_path):
    """
    Convierte un archivo PDF a formato Markdown
    
    Args:
        pdf_path: Ruta al archivo PDF
        output_path: Ruta donde guardar el archivo Markdown
    """
    # Abrir el PDF
    doc = fitz.open(pdf_path)
    
    markdown_content = []
    
    # Procesar cada página
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Agregar encabezado de página
        markdown_content.append(f"\n## Página {page_num + 1}\n")
        
        # Extraer el texto
        text = page.get_text()
        markdown_content.append(text)
        markdown_content.append("\n---\n")
    
    # Cerrar el documento
    doc.close()
    
    # Guardar el contenido en markdown
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(''.join(markdown_content))
    
    print(f"✓ PDF convertido exitosamente a {output_path}")


if __name__ == "__main__":
    # Configuración
    pdf_file = "mipdf.pdf"
    output_file = "mipdf.md"
    
    try:
        pdf_to_markdown(pdf_file, output_file)
    except FileNotFoundError:
        print(f"✗ Error: No se encontró el archivo {pdf_file}")
    except Exception as e:
        print(f"✗ Error al procesar el PDF: {e}")
