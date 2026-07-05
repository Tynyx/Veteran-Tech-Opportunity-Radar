from src.vettech_radar.collector import collect_jobs


def main():
    summary = collect_jobs(results_per_page=10)

    print("\nCollection complete.")
    print(f"Records collected: {summary['records_collected']}")
    print(f"Unique records saved: {summary['unique_records_saved']}")
    print(f"Clean run file: {summary['run_file']}")
    print(f"Master file: {summary['master_file']}")

    print("\nRaw files saved:")
    for file_path in summary["raw_files"]:
        print(f"- {file_path}")


if __name__ == "__main__":
    main()