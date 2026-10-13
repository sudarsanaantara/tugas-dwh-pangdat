# 07 — ETL Design

## 1. Tujuan

Tahap ini mendefinisikan rancangan ETL setelah proses cleansing berhasil dijalankan.

Pada tahap ini **belum dilakukan load ke database**. Fokusnya adalah menentukan urutan proses, sumber setiap target, aturan transformasi, dependensi antar tabel, dan validasi sebelum implementasi.

Alur utama:

```text
STAGING CLEAN
     │
     ▼
Build Dimensions
     │
     ├── dim_waktu
     ├── dim_toko
     └── dim_produk
     │
     ▼
Build Facts
     │
     ├── fakta_penjualan_bulanan
     └── fakta_pengiriman_bulanan
     │
     ▼
Validation
     │
     ▼
Load to DWH
```

---

## 2. Input ETL

ETL **tidak membaca langsung dari raw source**.

Input resmi ETL adalah:

```text
data/staging/clean/
├── brands.csv
├── categories.csv
├── customers.csv
├── order_items.csv
├── orders.csv
├── products.csv
├── staffs.csv
├── stocks.csv
└── stores.csv
```

Walaupun seluruh file tersedia, model DWH versi awal hanya menggunakan:

```text
brands.csv
categories.csv
products.csv
stores.csv
orders.csv
order_items.csv
```

---

## 3. Urutan Eksekusi

Urutan ETL harus menjaga referential integrity.

```text
1. Load staging clean
2. Build dim_waktu
3. Build dim_toko
4. Build dim_produk
5. Validate dimensions
6. Build fakta_penjualan_bulanan
7. Build fakta_pengiriman_bulanan
8. Validate facts
9. Export / load ke DWH
10. Simpan ETL log
```

Dimensi harus dibangun lebih dahulu karena fact table membutuhkan key dari dimensi.

---

# 4. ETL `dim_waktu`

## 4.1 Source

```text
orders.order_date
```

## 4.2 Grain

```text
1 row = 1 bulan
```

## 4.3 Transformasi

Dari setiap `order_date`:

```text
YYYY-MM-DD
    │
    ├── tahun
    ├── bulan
    ├── nama_bulan
    ├── kuartal
    └── id_waktu = YYYYMM
```

Contoh:

```text
order_date = 2018-03-15

id_waktu   = 201803
tahun      = 2018
bulan      = 3
nama_bulan = March
kuartal    = Q1
```

## 4.4 Output

```text
dim_waktu
├── id_waktu      PK
├── tahun
├── bulan
├── nama_bulan
└── kuartal
```

## 4.5 Validasi

```text
✓ id_waktu unik
✓ tidak NULL
✓ bulan berada pada 1..12
✓ kuartal berada pada Q1..Q4
✓ satu kombinasi tahun-bulan hanya satu record
```

---

# 5. ETL `dim_toko`

## 5.1 Source

```text
stores.csv
```

## 5.2 Grain

```text
1 row = 1 toko
```

## 5.3 Transformasi

Mapping:

```text
stores.store_id    → id_toko_oltp
stores.store_name  → nama_toko
stores.street      → alamat
stores.city        → kota
stores.state       → state
stores.zip_code    → kode_pos
stores.phone       → telepon
stores.email       → email
```

Tambahkan key DWH:

```text
id_toko
```

## 5.4 Output

```text
dim_toko
├── id_toko        PK
├── id_toko_oltp
├── nama_toko
├── alamat
├── kota
├── state
├── kode_pos
├── telepon
└── email
```

## 5.5 Validasi

```text
✓ id_toko unik
✓ id_toko_oltp unik
✓ tidak ada source store yang hilang
```

---

# 6. ETL `dim_produk`

## 6.1 Source

```text
products.csv
brands.csv
categories.csv
```

## 6.2 Join

```text
products.brand_id
       │
       ▼
brands.brand_id
```

dan:

```text
products.category_id
       │
       ▼
categories.category_id
```

## 6.3 Transformasi

```text
products.product_id      → id_produk_oltp
products.product_name    → nama_produk
brands.brand_name        → merek
categories.category_name → kategori
products.model_year      → tahun_model
products.list_price      → harga_list
```

Tambahkan:

```text
id_produk
```

sebagai key DWH.

## 6.4 Output

```text
dim_produk
├── id_produk       PK
├── id_produk_oltp
├── nama_produk
├── merek
├── kategori
├── tahun_model
└── harga_list
```

## 6.5 Validasi

```text
✓ id_produk unik
✓ id_produk_oltp unik
✓ jumlah hasil join = jumlah products
✓ tidak ada merek NULL akibat join
✓ tidak ada kategori NULL akibat join
```

---

# 7. ETL `fakta_penjualan_bulanan`

## 7.1 Source

```text
orders.csv
order_items.csv
dim_waktu
dim_toko
dim_produk
```

## 7.2 Filter

Hanya order selesai:

```text
order_status = 4
```

## 7.3 Join Source

```text
orders.order_id
      │
      ▼
order_items.order_id
```

## 7.4 Grain

```text
1 row =
1 bulan
× 1 toko
× 1 produk
```

Unique business grain:

```text
id_waktu + id_toko + id_produk
```

## 7.5 Lookup Dimension Key

```text
orders.order_date
    └── YYYYMM
          └── lookup dim_waktu.id_waktu

orders.store_id
    └── lookup dim_toko.id_toko_oltp
          └── id_toko

order_items.product_id
    └── lookup dim_produk.id_produk_oltp
          └── id_produk
```

## 7.6 Measure

```text
jumlah_order
= COUNT(DISTINCT order_id)
```

```text
total_qty
= SUM(quantity)
```

