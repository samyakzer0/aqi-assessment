import pandas as pd

# 1. Define the multi-format testing matrix
data = {
    'city': ['Singapore', 'Dubai', 'Seoul'],
    'aqi': [40, 110, 65],
    'pm25': [9.5, 38.0, 18.2],
    'raw_timestamp': ['2026-06-30 13:00:00', '2026-06-30 13:10:00', '2026-06-30 13:20:00'],
    'country': ['Singapore', 'UAE', 'South Korea']
}

# 2. Build the DataFrame structures
df = pd.DataFrame(data)

# 3. Export to highly optimized columnar parquet file format
df.to_parquet('sample_raw_data.parquet', index=False)
print("sample_raw_data.parquet created successfully!")