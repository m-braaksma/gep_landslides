import os
import numpy as np
import matplotlib.pyplot as plt
from osgeo import gdal

from skimpy import skim
import pandas as pd
import geopandas as gpd
from rasterstats import zonal_stats

# Directories and paths
user_dir = os.path.expanduser('~')
data_dir = os.path.join(user_dir, 'Files', 'base_data', 'gep', 'landslides')
cur_dir = os.path.join(user_dir, 'Files', 'gep_landslides')

# Import data
emdat_path = os.path.join(data_dir, 'emdat','public_emdat_2024-09-09.xlsx')
emdat = pd.read_excel(emdat_path)

# Subset data
emdat[emdat['Disaster Type']=='Mass movement (wet)']['Disaster Subtype'].value_counts()
landslide_condition = (emdat['Disaster Type'] == 'Mass movement (wet)') & ((emdat['Disaster Subtype']=='Landslide (wet)') | (emdat['Disaster Subtype']=='Mudslide'))
emdat_landslides = emdat[landslide_condition]
emdat_landslides = emdat_landslides.dropna(subset=['Total Deaths'])
skim(emdat_landslides)

# Convert to geopandas
# disasterlocations_path = os.path.join(data_dir, 'pend-gdis-1960-2018-disasterlocations-gpkg', 'pend-gdis-1960-2018-disasterlocations.gpkg')
# disasterlocations = gpd.read_file(disasterlocations_path)
# # emdat_gdf = world_borders.merge(emdat_landslides, left_on='iso3', right_on='ISO', how='inner')
# # emdat_gdf.explore()

disasterlocations_path = os.path.join(data_dir, 'pend-gdis-1960-2018-disasterlocations-gpkg', 'pend-gdis-1960-2018-disasterlocations.gpkg')
disasterlocations = gpd.read_file(
    disasterlocations_path,
    where="disastertype = 'landslide' AND level = '3'",
    engine='pyogrio'
)
disasterlocations = disasterlocations[disasterlocations['location'] != 'Okhaldunga District'] # drop duplicate

emdat['disasterno'] = emdat['DisNo.'].str.extract(r'(\d{4}-\d{4})')
emdat_gdf = disasterlocations.merge(emdat, on='disasterno', how='left')


########################################## 
####### Import gadm adm3 borders for relevant countries
########################################## 
# Step 1: Extract unique 'iso3' values
unique_country = emdat_gdf['country'].unique()

# Step 2: Format the 'where' clause for SQL query
country_filter = " OR ".join([f"COUNTRY = '{country}'" for country in unique_country])

# Step 3: Read the vector file using the dynamically generated 'where' clause
gadm_path = '/Users/mbraaksma/Files/base_data/cartographic/gadm/gadm_410-levels.gpkg'

borders_gdf = gpd.read_file(
    gadm_path,
    where=country_filter,
    engine='pyogrio',
    layer='ADM_3'
)

# Check number of countries match 
emdat_countries = emdat_gdf['country'].unique()
borders_countries = borders_gdf['COUNTRY'].unique()
assert set(emdat_countries) == set(borders_countries)


## Merge and keep Nepal for test case
emdat_nepal = emdat_gdf[emdat_gdf['country'] == 'Nepal']
border_nepal = borders_gdf[borders_gdf['COUNTRY'] == 'Nepal']

emdat_nepal_adm3 = emdat_nepal.merge(border_nepal, how='right', left_on='adm3', right_on='NAME_3')
# Drop the geometry_x column (from the left DataFrame)
emdat_nepal_adm3 = emdat_nepal_adm3.drop(columns=['geometry_x'])
# Ensure geometry_y is set as the geometry
emdat_nepal_adm3 = gpd.GeoDataFrame(emdat_nepal_adm3, geometry='geometry_y')





# Step 1: Collapse to adm3 level and sum Total Deaths
emdat_nepal_adm3_agg = emdat_nepal_adm3.groupby(['adm3','Start Year']).agg({'Total Deaths': 'sum'}).reset_index()

# Step 2: Merge with border_nepal to get geometries (perform a left join to keep all border_nepal regions)
emdat_nepal_adm3_merged = border_nepal.merge(emdat_nepal_adm3_agg, how='left', left_on='NAME_3', right_on='adm3')

# Step 3: Fill missing Total Deaths with 0
emdat_nepal_adm3_merged['Total Deaths'] = emdat_nepal_adm3_merged['Total Deaths'].fillna(0)

# Step 4: Plot the resulting data
fig, ax = plt.subplots(figsize=(10, 10))
emdat_nepal_adm3_merged.plot(column='Total Deaths', ax=ax, legend=True,
                             legend_kwds={'label': "Total Deaths by Region",
                                          'orientation': "horizontal"},
                             edgecolor='black', cmap='Reds')
ax.set_title("Total Deaths by Region (ADM3 level)", fontsize=16)
ax.set_xlabel("Longitude", fontsize=12)
ax.set_ylabel("Latitude", fontsize=12)
plt.show()




########################################## 
####### Import gadm adm3 borders for relevant countries
########################################## 

import os
import pandas as pd
from osgeo import ogr