```text
total_penjualan_kotor
= SUM(quantity × list_price)
```

```text
total_diskon
= SUM(quantity × list_price × discount)
```

```text
total_penjualan_bersih
= SUM(quantity × list_price × (1 - discount))
```

## 7.7 Output

```text
fakta_penjualan_bulanan
├── id_fakta_penjualan      PK
├── id_waktu                FK
├── id_toko                 FK
├── id_produk               FK
├── jumlah_order
├── total_qty
├── total_penjualan_kotor
├── total_diskon
└── total_penjualan_bersih
```

## 7.8 Validasi

```text
✓ tidak ada FK NULL
✓ tidak ada orphan dimension key
✓ grain unik
✓ gross - discount = net
✓ hanya Completed order yang masuk
```

---

# 8. ETL `fakta_pengiriman_bulanan`

## 8.1 Source

```text
orders.csv
dim_waktu
dim_toko
```

## 8.2 Grain

```text
1 row =
1 toko
× 1 bulan order
```

Unique business grain:

```text
id_waktu + id_toko
```

## 8.3 Periode

Periode menggunakan:

```text
order_date
```

bukan `shipped_date`.

## 8.4 Measure Status

```text
jumlah_order
= COUNT(order_id)
```

```text
jumlah_order_pending
= COUNT(order_status = 1)
```

```text
jumlah_order_diproses
= COUNT(order_status = 2)
```

```text
jumlah_order_ditolak
= COUNT(order_status = 3)
```

```text
jumlah_order_selesai
= COUNT(order_status = 4)
```

## 8.5 Measure Keterlambatan

```text
late_flag =
1 jika shipped_date > required_date
0 selain itu
```

Kemudian:

```text
jumlah_order_terlambat
= SUM(late_flag)
```

## 8.6 Lama Proses

Untuk record yang mempunyai `shipped_date`:

```text
hari_proses
= shipped_date - order_date
```

Kemudian:

```text
rata_rata_hari_proses
= AVG(hari_proses)
```

## 8.7 Output

```text
fakta_pengiriman_bulanan
├── id_fakta_pengiriman     PK
├── id_waktu                FK
├── id_toko                 FK
├── jumlah_order
├── jumlah_order_pending
├── jumlah_order_diproses
├── jumlah_order_ditolak
├── jumlah_order_selesai
├── jumlah_order_terlambat
└── rata_rata_hari_proses
```

## 8.8 Validasi

```text
✓ grain unik
✓ tidak ada FK NULL
✓ tidak ada orphan FK
```

Status reconciliation:

```text
jumlah_order
=
jumlah_order_pending
+ jumlah_order_diproses
+ jumlah_order_ditolak
+ jumlah_order_selesai
```

---

# 9. Dependency Diagram

```text
                    ┌──────────────────┐
                    │  staging/clean   │
                    └────────┬─────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
    ┌───────────┐      ┌───────────┐      ┌────────────┐
    │ dim_waktu │      │ dim_toko  │      │ dim_produk │
    └─────┬─────┘      └─────┬─────┘      └──────┬─────┘
          │                  │                    │
          │                  │                    │
          └────────┬─────────┴────────────┬───────┘
                   │                      │
                   ▼                      ▼
      ┌────────────────────────┐  ┌──────────────────────────┐
      │ fakta_penjualan_bulanan│  │fakta_pengiriman_bulanan │
      └────────────┬───────────┘  └─────────────┬────────────┘
                   │                            │
                   └──────────────┬─────────────┘
                                  ▼
                           ┌──────────────┐
                           │  Validation  │
                           └──────┬───────┘
                                  ▼
                           ┌──────────────┐
                           │     DWH      │
                           └──────────────┘
```

---

# 10. Idempotency

Pipeline final harus aman dijalankan kembali.

Tujuan:

```text
Run 1 → hasil benar
Run 2 → tidak menggandakan data
Run 3 → tetap konsisten
```

Implementasi teknisnya akan disesuaikan dengan target database.

Pilihan umum:

```text
TRUNCATE + reload
```

untuk proyek batch sederhana, atau:

```text
UPSERT / MERGE
```

jika ingin incremental load.

Untuk proyek ini, keputusan final dibuat pada tahap implementasi setelah target DB dipilih.

---

# 11. Logging

Setiap ETL run minimal mencatat:

```text
run_id
start_time
end_time
status
source_rows
output_rows
error_message
```

Contoh:

```text
run_id      = 20261014_001
process     = build_dim_produk
source_rows = 321
output_rows = 321
status      = SUCCESS
```

---

# 12. Kriteria Lulus ETL

Sebelum dianggap berhasil:

```text
DIMENSIONS
✓ key unik
✓ jumlah record masuk akal
✓ source key tidak hilang

FACTS
✓ grain unik
✓ seluruh FK valid
✓ aggregation benar
✓ reconciliation rule lolos

PIPELINE
✓ dapat dijalankan ulang
✓ menghasilkan log
✓ tidak membaca raw secara langsung
```

---

# 13. Keputusan yang Masih Harus Dibuat

Sebelum implementasi database, satu keputusan teknis perlu dikunci:

```text
Target DWH Database
```

Contoh opsi:

```text
SQLite
PostgreSQL
MySQL / MariaDB
```

Untuk testing di Google Colab, transformasi dapat dibuat dengan Pandas terlebih dahulu. Setelah hasil tabel benar, load database dilakukan pada tahap implementasi.

---

# 14. Status

**Status:** ETL Design selesai.

Tahap berikutnya:

```text
08 — ETL Implementation
```

Sebelum menulis implementasi final, target database harus dipilih agar strategi key, constraint, load, dan scheduler tidak berubah di tengah pengerjaan.
