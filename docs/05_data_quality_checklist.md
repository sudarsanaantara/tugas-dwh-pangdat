# 05 — Data Quality Checklist

## 1. Tujuan

Tahap ini memetakan hasil **Data Profiling** ke aspek kualitas data yang dibahas pada Chapter 10.

Prinsip utamanya:

```text
Profiling menemukan kondisi data
            │
            ▼
Data Quality menilai kondisi tersebut
            │
            ▼
Cleansing Rules menentukan tindakan
```

Pada tahap ini kita belum menjalankan cleansing massal. Kita hanya menentukan apakah suatu temuan:

```text
✓ valid dan dipertahankan
△ perlu standardisasi
! perlu perhatian
✗ harus ditolak/diperbaiki
```

---

## 2. Prinsip Penting

Tidak semua nilai yang terlihat "aneh" adalah data kotor.

Contoh:

```text
orders.shipped_date = NULL
```

tidak otomatis salah, karena pada dataset ini NULL tersebut konsisten dengan order yang belum selesai atau ditolak.

Sebaliknya:

```text
customers.street
```

memiliki leading/trailing whitespace pada seluruh record, sehingga ini merupakan masalah **consistency/standardization** yang nyata.

---

## 3. Checklist Kualitas Data

| Aspek                             | Yang Diperiksa                                                                                           | Evidence                                                                                                                                                    | Hasil                    | Keputusan / Tindakan                                                                                                                               |
| --------------------------------- | -------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Accuracy                          | Nilai numerik/tanggal yang secara jelas tidak masuk akal berdasarkan rule yang dapat diuji dari dataset. | Tidak ditemukan quantity <= 0, harga negatif, stock negatif, shipped_date < order_date, atau required_date < order_date.                                    | PASS_WITH_LIMITATION     | Tidak ada koreksi otomatis. Akurasi terhadap dunia nyata tidak dapat dibuktikan hanya dari CSV.                                                    |
| Domain Integrity                  | Nilai status, discount, quantity, harga, stok, serta rentang tanggal.                                    | Discount berada pada 0..1; quantity > 0; harga dan stok tidak negatif; status order berada pada domain yang digunakan.                                      | PASS                     | Pertahankan rule domain sebagai validasi ETL.                                                                                                      |
| Data Type                         | Kemampuan parse kolom tanggal dan kesesuaian kolom numerik utama.                                        | Semua tanggal non-NULL pada orders dapat diparse; kolom numeric utama terbaca sebagai numeric.                                                              | PASS                     | Tetap lakukan casting eksplisit di staging/ETL.                                                                                                    |
| Consistency                       | Konsistensi format dan whitespace pada data teks serta hubungan status dengan shipped_date.              | 1445 dari 1445 customers.street memiliki leading/trailing whitespace; pola shipped_date konsisten dengan status order.                                      | ISSUE_FOUND              | Trim whitespace pada atribut string yang relevan; jangan isi shipped_date yang NULL bila status bukan Completed.                                   |
| Redundancy                        | Duplikasi informasi dan full-row duplicate.                                                              | Tidak ditemukan full-row duplicate pada seluruh file. Redundansi struktural OLTP seperti brand/category melalui FK adalah bagian desain normalisasi.        | PASS_WITH_NOTE           | Tidak ada dedup otomatis. Denormalisasi hanya dilakukan saat membentuk dimensi DWH.                                                                |
| Completeness                      | NULL/missing value pada seluruh dataset.                                                                 | customers.phone NULL = 1267 (87.68%); staffs.manager_id NULL = 1; orders.shipped_date NULL = 170.                                                           | ISSUE_REQUIRES_CONTEXT   | Bedakan NULL valid vs NULL bermasalah. Jangan imputasi shipped_date; phone boleh dibiarkan NULL karena tidak dipakai pada model analitik saat ini. |
| Duplication                       | Full-row duplicate dan duplicate candidate key.                                                          | 0 full-row duplicate; 0 duplicate pada candidate key seluruh tabel yang diperiksa.                                                                          | PASS                     | Tidak ada deduplication yang diperlukan saat ini.                                                                                                  |
| Conformance to Business Rule      | Rule tanggal, status, completed order, quantity, discount, harga, stok, dan keterlambatan.               | 0 Completed tanpa shipped_date; 0 non-completed dengan shipped_date; 458 order terlambat adalah kejadian bisnis valid.                                      | PASS_WITH_BUSINESS_EVENT | Jangan menghapus late shipment. Gunakan sebagai measure jumlah_order_terlambat.                                                                    |
| Structural Definiteness           | Apakah atribut utama tersimpan pada field terpisah dan terstruktur.                                      | Nama, alamat, kota, state, zip, tanggal, status, quantity, price, discount tersimpan dalam kolom terpisah.                                                  | PASS                     | Tidak diperlukan pemecahan field tambahan untuk kebutuhan DWH saat ini.                                                                            |
| Data Anomaly                      | Indikasi field dipakai untuk isi yang tidak sesuai definisinya berdasarkan pola data yang tersedia.      | Tidak ditemukan indikasi kuat dari profiling otomatis bahwa field utama dipakai untuk informasi lain.                                                       | PASS_WITH_LIMITATION     | Pertahankan pemeriksaan manual/sampling saat cleansing.                                                                                            |
| Clarity                           | Kejelasan kode dan arti atribut.                                                                         | order_status berupa kode 1..4 sehingga membutuhkan mapping arti Pending/Processing/Rejected/Completed.                                                      | ISSUE_FOUND              | Dokumentasikan mapping kode status dan gunakan label bermakna pada transformasi/metadata.                                                          |
| Timeliness                        | Ketersediaan elemen waktu dan kemampuan data mendukung pembaruan periodik.                               | orders memiliki order_date/required_date/shipped_date; stocks tidak memiliki tanggal snapshot historis.                                                     | PARTIAL                  | Gunakan order_date untuk periodisasi fakta; jangan membuat histori stok palsu. Scheduler akan ditetapkan setelah ETL stabil.                       |
| Usefulness                        | Relevansi data terhadap kebutuhan analisis yang dipilih.                                                 | orders, order_items, products, brands, categories, stores relevan untuk dua fakta yang dipilih; customers, staffs, stocks tidak diperlukan pada versi awal. | PASS                     | Batasi scope agar pipeline sederhana dan sesuai kebutuhan analitik.                                                                                |
| Adherence to Data Integrity Rules | Entity integrity dan referential integrity.                                                              | 0 NULL/duplicate candidate key dan 0 orphan FK pada relasi yang diperiksa.                                                                                  | PASS                     | Terapkan PK/FK/UNIQUE constraint juga pada DWH.                                                                                                    |

