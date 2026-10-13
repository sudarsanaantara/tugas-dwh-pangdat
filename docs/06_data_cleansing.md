# 06 — Data Cleansing

## 1. Tujuan

Tahap ini menerapkan cleansing terhadap **staging copy**, bukan terhadap source mentah.

Arsitektur:

```text
RAW CSV
   │
   │ immutable
   ▼
STAGING RAW
   │
   ├── validation
   ├── cleansing rules
   └── logging
   │
   ▼
STAGING CLEAN
```

Implementasi pengujian disediakan dalam notebook:

```text
BikeStores_DWH_01_Staging_Cleansing.ipynb
```

Notebook dirancang untuk dijalankan di Google Colab dengan penyimpanan Google Drive. Apabila raw dataset belum tersedia, notebook akan mencoba mengunduh dataset secara otomatis dari Kaggle.

---

## 2. Prinsip

Cleansing tidak berarti "mengubah semua nilai yang terlihat aneh".

Setiap perubahan harus mempunyai dasar dari:

```text
Data Profiling
      │
      ▼
Data Quality Checklist
      │
      ▼
Cleansing Decision
```

Karena itu:

```text
NULL yang valid       → dipertahankan
late shipment         → dipertahankan
duplicate yang tidak ada → tidak dibuat-buat
whitespace nyata      → dibersihkan
```

---

## 3. Rule yang Diterapkan

### RULE 01 — Trim Whitespace

Seluruh kolom string diperiksa dan leading/trailing whitespace dibuang.

```text
"  value  "
    ↓
"value"
```

Rule ini tidak mengubah spasi di tengah teks.

Temuan utama sebelumnya:

```text
customers.street
= 1,445 record terdampak
```

### RULE 02 — Parse Date

Kolom berikut pada `orders` harus dapat diparse sebagai tanggal:

```text
order_date
required_date
shipped_date
```

`shipped_date` boleh NULL bila konteks bisnisnya valid.

### RULE 03 — Preserve Valid NULL

Tidak dilakukan imputasi otomatis pada:

```text
customers.phone
orders.shipped_date
staffs.manager_id
```

Alasannya telah didokumentasikan pada Data Quality Checklist.

### RULE 04 — Preserve Late Shipment

Record:

```text
shipped_date > required_date
```

tidak dihapus atau diperbaiki, karena merupakan event bisnis yang sah.

### RULE 05 — No Unnecessary Deduplication

Karena profiling menemukan:

```text
full-row duplicate      = 0
duplicate candidate key = 0
```

maka pipeline tidak menghapus record secara deduplication pada tahap ini.

### RULE 06 — Preserve Raw Source

File pada:

```text
data/raw/
```

tidak pernah ditimpa.

---

## 4. Struktur Folder Google Colab / Drive

```text
BikeStores_DWH/
├── data/
│   ├── raw/
│   │   ├── brands.csv
│   │   ├── categories.csv
│   │   ├── customers.csv
│   │   ├── order_items.csv
│   │   ├── orders.csv
│   │   ├── products.csv
│   │   ├── staffs.csv
│   │   ├── stocks.csv
│   │   └── stores.csv
│   │
│   ├── staging/
│   │   ├── raw/
│   │   └── clean/
│   │
│   └── evidence/
│       └── cleansing/
│
└── logs/
```

### 4.1 Strategi Pengadaan Dataset

Notebook menggunakan strategi **local-first, Kaggle fallback**.

```text
Cek data/raw/
    │
    ├── seluruh file ditemukan
    │      └── download dilewati
    │
    └── ada file yang hilang
           │
           ▼
    Download dari Kaggle
           │
           ▼
    Copy hanya file yang belum ada
           │
           ▼
    Validasi ulang 9 file
```

Dataset sumber:

```text
dillonmyrick/bike-store-sample-database
```

Prinsip:

```text
✓ file yang sudah tersedia tidak ditimpa
✓ download hanya dilakukan bila diperlukan
✓ data/raw tetap menjadi immutable source
✓ pipeline tetap dapat direproduksi dari environment baru
```

---

## 5. Expected Validation

Setelah cleansing:

```text
Row count before = Row count after
```

Untuk seluruh tabel.

Expected result penting:

```text
customers.street outer whitespace
before = 1,445
after  = 0
```

Sementara:

```text
orders.shipped_date NULL
before = 170
after  = 170
```

Nilai 170 tetap dipertahankan karena NULL tersebut valid menurut status order.

---

## 6. Evidence yang Dihasilkan Notebook

```text
data/evidence/cleansing/
├── before_summary.csv
├── after_summary.csv
├── cleansing_log.csv
├── row_count_validation.csv
├── null_preservation_validation.csv
├── preclean_pk_checks.csv
├── preclean_fk_checks.csv
└── preclean_business_checks.csv
```

Evidence ini memungkinkan proses cleansing dibuktikan dan direproduksi.

---

## 7. Kriteria Lulus Tahap Cleansing

Tahap dianggap berhasil apabila:

```text
✓ semua raw file berhasil dibaca
✓ row count tidak berubah
✓ whitespace target sudah dibersihkan
✓ tanggal valid dapat diparse
✓ NULL valid tidak berubah
✓ tidak ada raw file yang ditimpa
✓ evidence cleansing berhasil dibuat
```

Jika salah satu validasi gagal:

```text
STOP
│
└── jangan lanjut ke ETL dimensi/fakta
```

---

## 8. Status

**Status saat ini:** Implementasi notebook cleansing telah disiapkan dan siap diuji di Google Colab.

Tahap ini baru dianggap final setelah notebook dijalankan pada Colab dan seluruh validation check menghasilkan hasil sesuai ekspektasi.

Tahap berikutnya setelah testing berhasil:

```text
07 — ETL Design
```
