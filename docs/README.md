# Dokumen

Dokumen lomba tim NaS untuk Hackathon Deeptech 2026.

| Folder/File | Isi |
|---|---|
| [MILESTONES.md](MILESTONES.md) | Jadwal dan pembagian tugas |
| [proposal/](proposal/) | Sumber LaTeX mini proposal |
| [kirim/](kirim/) | PDF persis seperti yang dikirim ke panitia |
| [ketentuan.md](ketentuan.md) | Ringkasan ketentuan panitia |
| [catatan-teknis/](catatan-teknis/) | Catatan desain, alur teknis, dan rencana tes |

Dokumen panitia (poster dan FAQ) dan dokumen pergantian anggota (biodata, KTP, tanda tangan, surat pernyataan baru) disimpan lokal di folder panduan dan anggota, dan tidak diunggah ke repositori.

Mini proposal dikompilasi dari folder proposal dengan perintah berikut.

```
latexmk -pdf main.tex
```
