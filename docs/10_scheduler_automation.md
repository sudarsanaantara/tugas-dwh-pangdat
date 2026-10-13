# 10 — Scheduler & Automation

## 1. Tujuan

Tahap ini mengubah pipeline yang sebelumnya dijalankan melalui notebook menjadi proses otomatis yang dapat dijalankan oleh scheduler tanpa klik manual.

Pipeline otomatis yang digunakan:

```text
Scheduler
   │
   ▼
run_pipeline.py
   │
   ├── cek / download raw dataset
   ├── staging raw
   ├── pre-cleansing validation
   ├── cleansing
   ├── staging clean
   ├── build dimensions
   ├── build facts
   ├── recreate SQLite DWH
   ├── load DWH
   ├── validation
   └── log
```

---

## 2. Mengapa Notebook Tidak Dijadikan Scheduler

Google Colab digunakan untuk:

```text
development
testing
demonstration
```

Tetapi runtime Colab tidak dijamin terus aktif.

Karena itu proses otomatis dipindahkan ke script Python:

```text
scripts/run_pipeline.py
```

Notebook tetap menjadi evidence proses development, sedangkan script adalah bentuk pipeline yang dapat dipanggil scheduler.

---

## 3. File Otomatisasi

```text
BikeStores_DWH_Automation/
├── README.md
├── requirements.txt
└── scripts/
    ├── run_pipeline.py
    └── scheduler_apscheduler.py
```

### `run_pipeline.py`

Menjalankan seluruh pipeline satu kali.

### `scheduler_apscheduler.py`

Menjalankan `run_pipeline.py` secara periodik melalui APScheduler.

---

## 4. End-to-End Pipeline

```text
┌─────────────────────────────┐
│      Scheduled Trigger      │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ Check data/raw              │
│                             │
│ all files exist?            │
└──────────────┬──────────────┘
               │
       ┌───────┴────────┐
       │                │
      yes              no
       │                │
       │                ▼
       │         Kaggle fallback
       │                │
       └───────┬────────┘
               ▼
┌─────────────────────────────┐
│ Copy → staging/raw          │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Pre-clean validation        │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Cleansing                   │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ staging/clean               │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Dimensions                  │
│ - dim_waktu                 │
│ - dim_toko                  │
│ - dim_produk                │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Facts                       │
│ - penjualan bulanan         │
│ - pengiriman bulanan        │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ SQLite full reload          │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Validation                  │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Log SUCCESS / FAILED        │
└─────────────────────────────┘
```

---

## 5. Strategi Scheduling

Karena kedua fakta menggunakan grain bulanan, schedule default yang digunakan adalah:

```text
Tanggal : 1 setiap bulan
Waktu   : 02:00
```

Alasannya:

```text
1. data bulan sebelumnya telah selesai;
2. proses dijalankan di luar jam bisnis;
3. DWH siap digunakan setelah pipeline selesai.
```

Script juga menyediakan opsi **six-monthly** untuk demonstrasi skenario enam bulanan:

```text
1 Januari
1 Juli
```

---

## 6. Instalasi

Pada komputer yang akan menjadi scheduler host:

```bash
pip install -r requirements.txt
```

Dependensi:

```text
pandas
numpy
kagglehub
APScheduler
```

---

## 7. Test Pipeline Satu Kali

Sebelum mengaktifkan scheduler, pipeline wajib dites secara manual.

Windows:

```bash
python scripts/run_pipeline.py ^
  --project-dir "C:\BikeStores_DWH"
```

Linux/macOS:

```bash
python scripts/run_pipeline.py \
  --project-dir "/home/user/BikeStores_DWH"
```

Expected:

```text
[RAW] PASS
[STAGING] PASS
[VALIDATION] PASS
[CLEANSING] PASS
[ETL] PASS
[SQLITE] PASS
[VALIDATION] PASS
[PIPELINE] SUCCESS
```

---

## 8. APScheduler — Bulanan

