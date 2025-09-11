from intugle.streamlit import StreamlitApp


def export_data():
    """Exports the analysis results to CSV files."""
    app = StreamlitApp()
    app.export_analysis_to_csv()


if __name__ == "__main__":
    export_data()
