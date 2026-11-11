# Novel TL - Mobile App (React Native + Expo)

Aplikasi mobile resmi **Novel TL** berbasis React Native (Expo) dengan desain Neo-Brutalism presisi tinggi.

## Fitur Utama di Mobile
1. **Desain Neo-Brutalist:** Border tebal 2.5px, bayangan solid, palet warna Espresso, Peach, Pink, Acid Lime.
2. **Koneksi Backend Otomatis:** Otomatis mendeteksi IP lokal PC (`192.168.100.76:8000`) dan memiliki modal pengaturan jika menggunakan Cloudflare Tunnel / Ngrok.
3. **Download & Direct Open:** Begitu EPUB selesai digenerate, tombol **"BUKA / SIMPAN EPUB"** langsung memunculkan menu sistem Android/iOS untuk membuka file ke aplikasi e-reader favorit (Moon+ Reader, Apple Books, Google Play Books, dll.) atau menyimpan ke storage internal.
4. **Metode Jembatan (Bridge) & Fitur Cancel:** Dukungan penuh translasi Indonesia (JP -> EN Sugoi -> ID Qwen) dan pembatalan dengan hasil parsial.

## Cara Menjalankan di HP (Expo Go)
1. Install aplikasi **Expo Go** dari Google Play Store di HP kamu.
2. Pastikan HP dan PC terhubung ke Wi-Fi yang sama.
3. Di root project, jalankan:
   ```cmd
   start-mobile.bat
   ```
   atau:
   ```bash
   npm run mobile
   ```
4. Scan QR code yang muncul di terminal menggunakan kamera HP atau scanner Expo Go.

## Cara Build Menjadi File APK (Standalone)
Jika ingin menginstal sebagai file APK mandiri di HP tanpa Expo Go:
```bash
cd mobile
npx eas-cli build -p android --profile preview
```

