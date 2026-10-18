# Dokumen

Dokumen lomba tim NaS untuk Hackathon Deeptech 2026.

| Folder/File | Isi |
|---|---|
| [MILESTONES.md](MILESTONES.md) | Jadwal dan pembagian tugas |
| [proposal/](proposal/) | Sumber LaTeX mini proposal |
| [kirim/](kirim/) | PDF persis seperti yang dikirim ke panitia |
| [anggota/](anggota/) | Dokumen pergantian anggota: biodata anggota pengganti dan surat pernyataan baru |

Dokumen panitia (poster dan FAQ) disimpan lokal di folder panduan dan tidak diunggah ke repositori. Pindaian KTP dan tanda tangan anggota juga hanya disimpan lokal.

Mini proposal dikompilasi dari folder proposal dengan perintah berikut.

```
latexmk -pdf main.tex
```
