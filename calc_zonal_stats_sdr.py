
import os
from rasterstats import zonal_stats
import pandas as pd


def calc_zonal_stats(raster_base_path, borders_path, year_list, output_path):
    zonal_stats_list = []

    # Loop through years and calculate zonal statistics
    for year in year_list:
        raster_path = raster_base_path.replace("XXXX", str(year))
        print(f"Processing raster for year {year}...")
        stats = zonal_stats(borders_path, raster_path, stats='mean')  # List of dictionaries
        for fid, stat in enumerate(stats):  # Enumerate assumes stats is ordered by fid
            stat['fid'] = fid + 1
            stat['year'] = year
            zonal_stats_list.append(stat)

    zonal_stats_df = pd.DataFrame(zonal_stats_list)
    zonal_stats_df.rename(columns={'mean': 'avg_sed_exp'}, inplace=True)
    zonal_stats_df.to_csv(output_path, index=False)


user_dir = os.path.expanduser('~')
cur_dir = os.path.join(user_dir, 'Files', 'base_data', 'gep', 'landslides')

borders_path = os.path.join(cur_dir, 'borders', 'gadm_nepal_adm3_esri54030.gpkg')
raster_base_path = os.path.join(cur_dir, 'invest_sdr', 'XXXX', 'sed_export.tif')
output_path = os.path.join(cur_dir, 'invest_sdr', 'sdr_panel.csv')
raster_base_path_noforest = os.path.join(cur_dir, 'invest_sdr', 'XXXX_noforest', 'sed_export.tif')
output_path_noforest = os.path.join(cur_dir, 'invest_sdr', 'sdr_noforest_panel.csv')
year_list = range(2000, 2021)

calc_zonal_stats(raster_base_path, borders_path, year_list, output_path)
calc_zonal_stats(raster_base_path_noforest, borders_path, year_list, output_path_noforest)
