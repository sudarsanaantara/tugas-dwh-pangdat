# 02 — Data Warehouse Design

## 1. Tujuan

Tahap ini mendefinisikan struktur dimensional Data Warehouse berdasarkan proses bisnis BikeStores.

Desain dibuat sederhana dengan dua fact table dan tiga conformed dimension.

## 2. Arsitektur Dimensional

```text
                         ┌──────────────────────┐
                         │      dim_produk      │
                         ├──────────────────────┤
                         │ PK id_produk         │
                         │    id_produk_oltp    │
                         │    nama_produk       │
                         │    merek             │
                         │    kategori          │
                         │    tahun_model       │
                         │    harga_list        │
                         └──────────┬───────────┘
                                    │ 1
                                    │
                                    │ *
                  ┌─────────────────▼──────────────────┐
                  │    fakta_penjualan_bulanan        │
                  ├────────────────────────────────────┤
                  │ PK id_fakta_penjualan             │
                  │ FK id_waktu                        │
                  │ FK id_toko                         │
                  │ FK id_produk                       │
                  │    jumlah_order                    │
                  │    total_qty                       │
                  │    total_penjualan_kotor           │
                  │    total_diskon                    │
                  │    total_penjualan_bersih          │
                  └──────────────┬───────────┬─────────┘
                                 │           │
                              *  │           │  *
                                 │           │
                              1  │           │  1
                    ┌────────────▼───┐   ┌──▼────────────────┐
                    │   dim_waktu    │   │     dim_toko      │
                    ├────────────────┤   ├───────────────────┤
                    │ PK id_waktu    │   │ PK id_toko        │
                    │    tahun       │   │    id_toko_oltp   │
                    │    bulan       │   │    nama_toko      │
                    │    nama_bulan  │   │    alamat         │
                    │    kuartal     │   │    kota           │
                    └──────┬─────────┘   │    state          │
                           │             │    kode_pos       │
                           │ 1           │    telepon        │
                           │             │    email          │
                           │ *           └──────┬────────────┘
                           │                    │ 1
                  ┌────────▼────────────────────▼───────────┐
                  │      fakta_pengiriman_bulanan          │
                  ├─────────────────────────────────────────┤
                  │ PK id_fakta_pengiriman                 │
                  │ FK id_waktu                            │
                  │ FK id_toko                             │
                  │    jumlah_order                        │
                  │    jumlah_order_pending                │
                  │    jumlah_order_diproses               │
                  │    jumlah_order_ditolak                │
                  │    jumlah_order_selesai                │
                  │    jumlah_order_terlambat              │
                  │    rata_rata_hari_proses               │
                  └─────────────────────────────────────────┘
```

## 3. Conformed Dimension

`dim_waktu` dan `dim_toko` digunakan oleh kedua fact table.

```text
                         dim_waktu
                        /         \
                       /           \
          fakta_penjualan      fakta_pengiriman
                       \           /
                        \         /
                         dim_toko
```

`dim_produk` hanya berhubungan dengan fakta penjualan karena grain fakta pengiriman tidak berada pada level produk.

## 4. `dim_produk`

### Grain

> Satu baris mewakili satu produk.

### Struktur

| Kolom | Peran | Keterangan |
|---|---|---|
| `id_produk` | PK | Surrogate key DWH |
| `id_produk_oltp` | Source key | `products.product_id` |
| `nama_produk` | Atribut | Nama produk |
| `merek` | Atribut | Hasil join dengan brands |
| `kategori` | Atribut | Hasil join dengan categories |
| `tahun_model` | Atribut | Model year produk |
| `harga_list` | Atribut | Harga daftar |

### Sumber

```text
products
   │
   ├──── brands
   │
   └──── categories
   │
   ▼
dim_produk
```

## 5. `dim_toko`

### Grain

> Satu baris mewakili satu toko.

| Kolom | Peran |
|---|---|
| `id_toko` | PK |
| `id_toko_oltp` | Source key |
| `nama_toko` | Atribut |
| `alamat` | Atribut |
| `kota` | Atribut |
| `state` | Atribut |
| `kode_pos` | Atribut |
| `telepon` | Atribut |
| `email` | Atribut |