---

## 4. Pembahasan per Aspek

### 4.1 Accuracy

Yang diuji adalah kesalahan yang dapat dideteksi dari dataset itu sendiri, misalnya:

```text
quantity <= 0
harga < 0
stock < 0
shipped_date < order_date
required_date < order_date
```

Hasil:

```text
0 pelanggaran
```

Namun perlu dibedakan:

```text
"tidak ditemukan nilai yang tidak masuk akal"
        ≠
"akurasi dunia nyata sudah terbukti"
```

Contoh, kita tidak bisa membuktikan bahwa nama atau nomor telepon pelanggan benar-benar sesuai dunia nyata hanya dari CSV.

**Keputusan:** tidak ada koreksi otomatis untuk accuracy.

---

### 4.2 Domain Integrity

Domain utama yang diperiksa:

```text
discount       ∈ [0, 1]
quantity       > 0
list_price     >= 0
stock quantity >= 0
order_status   ∈ {1, 2, 3, 4}
```

Tidak ditemukan pelanggaran pada pemeriksaan awal.

**Keputusan:** rule ini tetap diterapkan sebagai validasi pada staging/ETL.

---

### 4.3 Data Type

Tanggal:

```text
order_date
required_date
shipped_date
```

seluruh nilai non-NULL berhasil diparse sebagai tanggal.

Kolom utama seperti:

```text
quantity
list_price
discount
model_year
```

juga terbaca sebagai numeric.

**Keputusan:** walaupun profiling lolos, ETL tetap harus melakukan casting eksplisit.

---

### 4.4 Consistency

Temuan paling jelas:

```text
customers.street
```

memiliki leading/trailing whitespace pada:

```text
1445 record
```

atau seluruh record customer.

Contoh cleansing yang nantinya dilakukan:

```python
customers["street"] = customers["street"].str.strip()
```

Sementara pola `shipped_date` justru konsisten terhadap `order_status`.

**Keputusan:** whitespace dibersihkan; `shipped_date` NULL yang valid dipertahankan.

---

### 4.5 Redundancy

Tidak ditemukan full-row duplicate.

