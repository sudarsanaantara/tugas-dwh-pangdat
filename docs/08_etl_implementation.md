# 08 — ETL Implementation (SQLite)

## 1. Tujuan

Tahap ini mengimplementasikan rancangan ETL ke dalam Python/Pandas dan SQLite.

Implementasi terdapat pada:

```text
BikeStores_DWH_02_ETL_SQLite.ipynb
```

Notebook ini merupakan notebook kedua dan dijalankan **setelah** notebook staging/cleansing berhasil.

---

## 2. Target Teknologi

```text
Development / Testing : Google Colab
Transformasi          : Python + Pandas
Storage Project       : Google Drive
Target DWH            : SQLite
Database File         : bikestores_dwh.db
```

SQLite dipilih untuk testing karena tidak membutuhkan database server dan cukup disimpan sebagai satu file.

---

## 3. Input

ETL membaca:

```text
data/staging/clean/
```

Bukan:

```text
data/raw/
```

File yang dibutuhkan:

```text
brands.csv
categories.csv
products.csv
stores.csv
orders.csv
order_items.csv
```

Jika staging clean tidak lengkap, notebook berhenti dan meminta notebook cleansing dijalankan terlebih dahulu.

---

## 4. Pipeline Implementasi

```text
STAGING CLEAN
     │
     ▼
┌─────────────────────┐
│ Build dim_waktu     │
├─────────────────────┤
│ Build dim_toko      │
├─────────────────────┤
│ Build dim_produk    │
└──────────┬──────────┘
           │
           ▼
   Validate Dimensions
           │
           ▼
┌──────────────────────────────┐
│ Build fakta_penjualan       │
├──────────────────────────────┤
│ Build fakta_pengiriman      │
└─────────────┬────────────────┘
              │
              ▼
        Validate Facts
              │
              ▼
        Recreate SQLite
              │
              ▼
         Load Dimensions
              │
              ▼
           Load Facts
              │
              ▼
       Validate Database
              │
              ▼
        Evidence + Log
```

---

## 5. Strategi Key

### `dim_waktu`

```text
id_waktu = YYYYMM
```

Contoh:

```text
201801
```

### `dim_toko`

```text
id_toko      = surrogate key DWH
id_toko_oltp = stores.store_id
```

### `dim_produk`

```text
id_produk      = surrogate key DWH
id_produk_oltp = products.product_id
```

Surrogate key dibuat deterministik berdasarkan source ID yang telah diurutkan sehingga hasil testing konsisten.

---

## 6. Fact Penjualan

Filter:

```text
order_status = 4
```

Grain:

```text
id_waktu
+ id_toko
+ id_produk
```

Measure:

```text
jumlah_order
total_qty
total_penjualan_kotor
total_diskon
total_penjualan_bersih
```

Formula:

```text
gross
= quantity × list_price

discount_value
= gross × discount

net
= gross - discount_value
```

Validasi:

```text
gross - discount = net
```

---

## 7. Fact Pengiriman

Grain:

```text
id_waktu
+ id_toko
```

Measure:

```text
jumlah_order
jumlah_order_pending
jumlah_order_diproses
jumlah_order_ditolak
jumlah_order_selesai
jumlah_order_terlambat
rata_rata_hari_proses
```

Rekonsiliasi:

```text
jumlah_order
=
pending
+ processing
+ rejected
+ completed
```

---

## 8. SQLite Schema

Constraint yang diterapkan meliputi:

```text
PRIMARY KEY
FOREIGN KEY
UNIQUE
NOT NULL
CHECK
```

SQLite foreign key enforcement diaktifkan dengan:

```sql
PRAGMA foreign_keys = ON;
```

Setelah load dilakukan:

```sql
PRAGMA foreign_key_check;
```

Hasil yang diharapkan:

```text
0 error
```

---

## 9. Strategi Idempotency untuk Testing

Tahap testing menggunakan **full reload**.

Urutan:

```text
DROP fact tables
DROP dimension tables
CREATE schema
LOAD dimensions
LOAD facts
```

Keuntungannya:

```text
Run 1 → hasil A
Run 2 → hasil A
Run 3 → hasil A
```

Bukan:

```text
Run 1 → A
Run 2 → A + A
Run 3 → A + A + A
```

Strategi incremental belum diperlukan pada tahap testing ini.

---

## 10. Expected Result

Untuk dataset BikeStores yang digunakan:

```text
dim_waktu                  ≈ 35 rows
dim_toko                   = 3 rows
dim_produk                 = 321 rows
fakta_penjualan_bulanan    ≈ 2,448 rows
fakta_pengiriman_bulanan   ≈ 93 rows
```

Rekonsiliasi utama:

```text
total order
= 1,615

late shipment
= 458
```

Angka ini adalah sanity check untuk dataset proyek saat ini. Notebook tetap menghitung expected value dari source secara dinamis.

---

## 11. Evidence

Notebook menghasilkan:

```text
data/evidence/etl/
├── etl_source_summary.csv
├── etl_output_summary.csv
├── dimension_validation.csv
├── fact_validation.csv
└── database_validation.csv
```

Log run disimpan pada:

```text
logs/
└── etl_run_<run_id>.csv
```

Database:

```text
database/
└── bikestores_dwh.db
```

---

## 12. Kriteria Lulus

Tahap implementasi ETL dianggap berhasil apabila:

```text
✓ seluruh dimension validation PASS
✓ seluruh fact validation PASS
✓ load SQLite berhasil
✓ database row count sesuai dataframe
✓ foreign_key_check = 0
✓ total order sesuai source
✓ late shipment sesuai source
✓ evidence tersimpan
✓ ETL log tersimpan
```

---

## 13. Status

**Status:** Notebook implementasi ETL SQLite telah disiapkan dan siap diuji di Google Colab.

Tahap baru dianggap final setelah:

```text
BikeStores_DWH_02_ETL_SQLite.ipynb
```

dijalankan dengan `Run all` dan seluruh validasi menghasilkan `PASS`.

Tahap selanjutnya:

```text
09 — Validation & Testing
```
