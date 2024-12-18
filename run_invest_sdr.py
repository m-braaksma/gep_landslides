
import logging
import sys
import os
import natcap.invest.sdr.sdr

LOGGER = logging.getLogger(__name__)
root_logger = logging.getLogger()

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    fmt=natcap.invest.utils.LOG_FMT,
    datefmt='%m/%d/%Y %H:%M:%S ')
handler.setFormatter(formatter)
logging.basicConfig(level=logging.INFO, handlers=[handler])

user_dir = os.path.expanduser('~')
input_dir = os.path.join(user_dir, 'Files', 'base_data', 'gep', 'landslides', 'invest_inputs')

sdr_args = {
    'biophysical_table_path': os.path.join(input_dir, 'expanded_biophysical_table_gura.csv'),
    'dem_path': os.path.join(input_dir, 'clipped_alt_m.tif'),
    'drainage_path': '',
    'erodibility_path': os.path.join(input_dir, 'clipped_RUSLE_KFactor_v1.1_25km.tif'),
    'erosivity_path': os.path.join(input_dir, 'clipped_GlobalR_NoPol-002.tif'),
    'ic_0_param': '0.5',
    'k_param': '2',
    'l_max': '122',
    'lulc_path': '',
    'n_workers': '-1',
    'results_suffix': '',
    'sdr_max': '0.8',
    'threshold_flow_accumulation': '1000',
    'watersheds_path': os.path.join(input_dir, 'hybas_as_lev06_v1c.gpkg'),
    'workspace_dir': '',
}

if __name__ == '__main__':
    # Run scenarios
    year_list = range(2000, 2021)
    cur_dir = os.path.join(user_dir, 'Files', 'base_data', 'gep', 'landslides', 'invest_sdr')

    for year in year_list:
        # SDR
        output_dir = os.path.join(cur_dir, str(year))
        os.makedirs(output_dir, exist_ok=True)
        sdr_args['workspace_dir'] = output_dir
        sdr_args['lulc_path'] = os.path.join(input_dir, f'clipped_lulc_esa_{year}.tif')
        natcap.invest.sdr.sdr.execute(sdr_args)

        # SDR - No Forest
        output_dir = os.path.join(cur_dir, str(year)+'_noforest')
        os.makedirs(output_dir, exist_ok=True)
        sdr_args['workspace_dir'] = output_dir
        sdr_args['lulc_path'] = os.path.join(input_dir, f'clipped_lulc_esa_{year}_noforest.tif')
        natcap.invest.sdr.sdr.execute(sdr_args)
