# 01 — Business Process

## 1. Tujuan

Tahap ini bertujuan memahami bagaimana data pada BikeStores merepresentasikan proses bisnis sehari-hari sebelum dilakukan desain Data Warehouse.

Pemahaman proses bisnis penting karena fakta, dimensi, dan grain harus ditentukan berdasarkan kejadian bisnis yang benar-benar terjadi pada sistem OLTP.

## 2. Entitas Utama OLTP

Dataset memiliki entitas berikut:

| Entitas | File | Peran |
|---|---|---|
| Brand | `brands.csv` | Merek produk |
| Category | `categories.csv` | Kategori produk |
| Product | `products.csv` | Produk yang dijual |
| Customer | `customers.csv` | Pelanggan |
| Store | `stores.csv` | Cabang/toko |
| Staff | `staffs.csv` | Pegawai yang menangani order |
| Order | `orders.csv` | Transaksi utama |
| Order Item | `order_items.csv` | Detail barang dalam order |
| Stock | `stocks.csv` | Persediaan produk per toko |

## 3. Hubungan Proses Bisnis

Secara konseptual, alur bisnis dapat digambarkan sebagai berikut:

```text
┌──────────────┐
│   Customer   │
└──────┬───────┘
       │ membuat
       ▼
┌──────────────┐        ditangani oleh        ┌──────────────┐
│    Order     │─────────────────────────────▶│    Staff     │
└──────┬───────┘                              └──────┬───────┘
       │                                             │ bekerja di
       │ terjadi di                                  ▼
       │                                      ┌──────────────┐
       └─────────────────────────────────────▶│    Store     │
                                              └──────────────┘
       │
       │ memiliki
       ▼
┌──────────────┐
│ Order Items  │
└──────┬───────┘
       │ berisi
       ▼
┌──────────────┐
│   Product    │
└──────┬───────┘
       │
       ├──────────────▶ Brand
       │
       └──────────────▶ Category
```

Stok mempunyai hubungan tersendiri:

```text
Store ───────┐
             ├──▶ Stock ◀── Product
Product ─────┘
```

Satu record `stocks.csv` menyatakan jumlah stok suatu produk pada suatu toko, tetapi tidak memiliki informasi kapan nilai stok tersebut berlaku.

## 4. Proses Order

Satu order disimpan pada `orders.csv`.

Atribut penting:

```text
order_id
customer_id
order_status
order_date
required_date
shipped_date
store_id
staff_id
```

Satu order dapat memiliki beberapa item.

Hubungan:

```text
orders.order_id
       │
       │ 1
       │
       │ *
       ▼
order_items.order_id
```

Setiap item menyimpan:

```text
order_id
item_id
product_id
quantity
list_price
discount
```

Dengan struktur ini, nilai penjualan tidak berasal langsung dari `orders`, tetapi perlu dihitung dari detail item.

## 5. Logika Penjualan

Nilai bruto satu item:

```text
gross_sales = quantity × list_price
```

Nilai diskon:

```text
discount_value = quantity × list_price × discount
```

Nilai bersih:

```text
net_sales = quantity × list_price × (1 - discount)
```

Contoh:

```text
quantity   = 2
list_price = 1000
discount   = 0.20

gross_sales    = 2 × 1000
               = 2000

discount_value = 2 × 1000 × 0.20
               = 400

net_sales      = 2 × 1000 × (1 - 0.20)
               = 1600
```

## 6. Status Order

Status order digunakan untuk membedakan kondisi transaksi.

```text
1 = Pending
2 = Processing
3 = Rejected
4 = Completed
```

Untuk fakta penjualan, hanya order **Completed** yang dianggap sebagai penjualan terealisasi.

```text
fakta_penjualan_bulanan
        │
        └── filter order_status = 4
```

Untuk fakta pengiriman, seluruh status tetap dipertahankan karena distribusi status merupakan bagian dari analisis operasional.

## 7. Proses Pengiriman

Tiga atribut waktu utama:

```text
order_date
required_date
shipped_date
```

### Lama Proses

```text
hari_proses = shipped_date - order_date
```

Hanya dihitung ketika `shipped_date` tersedia.

### Keterlambatan

Order dikategorikan terlambat apabila:

```text
shipped_date > required_date
```

`shipped_date = NULL` tidak otomatis berarti terlambat. Nilai NULL dapat valid untuk order yang belum dikirim atau ditolak.

## 8. Pertanyaan Analitik yang Ingin Didukung

Dengan struktur DWH ini, contoh pertanyaan yang dapat dijawab adalah:

### Analisis Penjualan

- Berapa total penjualan bersih per bulan?
- Produk apa yang paling banyak terjual?
- Merek apa yang menghasilkan penjualan terbesar?
- Kategori apa yang paling banyak menghasilkan revenue?
- Toko mana yang memiliki performa penjualan tertinggi?
- Bagaimana tren penjualan per produk dan toko?

### Analisis Operasional Order/Pengiriman

- Berapa jumlah order setiap toko per bulan?
- Berapa banyak order completed, rejected, pending, dan processing?
- Toko mana yang paling banyak mengalami keterlambatan?
- Berapa rata-rata hari proses order setiap toko?
- Bagaimana perubahan performa fulfillment dari bulan ke bulan?

## 9. Keputusan

Tidak seluruh entitas OLTP harus menjadi dimensi DWH.

Pada tahap ini:

```text
Digunakan langsung:
✓ Products
✓ Brands
✓ Categories
✓ Stores
✓ Orders
✓ Order Items

Belum digunakan pada model analitik:
○ Customers
○ Staffs
○ Stocks
```

Keputusan ini mengikuti kebutuhan analisis dan grain yang telah ditetapkan.

## 10. Status

**Status:** Pemahaman proses bisnis selesai.

**Tahap berikutnya:** Finalisasi desain dimensional.
