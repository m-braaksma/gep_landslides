
import os
import numpy as np
import geopandas as gpd
from osgeo import gdal
import pygeoprocessing

def clip_rasters(input_raster_paths, mask_vector_path, output_folder, mask_layer="gadm_nepal", dst_crs="ESRI:54030", nodata_value=-9999):
    """
    Clips multiple rasters with mixed data types based on a vector shapefile and saves them to a specified output folder.

    Parameters:
    - input_raster_paths (list of str): List of input raster file paths.
    - mask_vector_path (str): Path to the vector file (GeoPackage) used for clipping.
    - output_folder (str): Folder where the clipped rasters will be saved.
    - mask_layer (str): Layer name in the GeoPackage to use as the mask.
    - dst_crs (str): The desired target CRS for the output raster.
    - nodata_value: The NoData value to set in the output raster (default is -9999).
    """
    for input_raster in input_raster_paths:
        # Open the raster to determine its data type
        src = gdal.Open(input_raster)
        if src is None:
            print(f"Failed to open {input_raster}")
            continue
        band = src.GetRasterBand(1)
        raster_dtype = band.DataType
        dtype_str = gdal.GetDataTypeName(raster_dtype)
        print(f"Processing {input_raster} with data type: {dtype_str}")
        src = None  # Close the dataset

        # Set output raster path
        raster_name = os.path.basename(input_raster)
        output_raster = os.path.join(output_folder, f"clipped_{raster_name}")
        
        # Perform the clipping operation using gdal.Warp
        gdal.Warp(
            output_raster, input_raster,
            dstSRS=dst_crs,
            cutlineDSName=mask_vector_path,
            cutlineLayer=mask_layer,
            cropToCutline=True,
            dstNodata=nodata_value,
            outputType=raster_dtype,  # Use the same data type as the input raster
            warpOptions=["CUTLINE_ALL_TOUCHED=TRUE"],
            options=["COMPRESS=LZW", "TILED=YES", "BIGTIFF=YES"]
        )
        
        print(f"Saved clipped raster to {output_raster}")

# Example usage
input_raster_paths = [
    '/Users/mbraaksma/Files/base_data/seals/static_regressors/alt_m.tif',
    '/Users/mbraaksma/Files/base_data/global_invest/sediment_delivery/Global Erosivity/GlobalR_NoPol-002.tif',
    '/Users/mbraaksma/Files/base_data/global_invest/sediment_delivery/Global Soil Erodibility/Data_25km/RUSLE_KFactor_v1.1_25km.tif'
]
base_path = '/Users/mbraaksma/Files/base_data/lulc/esa/lulc_esa_'
years = range(2000, 2021)  # 2000 to 2020 inclusive
lulc_paths = [f"{base_path}{year}.tif" for year in years]
input_raster_paths.extend(lulc_paths)

mask_vector_path = "/Users/mbraaksma/Files/base_data/gep/landslides/borders/gadm_nepal.gpkg"
output_folder = "/Users/mbraaksma/Files/base_data/gep/landslides/invest_inputs"

clip_rasters(input_raster_paths, mask_vector_path, output_folder)

# Reclassify LULC to recreate no-forest counterfactuals
correspondence_path = '/Users/mbraaksma/Files/base_data/seals/default_inputs/esa_seals7_correspondence.csv'
rules_df = pd.read_csv(correspondence_path)

# Create the value map for reclassification
rules_df['dst_id'] = np.where(rules_df['dst_label'] == 'forest', 200, rules_df['src_id'])
rules_dict = dict(zip(rules_df.src_id, rules_df.dst_id))

input_paths = [
    f"/Users/mbraaksma/Files/base_data/gep/landslides/invest_inputs/clipped_lulc_esa_{year}.tif"
    for year in range(2000, 2021)
]
total_files = len(lulc_paths)