```text
full-row duplicate = 0
```

Tetapi redundancy tidak sama dengan duplication.

Contoh:

```text
products.brand_id
brands.brand_name
```

bukan duplicate yang salah. Itu bagian dari struktur OLTP yang dinormalisasi.

Saat masuk DWH, informasi merek dan kategori memang akan disatukan ke `dim_produk` sebagai denormalisasi terkontrol.

---

### 4.6 Completeness

Temuan:

```text
customers.phone     = 1267 NULL (87.68%)
staffs.manager_id   = 1 NULL
orders.shipped_date = 170 NULL
```

Evaluasi:

```text
customers.phone
└── missing tinggi, tetapi tidak digunakan pada model DWH saat ini

staffs.manager_id
└── NULL dapat valid untuk top-level manager

orders.shipped_date
└── NULL konsisten dengan non-completed order
```

**Keputusan:** tidak ada imputasi nilai palsu.

---

### 4.7 Duplication

Hasil:

```text
full-row duplicate     = 0
duplicate candidate key = 0
```

Composite key yang diperiksa:

```text
order_items
└── order_id + item_id

stocks
└── store_id + product_id
```

**Keputusan:** tidak diperlukan proses deduplication.

---

### 4.8 Conformance to Business Rule

Pemeriksaan utama:

```text
Completed tanpa shipped_date      = 0
Non-completed dengan shipped_date = 0
quantity <= 0                     = 0
discount di luar 0..1             = 0
harga negatif                     = 0
stock negatif                     = 0
```

Ditemukan:

```text
late shipment = 458
```

Late shipment bukan error.

Rule:

```text
shipped_date > required_date
```

merupakan kejadian bisnis yang akan digunakan sebagai measure analitik.

**Keputusan:** pertahankan.

---

### 4.9 Structural Definiteness

Atribut penting sudah terpisah secara jelas.

Contoh:

```text
street
city
state
zip_code
```

tidak disimpan sebagai satu field alamat yang harus dipecah lagi.

Tanggal juga terpisah:

```text
order_date
required_date
shipped_date
```

**Keputusan:** tidak diperlukan structural parsing tambahan untuk scope saat ini.

---

### 4.10 Data Anomaly

Kita mencari indikasi seperti:

```text
nomor telepon dimasukkan ke field alamat
kode status dimasukkan ke nama produk
```

Profiling otomatis tidak menemukan indikasi kuat seperti itu.

Namun pemeriksaan ini memiliki keterbatasan karena sebagian anomaly semantik hanya dapat diketahui melalui business knowledge atau sampling manual.

**Keputusan:** status `PASS_WITH_LIMITATION`.

---

### 4.11 Clarity

`order_status` disimpan sebagai kode:

```text
1
2
3
4
```

Tanpa metadata, angka tersebut ambigu.

Karena itu harus selalu didokumentasikan:

```text
1 = Pending
2 = Processing
3 = Rejected
4 = Completed
```

**Keputusan:** mapping kode menjadi bagian dari metadata dan transformasi.

---

### 4.12 Timeliness

Untuk transaksi, dataset menyediakan:

```text
order_date
required_date
shipped_date
```

sehingga analisis waktu dapat dilakukan.

Tetapi:

```text
stocks.csv
```

tidak mempunyai tanggal snapshot.

Karena itu:

```text
stok historis
```

tidak boleh diciptakan dari data yang tidak tersedia.

**Keputusan:** stok tidak digunakan sebagai fakta historis pada model saat ini.

Scheduler akan dibahas setelah pipeline ETL manual telah valid.

---

### 4.13 Usefulness

Data yang digunakan untuk kebutuhan analitik saat ini:

```text
orders
order_items
products
brands
categories
stores
```

Belum digunakan:

```text
customers
staffs
stocks
```

Ini bukan berarti data tersebut buruk. Data tersebut hanya **tidak diperlukan untuk analytical requirement versi saat ini**.

---

### 4.14 Adherence to Data Integrity Rules

Hasil pemeriksaan:

```text
duplicate candidate key = 0
NULL pada candidate key = 0
orphan foreign key      = 0
```

**Keputusan:** integritas data sumber baik; constraint serupa harus diterapkan pada DWH.

---

## 5. Classification of Findings

