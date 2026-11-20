# AIS replay data

The real-traffic testbed uses Danish Maritime Authority AIS data (2019, Kattegat and Øresund) in the cleaned form
released with TrAISformer (Nguyen and Fablet, IEEE Access 12:21596-21609, 2024). The data are not redistributed here.

```bash
git clone https://github.com/CIA-Oceanix/TrAISformer.git /tmp/TrAISformer
mkdir -p data && cp -r /tmp/TrAISformer/data/ct_dma data/ct_dma
# expected: data/ct_dma/ct_dma_train.pkl, ct_dma_valid.pkl, ct_dma_test.pkl, dma_coastline_polygons.pkl
```

Or point the code to another location with `export CORAL_AIS_DIR=/path/to/ct_dma`.
The pickles are read with `coral/safe_pickle.py`, which only reconstructs NumPy arrays.
The sandbox testbed needs no data.
