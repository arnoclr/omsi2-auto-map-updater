from google.cloud import storage
import os
from tqdm import tqdm
from pathlib import Path
from hashlib import sha1
import requests
import sys
import zipfile

def resourcePath(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def logEvent(category = "Executable", action = None):
    # send google analytics data
    cid = sha1(os.getlogin().encode()).hexdigest()[:10]
    event = {
        "v": 1,
        "tid": "UA-140457323-1",
        "cid": cid,
        "t": "event",
        "ec": category,
        "ea": action
    }
    req = requests.post("https://www.google-analytics.com/collect", event)
    # print(req.text)

if __name__ == "__main__":
    print("(c) omsistuff 2021")
    print("Auto map updater (Marne la Vallée)")

    # const
    steamapps_zip = r"C:\Program Files (x86)\Steam\steamapps\common\tmp.zip"
    omsi_folder = r"C:\Program Files (x86)\Steam\steamapps\common\OMSI 2"
    filename = os.path.join(omsi_folder, "plugins", "ga.omsistuff.maps.mlv.md5")

    # create instance of gcs
    storage_client = storage.Client.from_service_account_json(resourcePath('credentials.json'))
    bucket = storage_client.bucket('omsistuff-cdn')

    # get blob metadata
    blob = bucket.get_blob('maps/mlv.zip')
    hash_from_gcs = blob.md5_hash

    # read lasest hash file
    if not os.path.exists(filename):
        f = open(filename, 'w')
        f.close()

    hash_file = open(filename, "r+")
    hash_from_file = hash_file.readline()

    # compare 2 hash
    if hash_from_gcs != hash_from_file:
        print('New version available')

        # write new hash in file
        hash_file.seek(0)
        hash_file.write(hash_from_gcs)
        hash_file.truncate()

        # download new file version
        print('Download is starting ...')
        with open(steamapps_zip, 'wb') as f:
            with tqdm.wrapattr(f, "write", total=blob.size) as file_obj:
                storage_client.download_blob_to_file(blob, file_obj)

        # self update exe
        # delete all exe file that no currently running
        plugins_folder = os.path.join(omsi_folder, 'plugins')
        plugins_files = os.listdir(plugins_folder)
        for item in plugins_files:
            if item.endswith(".exe"):
                try:
                    os.remove(os.path.join(plugins_folder, item))
                except:
                    continue

        # extract archive
        print('Extract zip in OMSI folder')
        exe_hash = 'ga.omsistuff.maps.updater.' + hash_from_gcs[:5] + '.exe'
        with zipfile.ZipFile(steamapps_zip, 'r') as zf:
            # Get a list of all archived file names from the zip
            listOfFileNames = zf.namelist()
            # Iterate over the file names
            for fileName in listOfFileNames:
                # try to extract
                if fileName.endswith(".exe"):
                    executable_path = os.path.join(plugins_folder, exe_hash)
                    with open(executable_path, "wb") as f:  # open the output path for writing
                        try:
                            f.write(zf.read(fileName))
                        except:
                            continue
                else:
                    try:
                        zf.extract(fileName, omsi_folder)
                    except:
                        print('! unable to extract {}'.format(fileName))

        # change exe path in .cfg
        cfg = os.path.join(plugins_folder, 'run_on_close.cfg')
        f = open(cfg, "w")
        f.write('plugins\\' + exe_hash)
        f.close()

        os.remove(steamapps_zip)
        logEvent(action = "map_update")

    else:
        print('Map is already up to date')
        logEvent(action = "map_up_to_date")

    hash_file.close()
    print('Close installer')
