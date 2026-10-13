# 04 — Data Profiling

## 1. Tujuan

Tahap ini bertujuan **memahami kondisi data mentah sebelum dilakukan data cleansing**.

Pada tahap profiling, data **belum diperbaiki, belum dihapus, dan belum ditransformasikan ke Data Warehouse**. Seluruh pemeriksaan dilakukan untuk mengetahui:

- ukuran dan struktur dataset;
- missing value;
- duplikasi;
- keunikan candidate key;
- integritas foreign key;
- rentang numeric;
- validitas tanggal;
- distribusi status;
- whitespace pada atribut teks;
- indikasi pelanggaran business rule.

Hasil profiling menjadi dasar untuk tahap berikutnya:

```text
Data Profiling
      │
      ▼
Data Quality Checklist
      │
      ▼
Cleansing Rules
      │
      ▼
Data Cleansing
```

---

## 2. Dataset yang Diprofiling

Seluruh 9 file sumber tetap diperiksa meskipun tidak semuanya digunakan langsung pada DWH.

| File            | Rows | Columns | Full-row Duplicate | Total NULL |
| --------------- | ---- | ------- | ------------------ | ---------- |
| brands.csv      | 9    | 2       | 0                  | 0          |
| categories.csv  | 7    | 2       | 0                  | 0          |
| customers.csv   | 1445 | 9       | 0                  | 1267       |
| order_items.csv | 4722 | 6       | 0                  | 0          |
| orders.csv      | 1615 | 8       | 0                  | 170        |
| products.csv    | 321  | 6       | 0                  | 0          |
| staffs.csv      | 10   | 8       | 0                  | 1          |
| stocks.csv      | 939  | 3       | 0                  | 0          |
| stores.csv      | 3    | 8       | 0                  | 0          |

### Interpretasi Awal

Tidak ditemukan **full-row duplicate** pada seluruh file.

Namun, `0 full-row duplicate` belum berarti data pasti bersih. Duplikasi entitas dapat tetap terjadi walaupun keseluruhan baris tidak identik. Karena itu, candidate key dan foreign key diperiksa secara terpisah.

---

## 3. Pemeriksaan Missing Value

Missing value yang ditemukan:

```text
customers.phone     = 1,267 NULL dari 1,445 baris
staffs.manager_id   = 1 NULL dari 10 baris
orders.shipped_date = 170 NULL dari 1,615 baris
```

Persentase `customers.phone` yang kosong:

```text
1,267 / 1,445 × 100
≈ 87.68%
```

### Catatan Penting

Missing value **belum otomatis dianggap kesalahan**.

Contohnya:

- `staffs.manager_id = NULL` dapat merepresentasikan staff pada tingkat tertinggi yang memang tidak mempunyai manager.
- `orders.shipped_date = NULL` harus dianalisis bersama `order_status`.

Karena itu pada tahap profiling kita hanya mencatat kondisi. Keputusan apakah nilai tersebut harus dibersihkan akan dibuat pada tahap Data Quality Checklist dan Cleansing Rules.

---

## 4. Pemeriksaan Candidate Key / Primary Key

| File            | Candidate Key         | Duplicate Key Rows | NULL in Key | Status |
| --------------- | --------------------- | ------------------ | ----------- | ------ |
| brands.csv      | brand_id              | 0                  | 0           | PASS   |
| categories.csv  | category_id           | 0                  | 0           | PASS   |
| customers.csv   | customer_id           | 0                  | 0           | PASS   |
| orders.csv      | order_id              | 0                  | 0           | PASS   |
| order_items.csv | order_id + item_id    | 0                  | 0           | PASS   |
| products.csv    | product_id            | 0                  | 0           | PASS   |
| staffs.csv      | staff_id              | 0                  | 0           | PASS   |
| stocks.csv      | store_id + product_id | 0                  | 0           | PASS   |
| stores.csv      | store_id              | 0                  | 0           | PASS   |

### Hasil

Seluruh candidate key yang diperiksa:

```text
✓ tidak mengandung NULL
✓ tidak memiliki duplicate key
```

Khusus tabel yang secara alami menggunakan composite key:

```text
order_items:
    order_id + item_id

stocks:
    store_id + product_id
```

---

## 5. Pemeriksaan Referential Integrity

