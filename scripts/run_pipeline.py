from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import shutil
import sqlite3
import sys

import numpy as np
import pandas as pd


EXPECTED_FILES = [
    "brands.csv",
    "categories.csv",
    "customers.csv",
    "order_items.csv",
    "orders.csv",
    "products.csv",
    "staffs.csv",
    "stocks.csv",
    "stores.csv",
]

KAGGLE_DATASET = "dillonmyrick/bike-store-sample-database"


def utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def ensure_dirs(project_dir: Path) -> dict[str, Path]:
    paths = {
        "raw": project_dir / "data" / "raw",
        "staging_raw": project_dir / "data" / "staging" / "raw",
        "staging_clean": project_dir / "data" / "staging" / "clean",
        "evidence_cleansing": project_dir / "data" / "evidence" / "cleansing",
        "evidence_etl": project_dir / "data" / "evidence" / "etl",
        "evidence_validation": project_dir / "data" / "evidence" / "validation",
        "database": project_dir / "database",
        "logs": project_dir / "logs",
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths


def ensure_raw_data(raw_dir: Path, allow_kaggle_download: bool = True) -> None:
    missing = [f for f in EXPECTED_FILES if not (raw_dir / f).exists()]
    if not missing:
        print("[RAW] PASS: seluruh 9 file tersedia.")
        return

    if not allow_kaggle_download:
        raise FileNotFoundError(
            "Raw dataset tidak lengkap: " + ", ".join(missing)
        )

    print("[RAW] Dataset belum lengkap. Mencoba Kaggle fallback...")
    try:
        import kagglehub
    except ImportError as exc:
        raise RuntimeError(
            "kagglehub belum terpasang. Jalankan: pip install kagglehub"
        ) from exc

    kaggle_path = Path(kagglehub.dataset_download(KAGGLE_DATASET))
    downloaded = {p.name: p for p in kaggle_path.rglob("*.csv")}

    for filename in missing:
        src = downloaded.get(filename)
        if src is not None:
            shutil.copy2(src, raw_dir / filename)
            print(f"[RAW] Downloaded: {filename}")

    missing_after = [f for f in EXPECTED_FILES if not (raw_dir / f).exists()]
    if missing_after:
        raise FileNotFoundError(
            "Dataset masih belum lengkap setelah Kaggle fallback: "
            + ", ".join(missing_after)
        )

    print("[RAW] PASS: Kaggle fallback berhasil.")


def copy_to_staging_raw(raw_dir: Path, staging_raw_dir: Path) -> None:
    for filename in EXPECTED_FILES:
        shutil.copy2(raw_dir / filename, staging_raw_dir / filename)
    print("[STAGING] PASS: raw source disalin ke staging/raw.")


def load_all_csv(directory: Path) -> dict[str, pd.DataFrame]:
    return {
        filename: pd.read_csv(directory / filename)
        for filename in EXPECTED_FILES
    }


def preclean_validation(dfs: dict[str, pd.DataFrame]) -> None:
    pk_specs = {
        "brands.csv": ["brand_id"],
        "categories.csv": ["category_id"],
        "customers.csv": ["customer_id"],
        "orders.csv": ["order_id"],
        "order_items.csv": ["order_id", "item_id"],
        "products.csv": ["product_id"],
        "staffs.csv": ["staff_id"],
        "stocks.csv": ["store_id", "product_id"],
        "stores.csv": ["store_id"],
    }

    for filename, cols in pk_specs.items():
        df = dfs[filename]
        if df[cols].isna().any(axis=1).any():
            raise ValueError(f"NULL pada candidate key: {filename} {cols}")
        if df.duplicated(subset=cols).any():
            raise ValueError(f"Duplicate candidate key: {filename} {cols}")

    fk_specs = [
        ("products.csv", "brand_id", "brands.csv", "brand_id"),
        ("products.csv", "category_id", "categories.csv", "category_id"),
        ("orders.csv", "customer_id", "customers.csv", "customer_id"),
        ("orders.csv", "store_id", "stores.csv", "store_id"),
        ("orders.csv", "staff_id", "staffs.csv", "staff_id"),
        ("order_items.csv", "order_id", "orders.csv", "order_id"),
        ("order_items.csv", "product_id", "products.csv", "product_id"),
        ("staffs.csv", "store_id", "stores.csv", "store_id"),
        ("staffs.csv", "manager_id", "staffs.csv", "staff_id"),
        ("stocks.csv", "store_id", "stores.csv", "store_id"),
        ("stocks.csv", "product_id", "products.csv", "product_id"),
    ]

    for cf, cc, pf, pc in fk_specs:
        child = dfs[cf]
        parents = set(dfs[pf][pc].dropna())
        invalid = child[cc].notna() & ~child[cc].isin(parents)
        if invalid.any():
            raise ValueError(f"Orphan FK: {cf}.{cc} -> {pf}.{pc}")

    oi = dfs["order_items.csv"]
    products = dfs["products.csv"]
    stocks = dfs["stocks.csv"]

    if (oi["quantity"] <= 0).any():
        raise ValueError("quantity <= 0 ditemukan.")
    if ((oi["discount"] < 0) | (oi["discount"] > 1)).any():
        raise ValueError("discount di luar 0..1 ditemukan.")
    if (oi["list_price"] < 0).any() or (products["list_price"] < 0).any():
        raise ValueError("list_price negatif ditemukan.")
    if (stocks["quantity"] < 0).any():
        raise ValueError("stock negatif ditemukan.")

    print("[VALIDATION] PASS: pre-cleansing validation.")


def cleanse(
    dfs: dict[str, pd.DataFrame],
    staging_clean_dir: Path,
    evidence_dir: Path,
) -> dict[str, pd.DataFrame]:
    clean = {k: v.copy(deep=True) for k, v in dfs.items()}
    log_rows = []

    before_summary = []
    for filename, df in clean.items():
        before_summary.append({
            "file": filename,
            "rows": len(df),
            "columns": len(df.columns),
            "full_row_duplicates": int(df.duplicated().sum()),
            "total_null_values": int(df.isna().sum().sum()),
        })

    for filename, df in clean.items():
        for col in df.select_dtypes(include="object").columns:
            mask = df[col].notna()
            before = df.loc[mask, col].astype(str)
            after = before.str.strip()
            affected = int((before != after).sum())
            df.loc[mask, col] = after

            if affected:
                log_rows.append({
                    "file": filename,
                    "column": col,
                    "rule": "TRIM_WHITESPACE",
                    "rows_affected": affected,
                    "action": "CLEAN",
                })

    orders = clean["orders.csv"]
    for col in ["order_date", "required_date", "shipped_date"]:
        source_non_null = orders[col].notna()
        parsed = pd.to_datetime(orders[col], errors="coerce")
        failures = int((source_non_null & parsed.isna()).sum())
        if failures:
            raise ValueError(f"Gagal parse {failures} nilai pada {col}")
        orders[col] = parsed
        log_rows.append({
            "file": "orders.csv",
            "column": col,
            "rule": "PARSE_DATE",
            "rows_affected": int(source_non_null.sum()),
            "action": "STANDARDIZE_TYPE",
        })

    after_summary = []
    for filename, df in clean.items():
        after_summary.append({
            "file": filename,
            "rows": len(df),
            "columns": len(df.columns),
            "full_row_duplicates": int(df.duplicated().sum()),
            "total_null_values": int(df.isna().sum().sum()),
        })

    before_df = pd.DataFrame(before_summary)
    after_df = pd.DataFrame(after_summary)

    if not (before_df["rows"].to_numpy() == after_df["rows"].to_numpy()).all():
        raise ValueError("Row count berubah saat cleansing.")

    # Ensure no outer whitespace remains.
    for filename, df in clean.items():
        for col in df.select_dtypes(include="object").columns:
            s = df[col].dropna().astype(str)
            if (s != s.str.strip()).any():
                raise ValueError(f"Whitespace masih tersisa: {filename}.{col}")

    for filename, df in clean.items():
        out = df.copy()
        if filename == "orders.csv":
            for col in ["order_date", "required_date", "shipped_date"]:
                out[col] = out[col].dt.strftime("%Y-%m-%d")
        out.to_csv(staging_clean_dir / filename, index=False)

    before_df.to_csv(evidence_dir / "before_summary.csv", index=False)
    after_df.to_csv(evidence_dir / "after_summary.csv", index=False)
    pd.DataFrame(log_rows).to_csv(
        evidence_dir / "cleansing_log.csv", index=False
    )

    print("[CLEANSING] PASS: staging clean dan evidence dibuat.")
    return clean


def build_dimensions(clean: dict[str, pd.DataFrame]):
    orders = clean["orders.csv"].copy()
    stores = clean["stores.csv"].copy()
    products = clean["products.csv"].copy()
    brands = clean["brands.csv"].copy()
    categories = clean["categories.csv"].copy()

    dim_waktu = (
        orders[["order_date"]]
        .dropna()
        .assign(
            id_waktu=lambda x:
                x["order_date"].dt.year * 100 + x["order_date"].dt.month,
            tahun=lambda x: x["order_date"].dt.year,
            bulan=lambda x: x["order_date"].dt.month,
            nama_bulan=lambda x: x["order_date"].dt.month_name(),
            kuartal=lambda x: "Q" + x["order_date"].dt.quarter.astype(str),
        )
        [["id_waktu", "tahun", "bulan", "nama_bulan", "kuartal"]]
        .drop_duplicates()
        .sort_values("id_waktu")
        .reset_index(drop=True)
    )

    dim_toko = (
        stores.sort_values("store_id")
        .reset_index(drop=True)
        .rename(columns={
            "store_id": "id_toko_oltp",
            "store_name": "nama_toko",
            "street": "alamat",
            "city": "kota",
            "zip_code": "kode_pos",
            "phone": "telepon",
        })
    )
    dim_toko.insert(0, "id_toko", np.arange(1, len(dim_toko) + 1))
    dim_toko = dim_toko[
        [
            "id_toko", "id_toko_oltp", "nama_toko", "alamat",
            "kota", "state", "kode_pos", "telepon", "email",
        ]
    ]

    dim_produk = (
        products
        .merge(
            brands[["brand_id", "brand_name"]],
            on="brand_id",
            how="left",
            validate="many_to_one",
        )
        .merge(
            categories[["category_id", "category_name"]],
            on="category_id",
            how="left",
            validate="many_to_one",
        )
        .sort_values("product_id")
        .reset_index(drop=True)
        .rename(columns={
            "product_id": "id_produk_oltp",
            "product_name": "nama_produk",
            "brand_name": "merek",
            "category_name": "kategori",
            "model_year": "tahun_model",
            "list_price": "harga_list",
        })
    )
    dim_produk.insert(0, "id_produk", np.arange(1, len(dim_produk) + 1))
    dim_produk = dim_produk[
        [
            "id_produk", "id_produk_oltp", "nama_produk",
            "merek", "kategori", "tahun_model", "harga_list",
        ]
    ]

    if not dim_waktu["id_waktu"].is_unique:
        raise ValueError("dim_waktu id_waktu tidak unik.")
    if not dim_toko["id_toko"].is_unique or not dim_toko["id_toko_oltp"].is_unique:
        raise ValueError("dim_toko key tidak unik.")
    if not dim_produk["id_produk"].is_unique or not dim_produk["id_produk_oltp"].is_unique:
        raise ValueError("dim_produk key tidak unik.")
    if len(dim_toko) != len(stores):
        raise ValueError("Row count dim_toko tidak sama dengan stores.")
    if len(dim_produk) != len(products):
        raise ValueError("Row count dim_produk tidak sama dengan products.")
    if dim_produk[["merek", "kategori"]].isna().any().any():
        raise ValueError("Join dim_produk menghasilkan NULL.")

    print("[ETL] PASS: dimensions built.")
    return dim_waktu, dim_toko, dim_produk


def build_facts(
    clean: dict[str, pd.DataFrame],
    dim_toko: pd.DataFrame,
    dim_produk: pd.DataFrame,
):
    orders = clean["orders.csv"].copy()
    order_items = clean["order_items.csv"].copy()

    sales_detail = (
        orders.loc[orders["order_status"] == 4]
        .merge(order_items, on="order_id", how="inner", validate="one_to_many")
    )
    sales_detail["id_waktu"] = (
        sales_detail["order_date"].dt.year * 100
        + sales_detail["order_date"].dt.month
    )
    sales_detail = (
        sales_detail
        .merge(
            dim_toko[["id_toko", "id_toko_oltp"]],
            left_on="store_id",
            right_on="id_toko_oltp",
            how="left",
            validate="many_to_one",
        )
        .merge(
            dim_produk[["id_produk", "id_produk_oltp"]],
            left_on="product_id",
            right_on="id_produk_oltp",
            how="left",
            validate="many_to_one",
        )
    )
    if sales_detail[["id_toko", "id_produk"]].isna().any().any():
        raise ValueError("Lookup dimension key gagal pada sales detail.")

    sales_detail["gross_value"] = (
        sales_detail["quantity"] * sales_detail["list_price"]
    )
    sales_detail["discount_value"] = (
        sales_detail["gross_value"] * sales_detail["discount"]
    )
    sales_detail["net_value"] = (
        sales_detail["gross_value"] - sales_detail["discount_value"]
    )

    fact_sales = (
        sales_detail
        .groupby(["id_waktu", "id_toko", "id_produk"], as_index=False)
        .agg(
            jumlah_order=("order_id", "nunique"),
            total_qty=("quantity", "sum"),
            total_penjualan_kotor=("gross_value", "sum"),
            total_diskon=("discount_value", "sum"),
            total_penjualan_bersih=("net_value", "sum"),
        )
        .sort_values(["id_waktu", "id_toko", "id_produk"])
        .reset_index(drop=True)
    )
    money_cols = [
        "total_penjualan_kotor",
        "total_diskon",
        "total_penjualan_bersih",
    ]
    fact_sales[money_cols] = fact_sales[money_cols].round(4)
    fact_sales.insert(
        0, "id_fakta_penjualan", np.arange(1, len(fact_sales) + 1)
    )

    shipping = orders.copy()
    shipping["id_waktu"] = (
        shipping["order_date"].dt.year * 100 + shipping["order_date"].dt.month
    )
    shipping = shipping.merge(
        dim_toko[["id_toko", "id_toko_oltp"]],
        left_on="store_id",
        right_on="id_toko_oltp",
        how="left",
        validate="many_to_one",
    )
    if shipping["id_toko"].isna().any():
        raise ValueError("Lookup id_toko gagal pada shipping detail.")

    shipping["flag_pending"] = (shipping["order_status"] == 1).astype(int)
    shipping["flag_diproses"] = (shipping["order_status"] == 2).astype(int)
    shipping["flag_ditolak"] = (shipping["order_status"] == 3).astype(int)
    shipping["flag_selesai"] = (shipping["order_status"] == 4).astype(int)
    shipping["flag_terlambat"] = (
        shipping["shipped_date"].notna()
        & (shipping["shipped_date"] > shipping["required_date"])
    ).astype(int)
    shipping["hari_proses"] = (
        shipping["shipped_date"] - shipping["order_date"]
    ).dt.days

    fact_shipping = (
        shipping
        .groupby(["id_waktu", "id_toko"], as_index=False)
        .agg(
            jumlah_order=("order_id", "count"),
            jumlah_order_pending=("flag_pending", "sum"),
            jumlah_order_diproses=("flag_diproses", "sum"),
            jumlah_order_ditolak=("flag_ditolak", "sum"),
            jumlah_order_selesai=("flag_selesai", "sum"),
            jumlah_order_terlambat=("flag_terlambat", "sum"),
            rata_rata_hari_proses=("hari_proses", "mean"),
        )
        .sort_values(["id_waktu", "id_toko"])
        .reset_index(drop=True)
    )
    fact_shipping["rata_rata_hari_proses"] = (
        fact_shipping["rata_rata_hari_proses"].round(4)
    )
    fact_shipping.insert(
        0, "id_fakta_pengiriman", np.arange(1, len(fact_shipping) + 1)
    )

    if fact_sales.duplicated(
        subset=["id_waktu", "id_toko", "id_produk"]
    ).any():
        raise ValueError("Duplicate grain fakta_penjualan.")
    if fact_shipping.duplicated(
        subset=["id_waktu", "id_toko"]
    ).any():
        raise ValueError("Duplicate grain fakta_pengiriman.")

    status_total = (
        fact_shipping["jumlah_order_pending"]
        + fact_shipping["jumlah_order_diproses"]
        + fact_shipping["jumlah_order_ditolak"]
        + fact_shipping["jumlah_order_selesai"]
    )
    if not (fact_shipping["jumlah_order"] == status_total).all():
        raise ValueError("Status reconciliation gagal.")

    if not np.allclose(
        fact_sales["total_penjualan_kotor"]
        - fact_sales["total_diskon"],
        fact_sales["total_penjualan_bersih"],
        atol=1e-3,
    ):
        raise ValueError("Sales reconciliation internal gagal.")

    print("[ETL] PASS: facts built.")
    return fact_sales, fact_shipping


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS fakta_pengiriman_bulanan;
DROP TABLE IF EXISTS fakta_penjualan_bulanan;
DROP TABLE IF EXISTS dim_produk;
DROP TABLE IF EXISTS dim_toko;
DROP TABLE IF EXISTS dim_waktu;

CREATE TABLE dim_waktu (
    id_waktu INTEGER PRIMARY KEY,
    tahun INTEGER NOT NULL,
    bulan INTEGER NOT NULL CHECK (bulan BETWEEN 1 AND 12),
    nama_bulan TEXT NOT NULL,
    kuartal TEXT NOT NULL CHECK (kuartal IN ('Q1','Q2','Q3','Q4')),
    UNIQUE (tahun, bulan)
);

CREATE TABLE dim_toko (
    id_toko INTEGER PRIMARY KEY,
    id_toko_oltp INTEGER NOT NULL UNIQUE,
    nama_toko TEXT NOT NULL,
    alamat TEXT,
    kota TEXT,
    state TEXT,
    kode_pos TEXT,
    telepon TEXT,
    email TEXT
);

CREATE TABLE dim_produk (
    id_produk INTEGER PRIMARY KEY,
    id_produk_oltp INTEGER NOT NULL UNIQUE,
    nama_produk TEXT NOT NULL,
    merek TEXT NOT NULL,
    kategori TEXT NOT NULL,
    tahun_model INTEGER,
    harga_list REAL NOT NULL CHECK (harga_list >= 0)
);

CREATE TABLE fakta_penjualan_bulanan (
    id_fakta_penjualan INTEGER PRIMARY KEY,
    id_waktu INTEGER NOT NULL,
    id_toko INTEGER NOT NULL,
    id_produk INTEGER NOT NULL,
    jumlah_order INTEGER NOT NULL CHECK (jumlah_order >= 0),
    total_qty INTEGER NOT NULL CHECK (total_qty >= 0),
    total_penjualan_kotor REAL NOT NULL CHECK (total_penjualan_kotor >= 0),
    total_diskon REAL NOT NULL CHECK (total_diskon >= 0),
    total_penjualan_bersih REAL NOT NULL CHECK (total_penjualan_bersih >= 0),
    FOREIGN KEY (id_waktu) REFERENCES dim_waktu(id_waktu),
    FOREIGN KEY (id_toko) REFERENCES dim_toko(id_toko),
    FOREIGN KEY (id_produk) REFERENCES dim_produk(id_produk),
    UNIQUE (id_waktu, id_toko, id_produk)
);

CREATE TABLE fakta_pengiriman_bulanan (
    id_fakta_pengiriman INTEGER PRIMARY KEY,
    id_waktu INTEGER NOT NULL,
    id_toko INTEGER NOT NULL,
    jumlah_order INTEGER NOT NULL CHECK (jumlah_order >= 0),
    jumlah_order_pending INTEGER NOT NULL CHECK (jumlah_order_pending >= 0),
    jumlah_order_diproses INTEGER NOT NULL CHECK (jumlah_order_diproses >= 0),
    jumlah_order_ditolak INTEGER NOT NULL CHECK (jumlah_order_ditolak >= 0),
    jumlah_order_selesai INTEGER NOT NULL CHECK (jumlah_order_selesai >= 0),
    jumlah_order_terlambat INTEGER NOT NULL CHECK (jumlah_order_terlambat >= 0),
    rata_rata_hari_proses REAL,
    FOREIGN KEY (id_waktu) REFERENCES dim_waktu(id_waktu),
    FOREIGN KEY (id_toko) REFERENCES dim_toko(id_toko),
    UNIQUE (id_waktu, id_toko),
    CHECK (
        jumlah_order =
        jumlah_order_pending +
        jumlah_order_diproses +
        jumlah_order_ditolak +
        jumlah_order_selesai
    )
);
"""


def load_sqlite(
    db_path: Path,
    dim_waktu: pd.DataFrame,
    dim_toko: pd.DataFrame,
    dim_produk: pd.DataFrame,
    fact_sales: pd.DataFrame,
    fact_shipping: pd.DataFrame,
) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.executescript(SCHEMA_SQL)

        dim_waktu.to_sql("dim_waktu", conn, if_exists="append", index=False)
        dim_toko.to_sql("dim_toko", conn, if_exists="append", index=False)
        dim_produk.to_sql("dim_produk", conn, if_exists="append", index=False)
        fact_sales.to_sql(
            "fakta_penjualan_bulanan", conn, if_exists="append", index=False
        )
        fact_shipping.to_sql(
            "fakta_pengiriman_bulanan", conn, if_exists="append", index=False
        )
        conn.commit()

        fk_errors = conn.execute("PRAGMA foreign_key_check;").fetchall()
        if fk_errors:
            raise ValueError(f"Foreign key errors: {fk_errors}")

        print("[SQLITE] PASS: DWH loaded dan FK valid.")
    finally:
        conn.close()


def validate_dwh(
    db_path: Path,
    clean: dict[str, pd.DataFrame],
    evidence_dir: Path,
) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        results = []

        def rec(name, passed, expected=None, actual=None):
            results.append({
                "test": name,
                "status": "PASS" if passed else "FAIL",
                "expected": expected,
                "actual": actual,
            })

        expected_tables = {
            "dim_waktu", "dim_toko", "dim_produk",
            "fakta_penjualan_bulanan", "fakta_pengiriman_bulanan",
        }
        actual_tables = {
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table';"
            ).fetchall()
        }
        rec(
            "tables_exist",
            expected_tables.issubset(actual_tables),
            sorted(expected_tables),
            sorted(actual_tables),
        )

        fk_errors = conn.execute("PRAGMA foreign_key_check;").fetchall()
        rec("foreign_key_check", len(fk_errors) == 0, 0, len(fk_errors))

        sales_grain = conn.execute("""
            SELECT COUNT(*) FROM (
                SELECT id_waktu, id_toko, id_produk, COUNT(*) c
                FROM fakta_penjualan_bulanan
                GROUP BY id_waktu, id_toko, id_produk
                HAVING c > 1
            );
        """).fetchone()[0]
        rec("sales_grain_unique", sales_grain == 0, 0, sales_grain)

        shipping_grain = conn.execute("""
            SELECT COUNT(*) FROM (
                SELECT id_waktu, id_toko, COUNT(*) c
                FROM fakta_pengiriman_bulanan
                GROUP BY id_waktu, id_toko
                HAVING c > 1
            );
        """).fetchone()[0]
        rec("shipping_grain_unique", shipping_grain == 0, 0, shipping_grain)

        orders = clean["orders.csv"]
        order_items = clean["order_items.csv"]

        completed = orders.loc[
            orders["order_status"] == 4, ["order_id"]
        ].merge(
            order_items,
            on="order_id",
            how="inner",
            validate="one_to_many",
        )
        completed["gross"] = (
            completed["quantity"] * completed["list_price"]
        )
        completed["discount_value"] = (
            completed["gross"] * completed["discount"]
        )
        completed["net"] = (
            completed["gross"] - completed["discount_value"]
        )

        src_gross = float(completed["gross"].sum())
        src_discount = float(completed["discount_value"].sum())
        src_net = float(completed["net"].sum())

        dwh_gross, dwh_discount, dwh_net = conn.execute("""
            SELECT
                SUM(total_penjualan_kotor),
                SUM(total_diskon),
                SUM(total_penjualan_bersih)
            FROM fakta_penjualan_bulanan;
        """).fetchone()

        rec(
            "gross_reconciliation",
            np.isclose(src_gross, dwh_gross, atol=0.01),
            round(src_gross, 2),
            round(dwh_gross, 2),
        )
        rec(
            "discount_reconciliation",
            np.isclose(src_discount, dwh_discount, atol=0.01),
            round(src_discount, 2),
            round(dwh_discount, 2),
        )
        rec(
            "net_reconciliation",
            np.isclose(src_net, dwh_net, atol=0.01),
            round(src_net, 2),
            round(dwh_net, 2),
        )

        src_orders = len(orders)
        dwh_orders = conn.execute(
            "SELECT SUM(jumlah_order) FROM fakta_pengiriman_bulanan;"
        ).fetchone()[0]
        rec("order_reconciliation", src_orders == dwh_orders, src_orders, dwh_orders)

        src_late = int(
            (
                orders["shipped_date"].notna()
                & (orders["shipped_date"] > orders["required_date"])
            ).sum()
        )
        dwh_late = conn.execute(
            "SELECT SUM(jumlah_order_terlambat) "
            "FROM fakta_pengiriman_bulanan;"
        ).fetchone()[0]
        rec("late_reconciliation", src_late == dwh_late, src_late, dwh_late)

        results_df = pd.DataFrame(results)
        results_df.to_csv(
            evidence_dir / "scheduled_validation_results.csv", index=False
        )

        if (results_df["status"] == "FAIL").any():
            raise ValueError(
                "Validation gagal: "
                + ", ".join(
                    results_df.loc[
                        results_df["status"] == "FAIL", "test"
                    ].tolist()
                )
            )

        print("[VALIDATION] PASS: seluruh scheduled validation berhasil.")
        return results_df
    finally:
        conn.close()


def run_pipeline(
    project_dir: Path,
    allow_kaggle_download: bool = True,
) -> None:
    run_id = utc_run_id()
    paths = ensure_dirs(project_dir)
    log_path = paths["logs"] / f"pipeline_run_{run_id}.json"

    log = {
        "run_id": run_id,
        "start_time_utc": datetime.now(timezone.utc).isoformat(),
        "project_dir": str(project_dir),
        "status": "RUNNING",
        "error": None,
    }

    try:
        ensure_raw_data(
            paths["raw"],
            allow_kaggle_download=allow_kaggle_download,
        )
        copy_to_staging_raw(paths["raw"], paths["staging_raw"])

        dfs = load_all_csv(paths["staging_raw"])
        preclean_validation(dfs)

        clean = cleanse(
            dfs,
            paths["staging_clean"],
            paths["evidence_cleansing"],
        )

        dim_waktu, dim_toko, dim_produk = build_dimensions(clean)
        fact_sales, fact_shipping = build_facts(
            clean, dim_toko, dim_produk
        )

        db_path = paths["database"] / "bikestores_dwh.db"
        load_sqlite(
            db_path,
            dim_waktu,
            dim_toko,
            dim_produk,
            fact_sales,
            fact_shipping,
        )

        validation = validate_dwh(
            db_path,
            clean,
            paths["evidence_validation"],
        )

        pd.DataFrame([
            {"table": "dim_waktu", "rows": len(dim_waktu)},
            {"table": "dim_toko", "rows": len(dim_toko)},
            {"table": "dim_produk", "rows": len(dim_produk)},
            {"table": "fakta_penjualan_bulanan", "rows": len(fact_sales)},
            {"table": "fakta_pengiriman_bulanan", "rows": len(fact_shipping)},
        ]).to_csv(
            paths["evidence_etl"] / "scheduled_etl_output_summary.csv",
            index=False,
        )

        log["status"] = "SUCCESS"
        log["validation_pass"] = int(
            (validation["status"] == "PASS").sum()
        )
        print("[PIPELINE] SUCCESS")

    except Exception as exc:
        log["status"] = "FAILED"
        log["error"] = f"{type(exc).__name__}: {exc}"
        print("[PIPELINE] FAILED:", log["error"], file=sys.stderr)
        raise

    finally:
        log["end_time_utc"] = datetime.now(timezone.utc).isoformat()
        log_path.write_text(
            json.dumps(log, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print("[LOG]", log_path)


def parse_args():
    parser = argparse.ArgumentParser(
        description="BikeStores DWH end-to-end pipeline."
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        required=True,
        help="Root project directory, e.g. C:/BikeStores_DWH",
    )
    parser.add_argument(
        "--no-kaggle-download",
        action="store_true",
        help="Fail instead of downloading missing raw CSV from Kaggle.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(
        args.project_dir.resolve(),
        allow_kaggle_download=not args.no_kaggle_download,
    )