# Define file paths
borders_path = '/Users/mbraaksma/Files/base_data/gep/landslides/borders/gadm_nepal_adm3.gpkg'
raster_base_path = '/Users/mbraaksma/Files/base_data/gep/landslides/nasa-gpw/gpw-v4-population-density-rev11_XXXX_30_sec_tif/gpw_v4_population_density_rev11_XXXX_30_sec.tif'
years = [2000, 2005, 2010, 2015, 2020]

# Load the GeoPackage to get the fids and identifying attributes
shapefile = ogr.Open(borders_path)
layer = shapefile.GetLayer()
fid_data = []
for feature in layer:
    fid = feature.GetFID()
    props = feature.items()
    props['fid'] = fid
    fid_data.append(props)

# Convert shapefile attributes to a DataFrame
shapefile_df = pd.DataFrame(fid_data)

# Initialize an empty list to store results
zonal_stats_list = []

# Loop through years and calculate zonal statistics
for year in years:
    raster_path = raster_base_path.replace("XXXX", str(year))
    print(f"Processing raster for year {year}...")
    stats = zonal_stats(borders_path, raster_path)  # List of dictionaries
    for fid, stat in enumerate(stats):  # Enumerate assumes stats is ordered by fid
        stat['fid'] = fid + 1
        stat['year'] = year
        zonal_stats_list.append(stat)
        # 'NPL.5.3.6_1'

# Convert the list of dictionaries to a DataFrame
zonal_stats_df = pd.DataFrame(zonal_stats_list)
zonal_stats_df.rename(
    columns=lambda col: f"pop_{col}" if col not in ['fid'] else col,
    inplace=True
)

# Merge the zonal statistics with the shapefile data
pop_df = zonal_stats_df.merge(shapefile_df, on='fid')

# Save the panel dataset to a CSV
output_csv = '/Users/mbraaksma/Files/base_data/gep/landslides/nasa-gpw/nasa-gpw_panel.csv'
pop_df.to_csv(output_csv, index=False)
print(f"Panel dataset saved to {output_csv}")



# EXPAND EMDAT TO BALANCED PANEL
# Generate all possible GID_3-year combinations
all_gid_3 = emdat_nepal_adm3_merged['GID_3'].unique()
# all_years = range(emdat_nepal_adm3_merged['year'].min(), emdat_nepal_adm3_merged['year'].max() + 1)
all_years = range(2000, 2021)
all_combinations = pd.MultiIndex.from_product([all_gid_3, all_years], names=['GID_3', 'year'])

# Convert to a DataFrame
expanded_panel = pd.DataFrame(index=all_combinations).reset_index()

# Merge with the original data
emdat_panel = expanded_panel.merge(emdat_nepal_adm3_merged, on='GID_3', how='left')

# Fill missing values for 'Total Deaths' with 0
emdat_panel['Total Deaths'] = emdat_panel['Total Deaths'].fillna(0)

# Optionally sort for better readability
emdat_panel.sort_values(by=['GID_3', 'year'], inplace=True)




# MERGE EMDAT TO POP
# Function to find the closest year
def match_closest_year(row, available_years):
    return min(available_years, key=lambda x: abs(row - x))
pop_years = [2000, 2005, 2010, 2015, 2020]

# Add closest population year to panel data
emdat_panel['pop_year'] = emdat_panel['year'].apply(lambda x: match_closest_year(x, pop_years))

# Merge population data with panel data
pop_df = pop_df[['pop_min', 'pop_max', 'pop_mean', 'pop_count', 'pop_year', 'GID_3', 'fid']]
emdat_pop_panel = emdat_panel.merge(pop_df, on=['GID_3', 'pop_year'], how='left')



emdat_pop_panel_gdf = gpd.GeoDataFrame(emdat_pop_panel, geometry='geometry')





###################
# MERGE WITH SDR
###################

sdr_path = os.path.join(data_dir, 'invest_sdr', 'sdr_panel.csv')
sdr_df = pd.read_csv(sdr_path)

panel_gdf = emdat_pop_panel_gdf.merge(sdr_df, on=['fid','year'], how='left')


panel_gdf = panel_gdf.rename(columns={'fid': 'original_fid'})
panel_gdf['fid'] = panel_gdf.index
panel_gdf_output_path = os.path.join(data_dir, 'full_panel.gpkg')
panel_gdf.to_file(panel_gdf_output_path, driver='GPKG')


import pyfixest as pf

panel_df = pd.DataFrame(panel_gdf)
panel_df['deaths'] = panel_df['Total Deaths']
results = pf.feols("deaths ~ avg_sed_exp + pop_mean + C(GID_3) + C(year)", data=panel_df)
results.summary()


## TRY Poisson
import statsmodels.api as sm
import statsmodels.formula.api as smf

# Log-transform the independent variables
panel_df['ln_avg_sed_exp'] = panel_df['avg_sed_exp'].apply(lambda x: np.log(x) if x > 0 else np.nan)
panel_df['ln_pop_mean'] = panel_df['pop_mean'].apply(lambda x: np.log(x) if x > 0 else np.nan)

# Fit the Poisson regression model
formula = "deaths ~ ln_avg_sed_exp + ln_pop_mean + C(year)"
model = smf.glm(formula=formula, data=panel_df, family=sm.families.Poisson()).fit()

# Print the summary
print(model.summary())