| Child FK                   | Parent Key                 | Orphan Rows | Status |
| -------------------------- | -------------------------- | ----------- | ------ |
| products.csv.brand_id      | brands.csv.brand_id        | 0           | PASS   |
| products.csv.category_id   | categories.csv.category_id | 0           | PASS   |
| orders.csv.customer_id     | customers.csv.customer_id  | 0           | PASS   |
| orders.csv.store_id        | stores.csv.store_id        | 0           | PASS   |
| orders.csv.staff_id        | staffs.csv.staff_id        | 0           | PASS   |
| order_items.csv.order_id   | orders.csv.order_id        | 0           | PASS   |
| order_items.csv.product_id | products.csv.product_id    | 0           | PASS   |
| staffs.csv.store_id        | stores.csv.store_id        | 0           | PASS   |
| staffs.csv.manager_id      | staffs.csv.staff_id        | 0           | PASS   |
| stocks.csv.store_id        | stores.csv.store_id        | 0           | PASS   |
| stocks.csv.product_id      | products.csv.product_id    | 0           | PASS   |

### Hasil

Tidak ditemukan **orphan foreign key** pada relasi yang diperiksa.

Contoh:

```text
order_items.product_id
        │
        └── seluruh nilainya ditemukan pada products.product_id
```

dan:

```text
orders.store_id
        │
        └── seluruh nilainya ditemukan pada stores.store_id
```

Ini berarti struktur referensial dataset sumber berada dalam kondisi baik pada pemeriksaan awal.

---

## 6. Profiling Tanggal pada `orders`

| Kolom         | Non-NULL | Parse Failure | Tanggal Minimum | Tanggal Maksimum |
| ------------- | -------- | ------------- | --------------- | ---------------- |
| order_date    | 1615     | 0             | 2016-01-01      | 2018-12-28       |
| required_date | 1615     | 0             | 2016-01-03      | 2018-12-28       |
| shipped_date  | 1445     | 0             | 2016-01-03      | 2018-04-02       |

### Hasil

Semua nilai tanggal non-NULL dapat diparse sebagai tanggal.

```text
order_date:
2016-01-01 ───────────────────────────── 2018-12-28
```

`shipped_date` memiliki rentang lebih pendek karena tidak semua order mempunyai pengiriman.

---

## 7. Analisis `shipped_date` Berdasarkan Status

Distribusi status dan missing `shipped_date`:

| Status ID | Status     | Jumlah Order | Shipped NULL | Shipped Terisi |
| --------- | ---------- | ------------ | ------------ | -------------- |
| 1         | Pending    | 62           | 62           | 0              |
| 2         | Processing | 63           | 63           | 0              |
| 3         | Rejected   | 45           | 45           | 0              |
| 4         | Completed  | 1445         | 0            | 1445           |

Hubungannya sangat jelas:

```text
Pending      : 62 order  → 62 shipped_date NULL
Processing   : 63 order  → 63 shipped_date NULL
Rejected     : 45 order  → 45 shipped_date NULL
Completed    : 1,445     → 0 shipped_date NULL
```

Total:

```text
62 + 63 + 45 = 170
```

Jumlah tersebut sama dengan total `shipped_date` yang NULL.

### Kesimpulan Profiling

`shipped_date = NULL` **bukan indikasi otomatis data rusak**.

Pada dataset ini:

```text
order_status != Completed
        │
        └── shipped_date = NULL
```

dan:

```text
order_status = Completed
        │
        └── shipped_date terisi
```

Karena itu **jangan melakukan `fillna()` pada `shipped_date` secara sembarangan**.

---

## 8. Pemeriksaan Business Rule Dasar

| Pemeriksaan                       | Jumlah Temuan |
| --------------------------------- | ------------- |
| required_date < order_date        | 0             |
| shipped_date < order_date         | 0             |
| shipped_date > required_date      | 458           |
| Completed tanpa shipped_date      | 0             |
| Non-completed dengan shipped_date | 0             |
| quantity <= 0                     | 0             |
| discount < 0 atau > 1             | 0             |
| list_price < 0 pada order_items   | 0             |
| list_price < 0 pada products      | 0             |
| stock quantity < 0                | 0             |

### Interpretasi

Tidak ditemukan:

```text
required_date < order_date
shipped_date < order_date
quantity <= 0
discount di luar 0..1
harga negatif
stok negatif
Completed tanpa shipped_date
Non-completed dengan shipped_date
```

Ditemukan:

```text
458 order:
shipped_date > required_date
```

Ini **bukan data error**.

Kondisi tersebut justru merupakan kejadian bisnis yang valid dan akan digunakan untuk measure:

```text
jumlah_order_terlambat
```

pada `fakta_pengiriman_bulanan`.

---

## 9. Rentang Nilai Penting

### `order_items`

```text
quantity:
min = 1
max = 2

list_price:
min = 89.99
max = 11999.99

discount:
min = 0.05
max = 0.20
```

### `products`