```text
┌─────────────────────────────────────────────┐
│                PROFILING FINDING            │
├─────────────────────────────────────────────┤
│ customers.street whitespace                 │
│        └── CLEAN                            │
│                                             │
│ customers.phone NULL                        │
│        └── KEEP                             │
│                                             │
│ orders.shipped_date NULL                    │
│        └── KEEP (valid by business context) │
│                                             │
│ staffs.manager_id NULL                      │
│        └── KEEP                             │
│                                             │
│ late shipment                               │
│        └── KEEP (business event)            │
│                                             │
│ invalid quantity/discount/price/FK          │
│        └── NONE FOUND                       │
└─────────────────────────────────────────────┘
```

---

## 6. Cleansing Decision Register

| Field / Scope        | Temuan                         | Keputusan              | Action | Alasan                                                                                |
| -------------------- | ------------------------------ | ---------------------- | ------ | ------------------------------------------------------------------------------------- |
| customers.street     | Leading/trailing whitespace    | Trim dengan strip()    | CLEAN  | Tidak mengubah makna nilai; standardisasi konsistensi.                                |
| customers.phone      | NULL pada sebagian besar baris | Biarkan NULL           | KEEP   | Tidak dipakai pada model DWH saat ini dan tidak ada sumber terpercaya untuk imputasi. |
| orders.shipped_date  | NULL pada non-completed order  | Biarkan NULL           | KEEP   | Sesuai konteks bisnis; bukan error.                                                   |
| staffs.manager_id    | NULL pada satu baris           | Biarkan NULL           | KEEP   | Dapat merepresentasikan top-level manager.                                            |
| orders               | 458 late shipment              | Pertahankan            | KEEP   | Fenomena bisnis valid, dipakai untuk measure keterlambatan.                           |
| order_items.discount | Valid pada rentang 0..1        | Pertahankan + validasi | KEEP   | Tidak ada pelanggaran domain.                                                         |
| order_items.quantity | Semua > 0                      | Pertahankan + validasi | KEEP   | Tidak ada pelanggaran domain.                                                         |
| FK relationships     | Tidak ada orphan FK            | Pertahankan + validasi | KEEP   | Integritas referensial baik.                                                          |

Evidence machine-readable disimpan dalam:

```text
evidence/data_quality/
├── data_quality_checklist.csv
└── cleansing_decision_register.csv
```

---

## 7. Aturan yang Akan Dibawa ke Tahap Cleansing

Berdasarkan checklist ini, rule awalnya:

```text
RULE 01
Trim leading/trailing whitespace pada string.

RULE 02
Parse tanggal secara eksplisit.

RULE 03
Validasi order_status hanya 1..4.

RULE 04
Validasi discount pada rentang 0..1.

RULE 05
Validasi quantity > 0.

RULE 06
Validasi list_price >= 0.

RULE 07
Validasi stock quantity >= 0.

RULE 08
Jangan imputasi shipped_date yang NULL
jika NULL tersebut sesuai status bisnis.

RULE 09
Jangan menghapus late shipment.

RULE 10
Reject/log record jika foreign key tidak memiliki parent.

RULE 11
Reject/log duplicate candidate key apabila ditemukan
pada run di masa depan.

RULE 12
Pertahankan source raw tanpa modifikasi.
Cleansing dilakukan pada staging copy.
```

---

## 8. Apa yang Akan Terjadi Berikutnya

Tahap berikutnya adalah:

```text
06_data_cleansing.md
```

Pada tahap tersebut kita mulai **benar-benar mengubah data staging**, tetapi tetap menjaga raw source.

Arsitektur:

```text
RAW CSV
  │
  │  immutable
  ▼
STAGING RAW
  │
  ├── validation
  ├── trim
  ├── type casting
  ├── rule checking
  └── logging
  │
  ▼
STAGING CLEAN
```

Untuk setiap cleansing rule kita akan mencatat:

```text
before
rule
after
jumlah record terdampak
hasil validasi
```

---

## 9. Status

**Status:** Data Quality Checklist selesai.

Tahap yang sudah selesai:

```text
✓ 00 Project Overview
✓ 01 Business Process
✓ 02 DWH Design
✓ 03 OLTP → DWH Mapping
✓ 04 Data Profiling
✓ 05 Data Quality Checklist
```

Belum dikerjakan:

```text
○ 06 Data Cleansing
○ 07 ETL Design
○ 08 ETL Implementation
○ 09 Validation & Testing
○ 10 Scheduler & Automation
○ 11 Results & Findings
○ FINAL_REPORT
```
