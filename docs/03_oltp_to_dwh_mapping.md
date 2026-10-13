# 03 — OLTP to DWH Mapping

## 1. Tujuan

Tahap ini menentukan secara eksplisit:

- kolom target di Data Warehouse;
- tabel dan kolom sumber pada OLTP;
- join yang diperlukan;
- transformasi yang harus dilakukan;
- business rule yang berlaku.

Dokumen ini menjadi spesifikasi awal untuk implementasi ETL.

---

# 2. Source yang Digunakan

```text
brands.csv
categories.csv
products.csv
stores.csv
orders.csv
order_items.csv
```

Belum digunakan:

```text
customers.csv
staffs.csv
stocks.csv
```

---

# 3. Mapping `dim_produk`

## 3.1 Relasi Source

```text
               brands
                 ▲
                 │ brand_id
                 │
products ────────┤
                 │
                 │ category_id
                 ▼
             categories
```

## 3.2 Mapping

| Target DWH | Source OLTP | Transformasi |
|---|---|---|
| `id_produk` | DWH | Generate surrogate key |
| `id_produk_oltp` | `products.product_id` | Copy |
| `nama_produk` | `products.product_name` | Trim/clean jika diperlukan |
| `merek` | `brands.brand_name` | Join `products.brand_id = brands.brand_id` |
| `kategori` | `categories.category_name` | Join `products.category_id = categories.category_id` |
| `tahun_model` | `products.model_year` | Validasi numeric/domain |
| `harga_list` | `products.list_price` | Validasi numeric dan non-negatif |

## 3.3 SQL Konseptual

```sql
SELECT
    p.product_id,
    p.product_name,
    b.brand_name,
    c.category_name,
    p.model_year,
    p.list_price
FROM products AS p
JOIN brands AS b
    ON p.brand_id = b.brand_id
JOIN categories AS c
    ON p.category_id = c.category_id;
```

---

# 4. Mapping `dim_toko`

## 4.1 Source

`stores.csv`

```text
store_id
store_name
phone
email
street
city
state
zip_code
```

## 4.2 Mapping

| Target DWH | Source OLTP | Transformasi |
|---|---|---|
| `id_toko` | DWH | Generate surrogate key |
| `id_toko_oltp` | `stores.store_id` | Copy |
| `nama_toko` | `stores.store_name` | Trim |
| `alamat` | `stores.street` | Trim/standardisasi |
| `kota` | `stores.city` | Trim/standardisasi |
| `state` | `stores.state` | Trim/validasi |
| `kode_pos` | `stores.zip_code` | Standardisasi format |
| `telepon` | `stores.phone` | Standardisasi bila diperlukan |
| `email` | `stores.email` | Trim/lowercase bila diperlukan |

---

# 5. Mapping `dim_waktu`

## 5.1 Source

```text
orders.order_date
```

## 5.2 Grain

```text
1 row = 1 month
```

## 5.3 Mapping

| Target DWH | Source | Transformasi |
|---|---|---|
| `id_waktu` | `orders.order_date` | Format `YYYYMM` |
| `tahun` | `orders.order_date` | Extract year |
| `bulan` | `orders.order_date` | Extract month |
| `nama_bulan` | `orders.order_date` | Month name |
| `kuartal` | `orders.order_date` | Q1–Q4 |

Contoh:

```text
Source:
2018-01-15

Target:
id_waktu   = 201801
tahun      = 2018
bulan      = 1
nama_bulan = January
kuartal    = Q1
```

---

# 6. Mapping `fakta_penjualan_bulanan`

## 6.1 Source

```text
orders.csv
     │
     │ order_id
     ▼
order_items.csv
```

## 6.2 Filter Bisnis

```text
orders.order_status = 4
```

Hanya Completed order yang diperlakukan sebagai penjualan terealisasi.

## 6.3 Grain

```text
id_waktu
+ id_toko
+ id_produk
```

## 6.4 Mapping

| Target | Source | Transformasi |
|---|---|---|
| `id_fakta_penjualan` | DWH | Generate |
| `id_waktu` | `orders.order_date` | YYYYMM → lookup `dim_waktu` |
| `id_toko` | `orders.store_id` | Lookup `dim_toko.id_toko_oltp` |
| `id_produk` | `order_items.product_id` | Lookup `dim_produk.id_produk_oltp` |
| `jumlah_order` | `orders.order_id` | `COUNT(DISTINCT order_id)` |
| `total_qty` | `order_items.quantity` | `SUM(quantity)` |
| `total_penjualan_kotor` | `quantity`, `list_price` | `SUM(quantity * list_price)` |
| `total_diskon` | `quantity`, `list_price`, `discount` | `SUM(quantity * list_price * discount)` |
| `total_penjualan_bersih` | `quantity`, `list_price`, `discount` | `SUM(quantity * list_price * (1-discount))` |

## 6.5 Formula

```text
gross
=
quantity × list_price
```

```text
discount_value
=
quantity × list_price × discount
```

```text
net
=
quantity × list_price × (1 - discount)
```

Validasi:

```text
gross - discount_value = net
```

---

# 7. Mapping `fakta_pengiriman_bulanan`

