from pathlib import Path

import pandas as pd

from export_dashboard_data import write_exports


def test_writes_one_file_for_each_dashboard_view(tmp_path: Path) -> None:
    dataframes = {
        "vw_daily_operations": pd.DataFrame({"ride_date": ["2025-01-01"]}),
        "vw_neighborhood_performance": pd.DataFrame({"neighborhood": ["Moema"]}),
        "vw_cancellation_analysis": pd.DataFrame({"cancellation_count": [2]}),
        "vw_driver_quality": pd.DataFrame({"driver_id": ["DRV-00001"]}),
    }

    exported = write_exports(dataframes, tmp_path)

    assert len(exported) == 4
    assert all(path.exists() for path in exported)
    assert set(exported.values()) == {1}
