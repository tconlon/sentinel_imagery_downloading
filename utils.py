import numpy as np
import pandas as pd
import os
from google.cloud import storage
import pickle
from rasterio import Affine
from dateutil.rrule import rrule, MONTHLY


# Utility functions
def trim_index_csv():
    index_csv = pd.read_csv('/Volumes/Conlon Backup 2TB/GCP Sentinel Hosting/index.csv')
    index_csv_usa = index_csv[(index_csv['NORTH_LAT'] <= 15) &
                              (index_csv['SOUTH_LAT'] >= 3) &
                              (index_csv['WEST_LON'] >= 32) &
                              (index_csv['EAST_LON'] <= 48) &
                              (index_csv['GEOMETRIC_QUALITY_FLAG'] != 'FAILED') &
                              (index_csv['CLOUD_COVER'] <= 30)]
    index_csv_usa.to_csv('/Volumes/Conlon Backup 2TB/GCP Sentinel Hosting/index_eth_only.csv')

def find_images(tile):
    index_csv = pd.read_csv('/Volumes/sel_external/GCP Sentinel Hosting/index_eth_only.csv')

    gs_storage_list = []
    save_file = os.path.join('/Volumes/sel_external/sentinel_imagery/gcp_sentinel_imagery_utils/image_lists',
                                    'image_lists_by_tile', 'ethiopia', 'valid_tiles_{}.pkl'.format(tile))


    tile_dict = {}

    tile_name = tile[1::]
    valid_images = index_csv.loc[(index_csv['MGRS_TILE'] == tile_name) & (index_csv['TOTAL_SIZE'] > 750000000)]

    for index, row in valid_images.iterrows():
        if row['GRANULE_ID'][0:3] != 'L1C':
            valid_images = valid_images.drop(index)

    # Create dict
    for i in range(len(valid_images)):
        sensing_time = valid_images['SENSING_TIME'].iloc[i].split('-')
        year, month = sensing_time[0:2]
        day = sensing_time[2][0:2]

        ym_tuple = (int(year), int(month))
        image_info =  (valid_images['CLOUD_COVER'].iloc[i], year, month, day, valid_images['BASE_URL'].iloc[i])

        if ym_tuple not in tile_dict.keys():
            tile_dict[ym_tuple] = [image_info]
        else:
            tile_dict[ym_tuple].append(image_info)

    # Sort dict
    for key in tile_dict.keys():
        tile_dict[key] = sorted(tile_dict[key], key= lambda x: (x[0], np.abs(int(x[3])-15)))



    with open(save_file, 'wb') as f:
        pickle.dump(tile_dict, f)

def load_images_within_date_range(tile, strt_dt, end_dt):

    date_tuples = [(dt.year, dt.month) for dt in rrule(MONTHLY, dtstart=strt_dt, until=end_dt)]

    image_list = []

    corrupted_images = []

    save_file = os.path.join('/Volumes/sel_external/sentinel_imagery/gcp_sentinel_imagery_utils/image_lists',
                             'image_lists_by_tile', 'ethiopia', 'valid_tiles_{}.pkl'.format(tile))

    with open(save_file, 'rb') as f:
        tile_dict = pickle.load(f)

    for key in tile_dict.keys():

        try:
            if key in date_tuples:
                if key in corrupted_images:
                    image_list.append(tile_dict[key][1])
                else:
                    image_list.append(tile_dict[key][0])

        except Exception as e:
            print(e)
            print('Image not available for {}'.format(key))

    return image_list

def create_dirs(save_dir_base, tile_name, year, month, valid_bands):

    folder_level_1 = os.path.join(save_dir_base, tile_name)
    folder_level_2 = os.path.join(folder_level_1, year)
    folder_level_3 = os.path.join(folder_level_2, month)
    folder_level_cloud = os.path.join(folder_level_3, 'cloud_cover')

    for band in valid_bands:
        folder_level_band = os.path.join(folder_level_3, band)

    if not os.path.isdir(folder_level_1):
        os.mkdir(folder_level_1)
    if not os.path.isdir(folder_level_2):
        os.mkdir(folder_level_2)
    if not os.path.isdir(folder_level_3):
        os.mkdir(folder_level_3)
    if not os.path.exists(folder_level_cloud):
        os.mkdir(folder_level_cloud)
    for band in valid_bands:
        folder_level_band = os.path.join(folder_level_3, band)
        if not os.path.isdir(folder_level_band):
            os.mkdir(folder_level_band)

    return folder_level_3, folder_level_cloud

def download_blob(bucket_name, source_blob_name, destination_file_name):
    """Downloads a blob from the bucket."""
    # bucket_name = "your-bucket-name"
    # source_blob_name = "storage-object-name"
    # destination_file_name = "local/path/to/file"

    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)

    print(
        "Blob {} downloaded to {}.".format(
            source_blob_name, destination_file_name
        )
    )

def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    # bucket_name = "your-bucket-name"
    # source_file_name = "local/path/to/file"
    # destination_blob_name = "storage-object-name"

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)

    print(
        "File {} uploaded to {}.".format(
            source_file_name, destination_blob_name
        )
    )

def list_folders(tile_name):


    base_dir = os.path.join('/Volumes/sel_external/sentinel_imagery/reprojected_tiles', tile_name)
    dirs = [x[0] for x in os.walk(base_dir)]

    year_dirs = []
    month_dirs = []
    band_dirs = []

    for dir in dirs:
        dir_level = len(dir.split('/'))

        if dir_level == 7:
            year_dirs.append(dir)
        elif dir_level == 8:
            month_dirs.append(dir)
        elif dir_level == 9:
            band_dirs.append(dir)

    return year_dirs, month_dirs, band_dirs


