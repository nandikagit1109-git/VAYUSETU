# Raw data for real-data mode (`DATA_MODE=real`)

Place user-supplied files here. The app never fetches anything at startup;
the scripts in `backend/scripts/` are optional and run manually:

- `cpcb/city_day.csv` — CPCB city-level daily pollution (e.g. the public
  2015-2020 compilation). Columns: City, Date, PM2.5, PM10, NO, NO2, NOx, NH3,
  CO, SO2, O3, Benzene, Toluene, Xylene, AQI, AQI_Bucket.
- `power/{city_id}.csv` — NASA POWER daily weather per city.
  Columns: date,T2M,RH2M,PS,WS10M,WD10M (-999 sentinel values are treated as
  missing). Fetch with `python scripts/fetch_nasa_power.py` (needs internet).
- `firms/*.csv` — NASA FIRMS fire points. Columns: latitude,longitude,acq_date,frp
  (confidence optional). Fetch with `python scripts/fetch_firms.py`
  (needs the FIRMS_MAP_KEY env var).
- `s5p/{city_id}.csv` — optional Sentinel-5P columns. Columns:
  date,no2,so2,co,aai. Fetch with `python scripts/fetch_s5p_gee.py`
  (needs Earth Engine auth; this is a stretch integration).

On any missing file or schema mismatch the app logs a warning, falls back to
synthetic data, and reports the reason in `/api/meta` as `fallback_reason`.