```bash
python scripts/scheduler_apscheduler.py \
  --project-dir "/path/to/BikeStores_DWH" \
  --mode monthly \
  --hour 2 \
  --minute 0
```

Rule:

```text
day    = 1
hour   = 2
minute = 0
```

---

## 9. APScheduler — Setiap 6 Bulan

```bash
python scripts/scheduler_apscheduler.py \
  --project-dir "/path/to/BikeStores_DWH" \
  --mode six-monthly \
  --hour 2 \
  --minute 0
```

Rule:

```text
month  = January, July
day    = 1
hour   = 2
minute = 0
```

---

## 10. Logging

Setiap pipeline run membuat:

```text
logs/
└── pipeline_run_<UTC_TIMESTAMP>.json
```

Contoh:

```json
{
  "run_id": "20261014T020000Z",
  "status": "SUCCESS",
  "error": null
}
```

Jika gagal:

```json
{
  "run_id": "20261014T020000Z",
  "status": "FAILED",
  "error": "ValueError: ..."
}
```

Dengan demikian kegagalan tidak hanya terlihat di terminal tetapi juga tersimpan sebagai evidence.

---

## 11. Failure Behavior

Pipeline menggunakan prinsip:

```text
validation gagal
      │
      ▼
STOP
      │
      └── jangan load hasil yang dianggap valid
```

Contoh:

```text
orphan FK ditemukan
        ↓
pipeline FAILED

discount di luar 0..1
        ↓
pipeline FAILED

grain duplicate
        ↓
pipeline FAILED

rekonsiliasi source vs DWH gagal
        ↓
pipeline FAILED
```

---

## 12. Idempotency

Target DWH masih menggunakan strategi **full reload**.

```text
Scheduled Run #1
      │
      ▼
DWH State A

Scheduled Run #2
      │
      ▼
DWH State A
```

Tidak terjadi append berulang karena schema SQLite dibangun ulang sebelum load.

Ini sesuai dengan kebutuhan testing proyek saat ini.

---

## 13. APScheduler vs OS Scheduler

### APScheduler

Kelebihan:

```text
✓ mudah didemokan
✓ schedule terlihat di Python
✓ mudah mengganti monthly / six-monthly
```

Keterbatasan:

```text
△ proses Python harus tetap hidup
```

### Windows Task Scheduler / cron

Lebih cocok untuk deployment karena sistem operasi dapat memanggil:

```text
run_pipeline.py
```

secara otomatis tanpa menjalankan `scheduler_apscheduler.py` terus-menerus.

Untuk laporan proyek, APScheduler digunakan sebagai implementasi scheduler yang mudah didemokan. `run_pipeline.py` tetap dapat dipakai oleh OS scheduler bila diperlukan.

---

## 14. Evidence yang Perlu Disimpan

Untuk demo scheduler:

```text
1. screenshot scheduler aktif;
2. output terminal saat scheduled run;
3. pipeline_run_*.json;
4. bikestores_dwh.db setelah run;
5. scheduled_validation_results.csv.
```

Evidence tersebut membuktikan:

```text
scheduler trigger
      ↓
pipeline berjalan
      ↓
DWH diperbarui
      ↓
validation PASS
      ↓
log SUCCESS
```

---

## 15. Kriteria Lulus

Tahap scheduler dinyatakan selesai jika:

```text
✓ run_pipeline.py berhasil dijalankan manual
✓ pipeline dapat berjalan tanpa notebook
✓ scheduler berhasil memicu pipeline
✓ database dihasilkan / diperbarui
✓ validation tetap PASS
✓ log SUCCESS dibuat
```

---

## 16. Status

**Status saat ini:** Script otomatisasi dan scheduler telah disiapkan.

Tahap dianggap final setelah dilakukan satu pengujian scheduler pada environment host.

Setelah itu proyek dapat lanjut ke:

```text
11 — Results & Findings
FINAL REPORT
```
