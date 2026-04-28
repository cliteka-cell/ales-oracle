import pdfplumber
import os

def extract_clean_text(pdf_path):
    text_content = []
    print(f"Processing: {os.path.basename(pdf_path)}")
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # We split the page in half vertically to handle the 2-column layout
            width = page.width
            height = page.height
            
            # Left Column
            left_bbox = (0, 0, width/2, height)
            left_col = page.within_bbox(left_bbox).extract_text()
            
            # Right Column
            right_bbox = (width/2, 0, width, height)
            right_col = page.within_bbox(right_bbox).extract_text()
            
            if left_col: text_content.append(left_col)
            if right_col: text_content.append(right_col)
                
    return "\n".join(text_content)

# Folder path
data_folder = "data"
master_output = "ales_master_text.txt"

with open(master_output, "w", encoding="utf-8") as master_file:
    # Loop through all files in the screenshot
    for filename in sorted(os.listdir(data_folder)):
        if filename.endswith(".pdf"):
            file_path = os.path.join(data_folder, filename)
            
            master_file.write(f"\n\n{'='*30}\n")
            master_file.write(f"EXAM: {filename}\n")
            master_file.write(f"{'='*30}\n\n")
            
            text = extract_clean_text(file_path)
            master_file.write(text)

print(f"\n✅ Success! All 13 exams merged into {master_output}")