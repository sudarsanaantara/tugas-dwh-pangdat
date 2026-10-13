# 09 — Validation & Testing

## 1. Tujuan

Tahap ini membuktikan bahwa ETL yang berhasil dieksekusi juga menghasilkan Data Warehouse yang benar secara struktur, grain, integritas, agregasi, dan rekonsiliasi terhadap source.

Implementasi testing:

```text
BikeStores_DWH_03_Validation_Testing.ipynb
```

---

## 2. Prinsip

```text
"ETL tidak error"
        │
        ▼
belum cukup

"ETL menghasilkan data yang dapat direkonsiliasi"
        │
        ▼
baru dapat dinilai valid
```

Karena itu validasi dilakukan pada beberapa lapisan.

---

## 3. Lapisan Pengujian

```text
1. Structural Validation
2. Row Count Validation
3. Referential Integrity
4. Grain Validation
5. Sales Reconciliation
6. Shipping Reconciliation
7. Status Reconciliation
8. Analytic Query Sanity Test
9. Idempotency / Rerun Test
```

---

## 4. Structural Validation

Tabel wajib:

```text
dim_waktu
dim_toko
dim_produk
fakta_penjualan_bulanan
fakta_pengiriman_bulanan
```

Fact table juga diperiksa memiliki foreign key sesuai rancangan.

---

## 5. Row Count Validation

Rekonsiliasi dimensi utama:

```text
dim_toko
= jumlah stores source
```

```text
dim_produk
= jumlah products source
```

Fact table tidak dibandingkan langsung dengan row count source karena telah melalui proses agregasi.

---

## 6. Referential Integrity

Dijalankan:

```sql
PRAGMA foreign_key_check;
```

Expected:

```text
0 violation
```

---

## 7. Grain Validation

### Penjualan

```text
id_waktu + id_toko + id_produk
```

harus unik.

### Pengiriman

```text
id_waktu + id_toko
```

harus unik.

Expected:

```text
duplicate grain = 0
```

---

## 8. Sales Reconciliation

Source:

```text
Completed orders
      │
      ▼
order_items
      │
      ├── gross
      ├── discount
      └── net
```

Dibandingkan dengan:

```text
SUM(fakta_penjualan_bulanan)
```

Formula:

```text
gross
= quantity × list_price
```

```text
discount
= quantity × list_price × discount_rate
```

```text
net
= quantity × list_price × (1 - discount_rate)
```

Validasi:

```text
source gross    ≈ DWH gross
source discount ≈ DWH discount
source net      ≈ DWH net
```

dan:

```text
DWH gross - DWH discount ≈ DWH net
```

Toleransi kecil digunakan untuk floating-point.

---

## 9. Shipping Reconciliation

Validasi utama:

```text
source total order
=
SUM(fakta_pengiriman_bulanan.jumlah_order)
```

Late shipment:

```text
source shipped_date > required_date
=
SUM(jumlah_order_terlambat)
```

Status:

```text
jumlah_order
=
pending
+ processing
+ rejected
+ completed
```

---

## 10. Status Distribution

Seluruh distribusi status source dibandingkan dengan DWH:

```text
Pending
Processing
Rejected
Completed
```

Setiap status harus memiliki jumlah yang sama antara source dan DWH.

---

## 11. Analytic Query Sanity Test

Contoh query:

```text
penjualan per toko
penjualan per kategori
pengiriman per toko
```

Tujuannya memastikan Data Warehouse dapat menjawab kebutuhan analitik yang telah didefinisikan pada tahap business process.

---

## 12. Idempotency Test

Karena ETL testing menggunakan full reload:

```text
Run 1
  ↓
DWH State A

Run 2
  ↓
DWH State A
```

Hasil tidak boleh menjadi:

```text
Run 2
  ↓
A + A
```

Notebook validation menyimpan fingerprint:

```text
row count dimensions
row count facts
total gross
total discount
total net
total order
late shipment
```

### Prosedur

```text
1. Run all notebook 03
   → baseline dibuat

2. Run all notebook 02
   → ETL dijalankan ulang

3. Run all notebook 03
   → fingerprint dibandingkan

4. Expected:
   IDEMPOTENCY = PASS
```

---

## 13. Evidence

Notebook menghasilkan:

```text
data/evidence/validation/
├── validation_results.csv
├── row_counts.csv
├── sales_reconciliation.csv
├── status_reconciliation.csv
├── sales_by_store.csv
├── sales_by_category.csv
├── shipping_by_store.csv
└── idempotency_baseline.json
```

Log run:

```text
logs/
└── validation_run_<run_id>.csv
```

---

## 14. Kriteria Lulus

Tahap 09 dinyatakan selesai ketika:

```text
STRUCTURE               PASS
ROW COUNT               PASS
FOREIGN KEY             PASS
GRAIN                   PASS
SALES RECONCILIATION    PASS
SHIPPING RECONCILIATION PASS
STATUS RECONCILIATION   PASS
ANALYTIC QUERY          PASS
IDEMPOTENCY             PASS
```

dan:

```text
OVERALL STATUS: PASS
```

---

## 15. Status

**Status saat ini:** Notebook validation telah disiapkan.

Tahap ini menjadi final setelah notebook dijalankan sesuai prosedur idempotency dan seluruh test menunjukkan `PASS`.

Tahap selanjutnya:

```text
10 — Scheduler & Automation
```
