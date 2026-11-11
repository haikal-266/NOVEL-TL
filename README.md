# Kakuyomu Novel to EPUB Generator (Sugoi AI Local Translation)

Aplikasi Web dan CLI untuk mengonversi web novel dari **Kakuyomu** (Jepang) menjadi file **EPUB** full English menggunakan model AI penerjemah lokal (**Sugoi V4 CTranslate2**).

---

## 🎨 Tampilan Web (Neo-Brutalism & Mobile-Oriented)

* **Desain:** Mengusung gaya *Neo-Brutalism* dengan palet warna khusus:
  * `#55423C` (Dark Espresso / Cocoa)
  * `#FFC0AD` (Peach Coral)
  * `#E78FB3` (Muted Candy Pink)
  * `#D7FF28` (Neo Lime Highlighter)
  * `#FBFAF6` (Canvas Grid Background)
* **Frontend:** Dibangun menggunakan **Angular + TypeScript** (Strict types, **0% `any`**) dan **Tailwind CSS**.
* **Fitur Utama Web:**
  * Input link novel Kakuyomu dengan tombol *Gunakan Contoh*.
  * Deteksi otomatis judul, penulis, dan daftar bab.
  * Pilihan cakupan chapter:
    * Bab saat ini saja
    * Rentang tertentu (custom range, misal `1-5`)
    * **Mode Sampe Tamat (All Chapters):** Menggabungkan seluruh bab novel menjadi 1 file EPUB utuh.
  * *Live Progress Bar* pemantauan proses translasi secara *real-time*.
  * Tombol 1-klik download file `.epub` setelah selesai.
  * Tidak menyertakan gambar cover pada file EPUB (sesuai permintaan).

---

## 📁 Struktur Folder Proyek yang Rapi

```text
NOVEL TL/
├── core/                  # Modular Python Engine
│   ├── scraper.py         # Parser novel & chapter Kakuyomu
│   ├── epub_builder.py    # EPUB3 builder (Clean CSS, No Cover)
│   ├── cache_manager.py   # Resumable chapter cache
│   └── translators/       # Sugoi V4 & Local LLM translators
├── web/                   # Angular + TypeScript + Tailwind CSS Frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── models/    # Strict TypeScript interfaces (No `any`)
│   │   │   ├── services/  # API Client service
│   │   │   └── components/# Modular UI Components
│   └── ...
├── output/                # Folder penyimpanan semua file .epub hasil generasi
├── cache/                 # Cache chapter yang sudah diterjemahkan
├── models/                # File model Sugoi V4 CTranslate2
├── glossary.json          # Kamus nama karakter (Japanese -> English)
├── server.py              # Backend FastAPI & Web Hosting
├── novel_tl.py            # Terminal CLI Runner
├── start.bat              # Launcher 1-klik (Buka Web / CLI)
├── requirements.txt       # Dependensi Python
└── README.md
```

---

## 🚀 Cara Menjalankan

### Cara 1: Menggunakan Launcher 1-Klik (`start.bat`)
Cukup klik ganda (double-click) file **`start.bat`**.
* Tekan `Enter` untuk membuka Web App di browser (**`http://localhost:8000`**).
* Atau ketik `2` untuk masuk ke mode CLI interaktif terminal.

### Cara 2: Menjalankan Server Web Secara Manual
```powershell
python server.py
```
Lalu buka browser di **`http://localhost:8000`**.

### Cara 3: Menggunakan Perintah CLI
```powershell
# Download bab saat ini
python novel_tl.py --url "https://kakuyomu.jp/works/2912051607243271731/episodes/2912051607330854893" --range current

# Download semua bab (Sampe Tamat)
python novel_tl.py --url "https://kakuyomu.jp/works/2912051607243271731" --range all
```
Semua file `.epub` yang dihasilkan akan otomatis tersimpan rapi di folder **`output/`**.
