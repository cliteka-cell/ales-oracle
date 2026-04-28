import fitz  # This is PyMuPDF
import os

def pdf_to_images(pdf_path, output_folder):
    # Make sure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    print(f"Opening {pdf_path}...")
    doc = fitz.open(pdf_path)
    
    # Let's just do the first 5 pages as a test
    for page_num in range(min(5, len(doc))):
        page = doc.load_page(page_num)
        
        # We increase the resolution (zoom) so the AI can read small math text
        zoom = 2.0 
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # Save the image
        output_file = f"{output_folder}/page_{page_num + 1}.png"
        pix.save(output_file)
        print(f"Saved: {output_file}")

# Set your file path here (Change to one of your actual 2021 PDFs)
pdf_file = "data/ALES3_sorular.pdf" 
output_dir = "test_images"

pdf_to_images(pdf_file, output_dir)
print("Done! Check the 'test_images' folder.")