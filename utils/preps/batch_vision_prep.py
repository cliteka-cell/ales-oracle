import fitz  # PyMuPDF
import os

def process_all_pdfs(data_folder, base_output_folder):
    # Ana çıktı klasörünü oluştur
    if not os.path.exists(base_output_folder):
        os.makedirs(base_output_folder)

    # Veri klasöründeki tüm PDF'leri bul
    pdf_files = sorted([f for f in os.listdir(data_folder) if f.endswith('.pdf')])
    
    print(f"Toplam {len(pdf_files)} PDF bulundu. İşlem başlıyor...\n")

    for pdf_file in pdf_files:
        pdf_path = os.path.join(data_folder, pdf_file)
        
        # PDF isminden klasör adı oluştur (Örn: "2019_ALES_1.pdf" -> "2019_ALES_1")
        exam_name = os.path.splitext(pdf_file)[0]
        exam_output_folder = os.path.join(base_output_folder, exam_name)
        
        if not os.path.exists(exam_output_folder):
            os.makedirs(exam_output_folder)

        print(f"İşleniyor: {exam_name}")
        doc = fitz.open(pdf_path)
        
        # Sınavın TÜM sayfalarını dön
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Yapay Zekanın küçük yazıları (üssü, kök vb.) rahat okuması için Zoom x2
            zoom = 2.0 
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            # Sayfayı kaydet
            output_file = f"{exam_output_folder}/page_{page_num + 1}.png"
            pix.save(output_file)
            
        print(f"✅ {exam_name} tamamlandı. ({len(doc)} sayfa)")

# Klasör yollarını ayarla
data_dir = "data"
output_dir = "exam_images_dataset"

# Kodu çalıştır
process_all_pdfs(data_dir, output_dir)
print("\n🎉 Tüm sınavlar başarıyla görsellere dönüştürüldü!")