## 6. `dim_waktu`

Karena kedua fakta menggunakan grain bulanan, dimensi waktu juga dibuat pada level bulan.

### Grain

> Satu baris mewakili satu bulan.

Contoh:

```text
id_waktu   = 201801
tahun      = 2018
bulan      = 1
nama_bulan = January
kuartal    = Q1
```

### Struktur

| Kolom | Peran |
|---|---|
| `id_waktu` | PK |
| `tahun` | Atribut |
| `bulan` | Atribut |
| `nama_bulan` | Atribut |
| `kuartal` | Atribut |

Format key:

```text
id_waktu = YYYYMM
```

## 7. `fakta_penjualan_bulanan`

### Grain

> Satu baris = satu produk × satu toko × satu bulan.

```text
UNIQUE (
    id_waktu,
    id_toko,
    id_produk
)
```

### Struktur

| Kolom | Peran |
|---|---|
| `id_fakta_penjualan` | PK |
| `id_waktu` | FK |
| `id_toko` | FK |
| `id_produk` | FK |
| `jumlah_order` | Measure |
| `total_qty` | Measure |
| `total_penjualan_kotor` | Measure |
| `total_diskon` | Measure |
| `total_penjualan_bersih` | Measure |

### Formula

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

Business rule:

```text
order_status = 4
```

Hanya order Completed yang masuk ke fakta penjualan.

## 8. `fakta_pengiriman_bulanan`

### Grain

> Satu baris = satu toko × satu bulan berdasarkan `order_date`.

```text
UNIQUE (
    id_waktu,
    id_toko
)
```

### Struktur

| Kolom | Peran |
|---|---|
| `id_fakta_pengiriman` | PK |
| `id_waktu` | FK |
| `id_toko` | FK |
| `jumlah_order` | Measure |
| `jumlah_order_pending` | Measure |
| `jumlah_order_diproses` | Measure |
| `jumlah_order_ditolak` | Measure |
| `jumlah_order_selesai` | Measure |
| `jumlah_order_terlambat` | Measure |
| `rata_rata_hari_proses` | Measure |

### Rule Status

```text
Pending    = order_status 1
Processing = order_status 2
Rejected   = order_status 3
Completed  = order_status 4
```

Rule validasi:

```text
jumlah_order
=
jumlah_order_pending
+ jumlah_order_diproses
+ jumlah_order_ditolak
+ jumlah_order_selesai
```

### Rule Keterlambatan

```text
terlambat
=
shipped_date > required_date
```

Hanya dievaluasi pada order yang memiliki `shipped_date`.

### Lama Proses

```text
hari_proses
=
shipped_date - order_date
```

Measure:

```text
rata_rata_hari_proses
=
AVG(hari_proses)
```

## 9. Keputusan Desain

### Mengapa hanya satu `dim_waktu`?

Karena dimensi yang sama dapat dipakai bersama oleh beberapa fakta. Membuat `dim_waktu_s1`, `dim_waktu_s2`, dan seterusnya hanya menggandakan struktur yang sama tanpa kebutuhan.

### Mengapa hanya satu `dim_toko`?

Alasan yang sama berlaku untuk toko. Toko mempunyai definisi yang sama bagi kedua fact table.

### Mengapa tidak ada `dim_customer` dan `dim_staff`?

Karena grain analisis saat ini tidak membutuhkan analisis berdasarkan pelanggan atau staff.

Jika pada tahap selanjutnya kebutuhan bisnis diperluas, kedua dimensi tersebut dapat ditambahkan.

### Mengapa tidak memakai fakta stok?

Karena dataset stok tidak memiliki riwayat waktu.

```text
stocks.csv
├── store_id
├── product_id
└── quantity
```

Tidak ada:

```text
snapshot_date
transaction_date
effective_date
```

Karena itu fakta stok historis tidak dapat dibangun secara sah dari source yang tersedia.

## 10. Status

**Status:** Desain dimensional final untuk versi awal proyek.

**Tahap berikutnya:** Mapping OLTP → DWH.