```text
model_year:
min = 2016
max = 2019

list_price:
min = 89.99
max = 11999.99
```

### `stocks`

```text
quantity:
min = 0
max = 30
```

Tidak terlihat nilai numeric ekstrem yang langsung melanggar business rule dasar yang telah ditetapkan.

---

## 10. Pemeriksaan Whitespace

Pemeriksaan dilakukan pada seluruh kolom teks menggunakan konsep:

```python
value != value.strip()
```

Hasil yang menonjol:

```text
customers.street
= 1,445 dari 1,445 record memiliki leading/trailing whitespace
```

Artinya:

```text
100% nilai customers.street
memerlukan standardisasi whitespace
```

File/kolom teks lain tidak menunjukkan leading/trailing whitespace pada pemeriksaan yang sama.

### Status Temuan

Ini merupakan **candidate cleansing rule** yang nyata:

```text
customers.street
    │
    ▼
strip leading/trailing whitespace
```

Walaupun `customers` belum digunakan pada DWH versi saat ini, temuan tetap didokumentasikan karena dosen meminta proses data quality terhadap dataset sumber.

---

## 11. Ringkasan Temuan Profiling

```text
┌──────────────────────────────────────────┬────────────────────┐
│ Pemeriksaan                              │ Hasil              │
├──────────────────────────────────────────┼────────────────────┤
│ Full-row duplicate                       │ 0                  │
│ Duplicate candidate key                  │ 0                  │
│ Orphan foreign key                       │ 0                  │
│ Invalid date parsing                     │ 0                  │
│ Invalid quantity                         │ 0                  │
│ Invalid discount                         │ 0                  │
│ Negative price                           │ 0                  │
│ Negative stock                           │ 0                  │
│ customers.phone NULL                     │ 1,267              │
│ staffs.manager_id NULL                   │ 1                  │
│ orders.shipped_date NULL                 │ 170                │
│ Late shipment                            │ 458                │
│ customers.street with outer whitespace  │ 1,445              │
└──────────────────────────────────────────┴────────────────────┘
```

---

## 12. Apa yang Belum Boleh Dilakukan

Setelah profiling ini, kita **belum langsung membersihkan data**.

Contoh keputusan yang belum boleh dibuat tanpa evaluasi kualitas:

```text
✗ hapus semua NULL
✗ isi shipped_date yang kosong
✗ hapus order terlambat
✗ hapus row hanya karena terlihat tidak biasa
✗ standardisasi tanpa mendokumentasikan rule
```

Urutan yang benar:

```text
Profiling
    │
    ▼
Identifikasi kondisi
    │
    ▼
Klasifikasi menurut aspek Data Quality
    │
    ▼
Tentukan apakah:
    ├── valid
    ├── perlu standardisasi
    ├── perlu diperbaiki
    ├── perlu ditolak
    └── perlu dipertahankan apa adanya
```

---

## 13. File Hasil Profiling

Selain dokumen ini, hasil profiling disimpan dalam bentuk CSV agar pemeriksaan dapat ditelusuri kembali:

```text
profiling_summary.csv
profiling_columns.csv
profiling_pk_checks.csv
profiling_fk_checks.csv
profiling_date_checks.csv
profiling_order_status.csv
profiling_business_checks.csv
```

File-file tersebut menjadi **evidence/output teknis** dari tahap profiling.

---

## 14. Keputusan Tahap Ini

Dari tahap profiling, kita baru dapat menyimpulkan:

1. Struktur key dan referential integrity dataset cukup baik.
2. Tidak ditemukan duplicate penuh.
3. Terdapat missing values yang harus dianalisis berdasarkan konteks bisnis.
4. `shipped_date` NULL terbukti konsisten dengan order yang belum selesai/ditolak.
5. Terdapat 458 late shipment yang valid sebagai fenomena bisnis.
6. Terdapat masalah konsistensi whitespace pada seluruh `customers.street`.
7. Belum dilakukan perubahan terhadap source.

---

## 15. Status

**Status:** Data Profiling selesai untuk pemeriksaan awal dataset.

**Tahap berikutnya:**

```text
05_data_quality_checklist.md
```

Pada tahap berikutnya setiap temuan akan dipetakan ke checklist kualitas data Chapter 10, misalnya:

```text
Accuracy
Domain Integrity
Data Type
Consistency
Redundancy
Completeness
Duplication
Conformance to Business Rule
Structural Definiteness
Data Anomaly
Clarity
Timeliness
Usefulness
Adherence to Data Integrity Rules
```

Baru setelah checklist tersebut selesai, kita menentukan **cleansing rule**.
