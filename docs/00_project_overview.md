# 00 — Project Overview

## 1. Tujuan

Proyek ini bertujuan membangun Data Warehouse sederhana dari dataset OLTP BikeStores. Proses pengerjaan mencakup pemahaman proses bisnis, perancangan struktur dimensional, data profiling, data cleansing, ETL, validasi hasil, hingga otomatisasi proses ETL melalui scheduler.

## 2. Sumber Data

Dataset yang digunakan adalah **Bike Store Sample Database** dari Kaggle.

Dataset terdiri atas sembilan file CSV:

| File | Jumlah Baris | Fungsi Utama |
|---|---:|---|
| `brands.csv` | 9 | Master merek produk |
| `categories.csv` | 7 | Master kategori produk |
| `customers.csv` | 1.445 | Data pelanggan |
| `order_items.csv` | 4.722 | Detail item setiap order |
| `orders.csv` | 1.615 | Header transaksi/order |
| `products.csv` | 321 | Master produk |
| `staffs.csv` | 10 | Data pegawai |
| `stocks.csv` | 939 | Stok produk per toko |
| `stores.csv` | 3 | Master toko |

## 3. Ruang Lingkup

Ruang lingkup proyek dibatasi agar tetap sederhana, tetapi mencakup seluruh siklus utama pembangunan Data Warehouse.

```text
OLTP Dataset
     │
     ▼
Business Process Analysis
     │
     ▼
Dimensional Design
     │
     ▼
Data Profiling
     │
     ▼
Data Quality Checklist
     │
     ▼
Data Cleansing
     │
     ▼
ETL
     │
     ▼
Data Warehouse
     │
     ▼
Validation
     │
     ▼
Scheduler / Automation
```

## 4. Rancangan Data Warehouse

Rancangan menggunakan:

- **2 fact table**
- **3 dimension table**

### Fact Table

1. `fakta_penjualan_bulanan`
2. `fakta_pengiriman_bulanan`

### Dimension Table

1. `dim_produk`
2. `dim_toko`
3. `dim_waktu`

## 5. Grain

### `fakta_penjualan_bulanan`

> Satu baris merepresentasikan ringkasan penjualan **satu produk pada satu toko dalam satu bulan**.

```text
Grain = Produk × Toko × Bulan
```

### `fakta_pengiriman_bulanan`

> Satu baris merepresentasikan ringkasan order/pengiriman **satu toko dalam satu bulan berdasarkan order_date**.

```text
Grain = Toko × Bulan
```

## 6. Mengapa Fakta Stok Tidak Digunakan

File `stocks.csv` hanya memiliki:

```text
store_id
product_id
quantity
```

Dataset tidak menyediakan atribut waktu historis untuk stok. Karena itu, membangun fakta stok historis dengan `id_waktu` akan menciptakan informasi waktu yang tidak tersedia pada sumber.

Fakta stok hanya layak digunakan sebagai **periodic snapshot fact** apabila snapshot mulai dikumpulkan sejak pipeline berjalan.

Untuk menjaga ketepatan terhadap data sumber, proyek ini menggunakan dua fakta utama: penjualan dan pengiriman.

## 7. Tools

Tools implementasi belum dikunci. Kandidat utama:

- Python
- Pandas
- SQL / DBMS
- Scheduler sistem atau scheduler berbasis Python

Pemilihan final akan didokumentasikan pada tahap implementasi ETL.

## 8. Status

**Status:** Tahap overview selesai.

**Tahap berikutnya:** Pemahaman proses bisnis.
