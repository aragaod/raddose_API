from fastapi import FastAPI
import subprocess, sys, json, uuid,os
from libs.raddose_wrapper import raddose
from decimal import Decimal
from datetime import timedelta

app = FastAPI()

#DLS_scratch_folder = '/scratch/raddose3d/'
DLS_scratch_folder = '/run/user/1007182/raddose3d/'

#methods = {"getdose": "-get_dose", "getexposure": "-getexposure"}


@app.get("/api/v1.0/getdose")
def read_item(
        xtal_size_x: float = None,
        xtal_size_y: float = None,
        xtal_size_z: float = None,
        comp_reso: float = None,
        unit_cell_a: float = None,
        unit_cell_b: float = None,
        unit_cell_c: float = None,
        number_of_monomers: int = None,
        number_of_residues: int = None,
        elements_protein_concentration: float =  None,
        elements_solvent_concentration: float =  None,
        solvent_fraction: float = None,
        flux: float = None,
        beam_size_x: float = None,
        beam_size_y: float = None,
        energy_kev: float = None,
        oscillation_start: float = None,
        oscillation_end: float = None,
        total_exposure_time: float = None):
    
    original_dict = {
        'size_x':xtal_size_x,
        'size_y':xtal_size_y,
        'size_z':xtal_size_z,
        'unit_cell_a':unit_cell_a,
        'unit_cell_b':unit_cell_b,
        'unit_cell_c':unit_cell_c,
        'number_of_monomers':number_of_monomers,
        'number_of_residues':number_of_residues,
        'elements_protein_concentration':elements_protein_concentration,
        'elements_solvent_concentration':elements_solvent_concentration,
        'solvent_fraction':solvent_fraction,
        'flux':'%.1e' % Decimal(flux),
        'beam_size_x':beam_size_x,
        'beam_size_y':beam_size_y,
        'photon_energy':energy_kev,
        'oscillation_start':oscillation_start,
        'oscillation_end':oscillation_end,
        'total_exposure_time':total_exposure_time,
    }

    
    filtered_nones = {k: v for k, v in original_dict.items() if v is not None}
    
    result = run_raddose3d(**filtered_nones)
    return result


@app.get("/api/v1.0/getexposure")
def read_item(flux: float = None, beam_size_x: float = None, beam_size_y: float = None, total_exposure_time: float = None):

    result = {'TODO': 'NOT YET IMPLEMENTED'}
    #result = run_raddose3d(flux=kargs['flux'])
    return result
    
def run_raddose3d(**kargs):
    print(f'kargs are: {kargs}')
    new_temp_folder_name = uuid.uuid4().hex
    new_temp_folder = os.path.join(DLS_scratch_folder,new_temp_folder_name)
    
    rp = raddose(output_directory=new_temp_folder,**kargs)
    if not rp.check_if_already_in_redis():
        if make_temporary_folder(new_temp_folder):
            rp.run(redis_timedelta=timedelta(days=15))
    return rp.data

def make_temporary_folder(temp_folder):
    
    try:
        os.makedirs(temp_folder)
        return temp_folder
    except Exception as e:
        print(f'Error creating directory {temp_folder}. Error was {e}')
        return False
