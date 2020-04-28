from fastapi import FastAPI, Query
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
        xtal_size_x: float = Query(None, description="Crystal horizontal size (microns)", title="in microns"),
        xtal_size_y: float = Query(None, description="Crystal vertical size (microns)", title="in microns"),
        xtal_size_z: float = Query(None, description="Crystal depth size (microns)", title="in microns"),
        comp_reso: float = Query(None, description="The computational resolution needs to be increased from 0.5 for small crystals of 20 cubic microns or less (pixels/micron)", title="pixels per micron"),
        unit_cell_a: float = Query(None, description="Unit cell a dimension (angstroms)", title="Angstroms"),
        unit_cell_b: float = Query(None, description="Unit cell b dimension (angstroms)", title="Angstroms"),
        unit_cell_c: float = Query(None, description="Unit cell c dimension (angstroms)", title="Angstroms"),
        number_of_monomers: int = Query(None, description="Number of monomers", title="Integer"),
        number_of_residues: int = Query(None, description="Number of aminoacids", title="Integer"),
        elements_protein_concentration: float =  Query(None, description="Protein concentration (M)", title="Molar"),
        elements_solvent_concentration: float =  Query(None, description="Crystallant concentration (M)", title="Molar"),
        solvent_fraction: float = Query(None, description="Solvent content (fractional number)", title="fraction"),
        flux: str = Query(None, description="Scientific notation e.g 3e11 acceptable", title="in ph/s"),
        beam_size_x: float = Query(None, description="Beam horizontal size (microns)", title="in microns"),
        beam_size_y: float = Query(None, description="Beam vertical size (microns)", title="in microns"),
        energy_kev: float = Query(None, description="X-ray energy (kev)", title="kev"),
        oscillation_start: float = Query(None, description="Starting angle for dataset (degrees)", title="degrees"),
        oscillation_end: float = Query(None, description="End angle for dataset (degrees)", title="degrees"),
        total_exposure_time: float = Query(None, description="Total exposure for dataset (s)", title="seconds")):
    
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
def read_item(
        xtal_size_x: float = Query(None, description="Crystal horizontal size (microns)", title="in microns"),
        xtal_size_y: float = Query(None, description="Crystal vertical size (microns)", title="in microns"),
        xtal_size_z: float = Query(None, description="Crystal depth size (microns)", title="in microns"),
        comp_reso: float = Query(None, description="The computational resolution needs to be increased from 0.5 for small crystals of 20 cubic microns or less (pixels/micron)", title="pixels per micron"),
        unit_cell_a: float = Query(None, description="Unit cell a dimension (angstroms)", title="Angstroms"),
        unit_cell_b: float = Query(None, description="Unit cell b dimension (angstroms)", title="Angstroms"),
        unit_cell_c: float = Query(None, description="Unit cell c dimension (angstroms)", title="Angstroms"),
        number_of_monomers: int = Query(None, description="Number of monomers", title="Integer"),
        number_of_residues: int = Query(None, description="Number of aminoacids", title="Integer"),
        elements_protein_concentration: float =  Query(None, description="Protein concentration (M)", title="Molar"),
        elements_solvent_concentration: float =  Query(None, description="Crystallant concentration (M)", title="Molar"),
        solvent_fraction: float = Query(None, description="Solvent content (fractional number)", title="fraction"),
        flux: str = Query(None, description="Scientific notation e.g 3e11 acceptable", title="in ph/s"),
        beam_size_x: float = Query(None, description="Beam horizontal size (microns)", title="in microns"),
        beam_size_y: float = Query(None, description="Beam vertical size (microns)", title="in microns"),
        energy_kev: float = Query(None, description="X-ray energy (kev)", title="kev"),
        oscillation_start: float = Query(None, description="Starting angle for dataset (Degrees)", title="degrees"),
        oscillation_end: float = Query(None, description="End angle for dataset (Degrees)", title="degrees"),
        total_dose: float = Query(None, description="Total dose for dataset (MGy)", title="MGy"),
        dose_method: str = Query('Max Dose', description="Dose calculating method (default Max Dose)", title="See raddose3d documentation http://scripts.iucr.org/cgi-bin/paper?S0021889813011461", enum=["Max Dose", "Average DWD", "Dose Threshold", "AD-ExpRegion"])):
    
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
        'oscillation_end':oscillation_end}

    
    filtered_nones = {k: v for k, v in original_dict.items() if v is not None}

    result = loop_raddose_until_target_dose(total_dose, dose_method, **filtered_nones)
   
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

def calculate_exposure_from_dose(initial_exposure,initial_dose,required_dose):
    new_exposure = required_dose * initial_exposure / initial_dose
    return new_exposure

def loop_raddose_until_target_dose(total_dose, dose_method, starting_exposure = 10.0, number_of_iterations = 10, deadband = 0.1, **kargs):

    
    
    #running first time with fixed exposure time
    kargs['total_exposure_time'] = starting_exposure
    new_exposure = starting_exposure
    new_result = run_raddose3d(**kargs)

    #Checking if dose that came back is inside deadbank from requested (almost for sure not)
    for n in range(number_of_iterations):
        lower_limit = total_dose - deadband
        upper_limit = total_dose + deadband
        print(f'here: {lower_limit}, {new_result[dose_method]}, {upper_limit}')
        if  not lower_limit < new_result[dose_method] < upper_limit:
            print('there')
            new_exposure = round(calculate_exposure_from_dose(new_exposure, new_result[dose_method], total_dose),1)
            kargs['total_exposure_time'] = new_exposure
            #Running raddose3d again
            new_result = run_raddose3d(**kargs)
        else:
            break

    new_result['total_exposure'] = new_exposure
    return new_result