## 7.1 Source

```text
orders.csv
```

## 7.2 Grain

```text
id_waktu
+ id_toko
```

Periode ditentukan berdasarkan:

```text
orders.order_date
```

Bukan `shipped_date`.

Alasannya, order yang Pending, Processing, atau Rejected dapat tidak memiliki `shipped_date`.

## 7.3 Mapping

| Target | Source | Transformasi |
|---|---|---|
| `id_fakta_pengiriman` | DWH | Generate |
| `id_waktu` | `orders.order_date` | YYYYMM → lookup |
| `id_toko` | `orders.store_id` | Lookup |
| `jumlah_order` | `orders.order_id` | COUNT |
| `jumlah_order_pending` | `order_status` | COUNT status = 1 |
| `jumlah_order_diproses` | `order_status` | COUNT status = 2 |
| `jumlah_order_ditolak` | `order_status` | COUNT status = 3 |
| `jumlah_order_selesai` | `order_status` | COUNT status = 4 |
| `jumlah_order_terlambat` | `shipped_date`, `required_date` | COUNT shipped > required |
| `rata_rata_hari_proses` | `order_date`, `shipped_date` | AVG(shipped - order) |

## 7.4 Rule Status

```text
1 = Pending
2 = Processing
3 = Rejected
4 = Completed
```

Validasi:

```text
jumlah_order
=
pending
+ processing
+ rejected
+ completed
```

## 7.5 Rule Keterlambatan

```text
IF shipped_date IS NOT NULL
AND shipped_date > required_date
THEN terlambat = 1
ELSE terlambat = 0
```

`NULL shipped_date` tidak otomatis dianggap sebagai data rusak ataupun terlambat.

## 7.6 Lama Proses

```text
IF shipped_date IS NOT NULL
THEN hari_proses = shipped_date - order_date
```

Kemudian:

```text
rata_rata_hari_proses
=
AVG(hari_proses)
```

---

# 8. Mapping Keseluruhan

```text
┌────────────┐
│   brands   │
└─────┬──────┘
      │
      │
┌─────▼──────┐
│  products  │─────────────┐
└─────┬──────┘             │
      │                    │
      │                    ▼
┌─────▼──────────┐   ┌───────────────┐
│  categories    │   │  dim_produk   │
└────────────────┘   └───────┬───────┘
                              │
                              │
                              ▼
                       ┌──────────────────────┐
┌──────────────┐       │ fakta_penjualan     │
│ order_items  │──────▶│      _bulanan       │
└──────┬───────┘       └──────────┬───────────┘
       │                          ▲
       │ order_id                 │
       ▼                          │
┌──────────────┐                  │
│    orders    │──────────────────┘
└──────┬───────┘
       │
       ├──────────────▶ dim_waktu
       │
       ├──────────────▶ fakta_pengiriman_bulanan
       │
       │
       │ store_id
       ▼
┌──────────────┐
│    stores    │──────────────▶ dim_toko
└──────────────┘
```

Versi alur yang lebih ringkas:

```text
products + brands + categories
              │
              ▼
          dim_produk
              │
              ▼
orders + order_items ──▶ fakta_penjualan_bulanan
   │                          ▲
   │                          │
   ├────────▶ dim_waktu ──────┤
   │                          │
   ├────────▶ fakta_pengiriman_bulanan
   │                          ▲
   ▼                          │
 stores ─────────▶ dim_toko ──┘
```

---

# 9. Keputusan Penting

## 9.1 Surrogate Key

DWH memiliki key sendiri:

```text
id_produk
id_toko
```

ID OLTP tetap disimpan:

```text
id_produk_oltp
id_toko_oltp
```

Tujuannya agar lookup dan data lineage tetap dapat dilakukan.

## 9.2 Denormalisasi Produk

OLTP:

```text
products
   ├── brands
   └── categories
```

DWH:

```text
dim_produk
├── nama_produk
├── merek
└── kategori
```

Ini disengaja untuk mempermudah query analitik.

## 9.3 `order_date` sebagai Acuan Bulan

Kedua fakta menggunakan bulan dari `order_date`.

```text
order_date
    │
    ▼
 id_waktu
```

`required_date` dan `shipped_date` digunakan sebagai atribut perhitungan operasional, bukan sebagai key waktu utama pada model saat ini.

---

# 10. Validasi yang Akan Dilakukan Saat ETL

Mapping ini juga menentukan pemeriksaan yang nantinya harus dilakukan.

### Penjualan

```text
total_penjualan_kotor
-
total_diskon
=
total_penjualan_bersih
```

### Order Status

```text
jumlah_order
=
pending + processing + rejected + completed
```

### Referential Integrity

Setiap:

```text
id_produk
id_toko
id_waktu
```

pada fact table harus memiliki pasangan pada dimension table.

---

# 11. Status

**Status:** Mapping OLTP → DWH selesai untuk rancangan awal.

Belum dilakukan:

```text
✗ Profiling
✗ Cleansing
✗ ETL
✗ Load ke DWH
✗ Scheduler
```

**Tahap berikutnya:** `04_data_profiling.md`.
