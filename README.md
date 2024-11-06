# dsa4264-lta-geospatial

## Set up

``` bash
conda create -n dsa4264 python=3.11
conda activate dsa4264
pip install -r requirements.txt
```

## Streamlit app

Copy `appdata` (provided in repo data GDrive link) into `app/`.  
Copy `data` (provided in repo data GDrive link) into repo root.  

Ensure that Streamlit is available in your environment:

``` bash
streamlit --version
```

In the repo root directory, run the following:

``` bash
streamlit run app/app.py
```