for index, lulc_path in enumerate(input_paths, start=1):    
    print(f"Processing {index}/{total_files}: {lulc_path}")
    target_raster_path = f"{lulc_path[:-4]}_noforest.tif"

    # Get raster info
    raster_info = pygeoprocessing.geoprocessing.get_raster_info(lulc_path)
    target_datatype = raster_info['datatype']
    target_nodata = raster_info['nodata'][0]  # Assuming a single-band raster

    # Call the reclassify_raster function
    pygeoprocessing.geoprocessing.reclassify_raster(
        base_raster_path_band=(lulc_path, 1), 
        value_map=rules_dict, 
        target_raster_path=target_raster_path, 
        target_datatype=target_datatype, 
        target_nodata=target_nodata, 
        values_required=True, 
        raster_driver_creation_tuple=('GTIFF', ('TILED=YES', 'BIGTIFF=YES', 'COMPRESS=LZW', 'BLOCKXSIZE=256', 'BLOCKYSIZE=256'))
    )

########## 
# Convert biophysical table from SEALS TO ESA
import pandas as pd

reverse_reclass_esa_seals7 = {
    1: [190],  # Urban
    2: [10, 11, 12, 20, 30],  # Cropland
    3: [130],  # Grassland
    4: [40, 50, 60, 61, 62, 70, 71, 72, 80, 81, 82, 90, 100],  # Forest
    5: [110, 120, 121, 122, 140],  # Othernat
    6: [210],  # Water
    7: [150, 151, 152, 153, 160, 170, 180, 200, 201, 202, 220],  # Other
}

# Load the CSV into a DataFrame
csv_file = '/Users/mbraaksma/Files/base_data/gep/landslides/invest_inputs/biophysical_table_gura.csv'
df = pd.read_csv(csv_file)

# Expand rows based on the new dictionary
expanded_rows = []
for _, row in df.iterrows():
    lucode = row['lucode']
    if lucode in reverse_reclass_esa_seals7:
        for original_lucode in reverse_reclass_esa_seals7[lucode]:
            new_row = row.copy()
            new_row['original_lucode'] = original_lucode
            expanded_rows.append(new_row)

# Create a new DataFrame from the expanded rows
expanded_df = pd.DataFrame(expanded_rows)

# Save the expanded DataFrame
output_csv = '/Users/mbraaksma/Files/base_data/gep/landslides/invest_inputs/expanded_biophysical_table_gura.csv'
expanded_df.to_csv(output_csv, index=False)

print(f"Expanded data saved to {output_csv}")


# import geopandas as gpd 
# import numpy as np
# from osgeo import gdal 

# input_shape = '/Users/mbraaksma/Files/base_data/cartographic/gadm/gadm_410-levels.gpkg'
# output_shape = '/Users/mbraaksma/Files/base_data/gep/landslides/borders/gadm_nepal.gpkg'
# npl_gdf = gpd.read_file(input_shape, layer='ADM_0', where="COUNTRY = 'Nepal'", engine='pyogrio')
# # npl_gdf = npl_gdf.to_crs('ESRI:54030')
# npl_gdf.to_file(output_shape, driver='GPKG')

# # CLIP LULC
# mask_vector_path = output_shape 
# input_raster = "/Users/mbraaksma/Files/base_data/lulc/esa/lulc_esa_2017.tif"
# output_raster= "/Users/mbraaksma/Files/base_data/gep/landslides/invest_inputs/lulc_esa_2017_clipped.tif" 

# from osgeo import gdal

# gdal.Warp(output_raster, input_raster, 
#            dstSRS='ESRI:54030',
#            cutlineDSName=mask_vector_path, 
#            cutlineLayer='gadm_nepal',
#            cropToCutline=True, 
#            dstNodata=-9999,  # Set NoData to -9999
#            outputType=gdal.GDT_Int16,  # Use int16 as output data type
#            options=["COMPRESS=LZW", "TILED=YES", "BIGTIFF=YES"])  # Set format options



# # Read the first band of the raster (assuming it's a single band raster)
# output_ds = gdal.Open(output_raster)

# band = output_ds.GetRasterBand(1)
# data = band.ReadAsArray()

# # Inspect the values
# print(f"Data type: {data.dtype}")
# print(f"Array shape: {data.shape}")
# print(f"Array values (sample): {data[:5, :5]}")  # First 5x5 cells as an example

# # Check for any no-data values
# nodata_value = band.GetNoDataValue()
# print(f"NoData value: {nodata_value}")

# output_ds = None




