# BikeStores Data Warehouse Project

Proyek ini merupakan implementasi mini Data Warehouse berbasis dataset **Bike Store Sample Database** dari Kaggle.

Fokus proyek:

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
SQLite Data Warehouse
     │
     ▼
Validation & Testing
     │
     ▼
Scheduler & Automation
```

## Struktur Repository

```text
BikeStores_DWH_GitHub/
├── README.md
├── requirements.txt
├── docs/
│   ├── README.md
│   ├── 00_project_overview.md
│   ├── 01_business_process.md
│   ├── 02_dwh_design.md
│   ├── 03_oltp_to_dwh_mapping.md
│   ├── 04_data_profiling.md
│   ├── 05_data_quality_checklist.md
│   ├── 06_data_cleansing.md
│   ├── 07_etl_design.md
│   ├── 08_etl_implementation.md
│   ├── 09_validation_testing.md
│   └── 10_scheduler_automation.md
├── notebooks/
│   ├── BikeStores_DWH_01_Staging_Cleansing_v2.ipynb
│   ├── BikeStores_DWH_02_ETL_SQLite.ipynb
│   └── BikeStores_DWH_03_Validation_Testing.ipynb
└── scripts/
    ├── run_pipeline.py
    └── scheduler_apscheduler.py
```

## DWH yang Digunakan

Dimension table:

```text
dim_waktu
dim_toko
dim_produk
```

Fact table:

```text
fakta_penjualan_bulanan
fakta_pengiriman_bulanan
```

## Grain

```text
fakta_penjualan_bulanan
= bulan × toko × produk
```

```text
fakta_pengiriman_bulanan
= bulan × toko
```

## Notebook

### 1. Staging & Cleansing

```text
notebooks/BikeStores_DWH_01_Staging_Cleansing_v2.ipynb
```

Digunakan untuk:

- mengambil raw dataset;
- Kaggle fallback bila file belum tersedia;
- staging;
- validation;
- cleansing;
- menghasilkan staging clean.

### 2. ETL SQLite

```text
notebooks/BikeStores_DWH_02_ETL_SQLite.ipynb
```

Digunakan untuk:

- membangun dimensions;
- membangun facts;
- membuat schema SQLite;
- load DWH;
- validasi hasil ETL.

### 3. Validation & Testing

```text
notebooks/BikeStores_DWH_03_Validation_Testing.ipynb
```

Digunakan untuk:

- structural validation;
- row-count validation;
- foreign-key validation;
- grain validation;
- sales reconciliation;
- shipping reconciliation;
- status reconciliation;
- analytic query sanity test;
- idempotency test.

Pada pengujian proyek, notebook validation menghasilkan **22 PASS**.

## Automation

Pipeline end-to-end tersedia pada:

```text
scripts/run_pipeline.py
```

Scheduler berbasis APScheduler:

```text
scripts/scheduler_apscheduler.py
```

Contoh scheduler bulanan:

```bash
python scripts/scheduler_apscheduler.py   --project-dir "/path/to/BikeStores_DWH"   --mode monthly   --hour 2   --minute 0
```

Scheduler disertakan untuk memenuhi kebutuhan otomatisasi pipeline. Pengujian scheduler host tidak menjadi prasyarat untuk membaca atau meninjau implementasi repository ini.

## Catatan

Google Colab digunakan sebagai environment development/testing notebook.

SQLite digunakan sebagai target Data Warehouse karena proyek berfokus pada demonstrasi proses ETL, validasi, dan otomatisasi dalam skala akademik.
