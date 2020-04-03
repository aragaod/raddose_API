from fastapi import FastAPI
import subprocess, sys, json, uuid,os
from libs.raddose_wrapper import raddose

app = FastAPI()

DLS_scratch_folder = '/scratch/raddose3d/'

#methods = {"getdose": "-get_dose", "getexposure": "-getexposure"}

default_flux = 3.0e13

@app.get("/api/v1.0/getdose")
def read_item(flux: float = None, dose: float = None):

    result = run_raddose3d(flux, dose)
    return result


@app.get("/api/v1.0/getexposure")
def read_item(flux: float = None, dose: float = None):

    result = {'TODO': 'NOT YET IMPLEMENTED'}
    #result = run_raddose3d(flux, dose)
    return result
    
def run_raddose3d(*args):
    print(args)
    new_temp_folder_name = uuid.uuid4().hex
    new_temp_folder = os.path.join(DLS_scratch_folder,new_temp_folder_name)

    try:
        os.makedirs(new_temp_folder)
    except Exception as e:
        print(f'Error creating directory {new_temp_folder}')

    if args[0]:
        flux = args[0]
    else:
        flux = default_flux
        
    rp = raddose(output_directory=new_temp_folder,flux=flux)
    rp.run()
        
    return rp.data