# # SUBSET AND REPROJ GPKG
# input_shape = '/Users/mbraaksma/Files/base_data/cartographic/gadm/gadm_410-levels.gpkg'
# output_shape = '/Users/mbraaksma/Files/base_data/gep/landslides/borders/gadm_nepal.gpkg'
# npl_gdf = gpd.read_file(input_shape, layer='ADM_0', where="COUNTRY = 'Nepal'", engine='pyogrio')
# # npl_gdf = npl_gdf.to_crs('ESRI:54030')
# npl_gdf.to_file(output_shape, driver='GPKG')

# # CLIP LULC
# mask_vector_path = output_shape 
# input_raster = "/Users/mbraaksma/Files/base_data/lulc/esa/lulc_esa_2017.tif"
# output_raster= "/Users/mbraaksma/Files/base_data/gep/landslides/invest_inputs/lulc_esa_2017_clipped.tif" 
# gdal.Warp(output_raster, input_raster, 
#             dstSRS='ESRI:54030',
#             cutlineDSName=mask_vector_path, 
#             cutlineLayer='gadm_nepal',
#             cropToCutline=True, 
#             dstNodata=np.nan)

# # Read the first band of the raster (assuming it's a single band raster)
# output_ds = gdal.Open(output_raster)

# band = output_ds.GetRasterBand(1)
# data = band.ReadAsArray()

# # Inspect the values
# print(f"Data type: {data.dtype}")
# print(f"Array shape: {data.shape}")
# print(f"Array values (sample): {data[:5, :5]}")  # First 5x5 cells as an example

# # Check for any no-data values
# nodata_value = band.GetNoDataValue()
# print(f"NoData value: {nodata_value}")

# output_ds = None

# # REPROJ SEALS
# # scenario_list = ['ssp1_rcp26', 'ssp2_rcp45','ssp5_rcp85']
# # year_list = [2030, 2035, 2040]
# # seals_lulc_path = '/Users/mbraaksma/Files/seals/projects/ghana_policy_forest/intermediate/stitched_lulc_simplified_scenarios/'
# # for scenario in scenario_list:
# #     for year in year_list:
# #         input_raster = seals_lulc_path + f'lulc_esa_seals7_{scenario}_luh2-message_bau_{year}_clipped.tif'
# #         output_raster= seals_lulc_path + f'reprojected/lulc_esa_seals7_{scenario}_luh2-message_bau_{year}_clipped.tif'
# #         gdal.Warp(output_raster, input_raster, dstSRS='ESRI:54030')


# # NDR TIFFS 
# # DEM
# mask_vector_path = "/Users/mbraaksma/Files/base_data/pyramids/countries_iso3_ghana.gpkg" 
# gdal.Warp('/Users/mbraaksma/Files/base_data/global_invest/nutrient_delivery/alt_m.tif', 
#           '/Users/mbraaksma/Files/base_data/seals/static_regressors/alt_m.tif', 
#           dstSRS='ESRI:54030',
#           cutlineDSName=mask_vector_path, cropToCutline=True, dstNodata=np.nan)

# # SDR TIFFS 
# # Erosivity
# mask_vector_path = "/Users/mbraaksma/Files/base_data/pyramids/countries_iso3_ghana.gpkg" 
# gdal.Warp('/Users/mbraaksma/Files/base_data/global_invest/sediment_delivery/GlobalR_NoPol-002.tif', 
#           '/Users/mbraaksma/Files/base_data/global_invest/sediment_delivery/Global Erosivity/GlobalR_NoPol-002.tif', 
#           dstSRS='ESRI:54030',
#           cutlineDSName=mask_vector_path, cropToCutline=True, dstNodata=np.nan)
# # Soil Erodibility
# mask_vector_path = "/Users/mbraaksma/Files/base_data/pyramids/countries_iso3_ghana.gpkg" 
# gdal.Warp('/Users/mbraaksma/Files/base_data/global_invest/sediment_delivery/RUSLE_KFactor_v1.1_25km.tif', 
#           '/Users/mbraaksma/Files/base_data/global_invest/sediment_delivery/Global Soil Erodibility/Data_25km/RUSLE_KFactor_v1.1_25km.tif', 
#           dstSRS='ESRI:54030',
#           cutlineDSName=mask_vector_path, cropToCutline=True, dstNodata=np.nan)


