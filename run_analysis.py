from src.vettech_radar.analyze import save_summary_tables
from src.vettech_radar.visualize import create_all_charts


def main():
    print("Starting VetTech Opportunity Radar analysis...")

    summary_files = save_summary_tables()

    print("\nSummary tables created:")
    for file_path in summary_files:
        print(f"- {file_path}")

    chart_files = create_all_charts()

    print("\nCharts created:")
    for file_path in chart_files:
        print(f"- {file_path}")

    print("\nAnalysis complete.")


if __name__ == "__main__":
    main()