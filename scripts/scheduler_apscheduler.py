from pathlib import Path
import argparse
import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from run_pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="BikeStores DWH APScheduler runner."
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        required=True,
        help="Root folder proyek BikeStores_DWH.",
    )
    parser.add_argument(
        "--mode",
        choices=["monthly", "six-monthly"],
        default="monthly",
        help="Frekuensi scheduler.",
    )
    parser.add_argument(
        "--hour",
        type=int,
        default=2,
        help="Jam eksekusi (0-23). Default 02:00.",
    )
    parser.add_argument(
        "--minute",
        type=int,
        default=0,
        help="Menit eksekusi. Default 00.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    project_dir = args.project_dir.resolve()

    scheduler = BlockingScheduler()

    if args.mode == "monthly":
        # Tanggal 1 setiap bulan pukul HH:MM.
        trigger = CronTrigger(
            day=1,
            hour=args.hour,
            minute=args.minute,
        )
        label = "tanggal 1 setiap bulan"
    else:
        # 1 Januari dan 1 Juli setiap tahun.
        trigger = CronTrigger(
            month="1,7",
            day=1,
            hour=args.hour,
            minute=args.minute,
        )
        label = "1 Januari dan 1 Juli"

    scheduler.add_job(
        lambda: run_pipeline(project_dir),
        trigger=trigger,
        id="bikestores_dwh_pipeline",
        name="BikeStores DWH Pipeline",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )

    print(
        f"Scheduler aktif: {label} pukul "
        f"{args.hour:02d}:{args.minute:02d}."
    )
    print("Tekan Ctrl+C untuk menghentikan scheduler.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler dihentikan.")


if __name__ == "__main__":
    main()
