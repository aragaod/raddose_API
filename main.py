"""
Main daemon to run that setups up a HTTP restfull API for raddose3D java program
"""

from fastapi import FastAPI, Query
from typing import Union
import subprocess, sys, json, uuid, os
from libs.raddose_wrapper import raddose
from libs.lookuptables import flux_bs_lookup
from decimal import Decimal
from datetime import timedelta
from enum import Enum

# Beamlines = Enum(
#    "Beamlines",
#    {
#        "i03": "i03",
#        "i04": "i04",
#        "i04-1": "i04-1",
#        "i24": "i24",
#    },
# )


class Beamlines(str, Enum):
    i03 = "i03"
    i04 = "i04"
    i041 = "i04-1"
    i24 = "i24"


tags_metadata = [
    {
        "name": "getdose",
        "description": """Calculate dose given a series of parameters

        The most important are: 
        Energy
        Beam size
        Flux
        Crystal size (Assumed the same as the beam if not given)
         
         
        """,
    },
    {
        "name": "getexposure",
        "description": """Calculate exposure given a series of parameters. 
    
    IMPORTANT: One needs to choose which dose method does the dose refere to

    Raddose is not designed to do this calculation so we run with a hardcoded dose 
    and then scale the result to the requested dose, finally run again with the scaled 
    exposure to test.

        """,
        "externalDocs": {
            "description": "Python code in gitlab repo",
            "url": "https://gitlab.diamond.ac.uk/mx/microdose",
        },
    },
    {
        "name": "getflux",
        "description": """Estimate flux based on energy and beamsize input. 
    
        """,
        "externalDocs": {
            "description": "Python code in gitlab repo",
            "url": "https://gitlab.diamond.ac.uk/mx/microdose",
        },
    },
]


app = FastAPI(
    title="RestFUL API for raddose3d",
    description="With this HTTP API one can run raddose3d to calculate dose from a series of parameters or obtain how many seconds exposure for a particular dose demand",
    version="1.0.0",
    openapi_tags=tags_metadata,
)

# DLS_scratch_folder = '/scratch/raddose3d/'
DLS_scratch_folder = f"/run/user/{os.getuid()}/raddose3d/cache/"

# methods = {"getdose": "-get_dose", "getexposure": "-getexposure"}


@app.get("/api/v1.0/getdose", tags=["getdose"])
def read_item(
    xtal_size_x: float = Query(
        None, description="Crystal horizontal size (microns)", title="in microns"
    ),
    xtal_size_y: float = Query(
        None, description="Crystal vertical size (microns)", title="in microns"
    ),
    xtal_size_z: float = Query(
        None, description="Crystal depth size (microns)", title="in microns"
    ),
    comp_reso: float = Query(
        None,
        description="The computational resolution needs to be increased from 0.5 for small crystals of 20 cubic microns or less (pixels/micron)",
        title="pixels per micron",
    ),
    unit_cell_a: float = Query(
        None, description="Unit cell a dimension (angstroms)", title="Angstroms"
    ),
    unit_cell_b: float = Query(
        None, description="Unit cell b dimension (angstroms)", title="Angstroms"
    ),
    unit_cell_c: float = Query(
        None, description="Unit cell c dimension (angstroms)", title="Angstroms"
    ),
    number_of_monomers: int = Query(
        None, description="Number of monomers", title="Integer"
    ),
    number_of_residues: int = Query(
        None, description="Number of aminoacids", title="Integer"
    ),
    elements_protein_concentration: Union[str,None] = Query(default=None, description="Protein HA content", title="e.g. Zn 0.333 S 6", max_length=20),
    elements_solvent_concentration: Union[str,None] = Query(default=None, description="HA concentration", title="e.g. P 425 (in nmol/l)", max_length=20),
    solvent_fraction: float = Query(
        None, description="Solvent content (fractional number)", title="fraction"
    ),
    flux: str = Query(
        None, description="Scientific notation e.g 3e11 acceptable", title="in ph/s"
    ),
    beam_size_x: float = Query(
        None, description="Beam horizontal size (microns)", title="in microns"
    ),
    beam_size_y: float = Query(
        None, description="Beam vertical size (microns)", title="in microns"
    ),
    collimation_x: float = Query(
        None,
        description="Horizontal collimation size (microns) assumes 100 ",
        title="in microns",
    ),
    collimation_y: float = Query(
        None,
        description="Vertical Collimation size (microns) assumes 100",
        title="in microns",
    ),
    energy_kev: float = Query(None, description="X-ray energy (kev)", title="kev"),
    energy_bandpass_kev: float = Query(
        None, description="X-ray energy bandpass (kev) leave empty for DCM", title="kev"
    ),
    oscillation_start: float = Query(
        None, description="Starting angle for dataset (degrees)", title="degrees"
    ),
    oscillation_end: float = Query(
        None, description="End angle for dataset (degrees)", title="degrees"
    ),
    total_exposure_time: float = Query(
        None, description="Total exposure for dataset (s)", title="seconds"
    ),
):
    original_dict = {
        "size_x": xtal_size_x,
        "size_y": xtal_size_y,
        "size_z": xtal_size_z,
        "unit_cell_a": unit_cell_a,
        "unit_cell_b": unit_cell_b,
        "unit_cell_c": unit_cell_c,
        "number_of_monomers": number_of_monomers,
        "number_of_residues": number_of_residues,
        "elements_protein_concentration": elements_protein_concentration,
        "elements_solvent_concentration": elements_solvent_concentration,
        "solvent_fraction": solvent_fraction,
        "flux": "%.1e" % Decimal(flux),
        "beam_size_x": beam_size_x,
        "beam_size_y": beam_size_y,
        "photon_energy": energy_kev,
        "photon_energy_FWHM": energy_bandpass_kev,
        "oscillation_start": oscillation_start,
        "oscillation_end": oscillation_end,
        "total_exposure_time": total_exposure_time,
        "collimation_x": collimation_x,
        "collimation_y": collimation_y,
    }

    filtered_nones = {k: v for k, v in original_dict.items() if v is not None}

    result = run_raddose3d(**filtered_nones)
    return result


@app.get("/api/v1.0/getexposure", tags=["getexposure"])
def read_item(
    xtal_size_x: float = Query(
        None, description="Crystal horizontal size (microns)", title="in microns"
    ),
    xtal_size_y: float = Query(
        None, description="Crystal vertical size (microns)", title="in microns"
    ),
    xtal_size_z: float = Query(
        None, description="Crystal depth size (microns)", title="in microns"
    ),
    comp_reso: float = Query(
        None,
        description="The computational resolution needs to be increased from 0.5 for small crystals of 20 cubic microns or less (pixels/micron)",
        title="pixels per micron",
    ),
    unit_cell_a: float = Query(
        None, description="Unit cell a dimension (angstroms)", title="Angstroms"
    ),
    unit_cell_b: float = Query(
        None, description="Unit cell b dimension (angstroms)", title="Angstroms"
    ),
    unit_cell_c: float = Query(
        None, description="Unit cell c dimension (angstroms)", title="Angstroms"
    ),
    number_of_monomers: int = Query(
        None, description="Number of monomers", title="Integer"
    ),
    number_of_residues: int = Query(
        None, description="Number of aminoacids", title="Integer"
    ),
    elements_protein_concentration: float = Query(
        None, description="Protein concentration (M)", title="Molar"
    ),
    elements_solvent_concentration: float = Query(
        None, description="Crystallant concentration (M)", title="Molar"
    ),
    solvent_fraction: float = Query(
        None, description="Solvent content (fractional number)", title="fraction"
    ),
    flux: str = Query(
        None, description="Scientific notation e.g 3e11 acceptable", title="in ph/s"
    ),
    beam_size_x: float = Query(
        None, description="Beam horizontal size (microns)", title="in microns"
    ),
    beam_size_y: float = Query(
        None, description="Beam vertical size (microns)", title="in microns"
    ),
    energy_kev: float = Query(None, description="X-ray energy (kev)", title="kev"),
    energy_bandpass_kev: float = Query(
        None, description="X-ray energy bandpass (kev) leave empty for DCM", title="kev"
    ),
    oscillation_start: float = Query(
        None, description="Starting angle for dataset (Degrees)", title="degrees"
    ),
    oscillation_end: float = Query(
        None, description="End angle for dataset (Degrees)", title="degrees"
    ),
    total_dose: float = Query(
        None, description="Total dose for dataset (MGy)", title="MGy"
    ),
    dose_method: str = Query(
        "Max Dose",
        description="Dose calculating method (default Max Dose)",
        title="See raddose3d documentation http://scripts.iucr.org/cgi-bin/paper?S0021889813011461",
        enum=["Max Dose", "Average DWD", "Dose Threshold", "AD-ExpRegion"],
    ),
):
    original_dict = {
        "size_x": xtal_size_x,
        "size_y": xtal_size_y,
        "size_z": xtal_size_z,
        "unit_cell_a": unit_cell_a,
        "unit_cell_b": unit_cell_b,
        "unit_cell_c": unit_cell_c,
        "number_of_monomers": number_of_monomers,
        "number_of_residues": number_of_residues,
        "elements_protein_concentration": elements_protein_concentration,
        "elements_solvent_concentration": elements_solvent_concentration,
        "solvent_fraction": solvent_fraction,
        "flux": "%.1e" % Decimal(flux),
        "beam_size_x": beam_size_x,
        "beam_size_y": beam_size_y,
        "photon_energy": energy_kev,
        "photon_energy_FWHM": energy_bandpass_kev,
        "oscillation_start": oscillation_start,
        "oscillation_end": oscillation_end,
    }

    filtered_nones = {k: v for k, v in original_dict.items() if v is not None}

    result = loop_raddose_until_target_dose(total_dose, dose_method, **filtered_nones)

    return result


@app.get("/api/v1.0/getflux", tags=["getflux"])
def read_item(
    energy: float = Query(None, description="Energy (KeV)", title="in KeVs"),
    vsize_sp: int = Query(
        None, description="Vertical beamsize set point (microns)", title="in microns"
    ),
    beamline: Beamlines = Query(None, description="MX beamline"),
):
    if beamline == "i03" or beamline == "i24" or beamline == "i04-1":
        print(str(beamline))
        print(type(beamline))
        return json.dumps("Not implemented for that beamline yet")

    if energy < 6.0 or energy > 20.0:
        print(str(beamline))
        return json.dumps(f"Energy outside range 6 KeV < {energy} < 20.0 Kev")

    redis_key = "i04:energy_flux:lookup:20240420c"
    print(f"Redis key to read is {redis_key}")
    lookup = flux_bs_lookup([redis_key])

    energy = energy * 1000
    print("Re-calculated polinomial fits")
    flux = lookup.calculate_flux(energy, vsize_sp)
    if isinstance(flux, str):
        flux_sn = flux
    else:
        flux_sn = ("{:.5E}".format(flux),)
    n_lenses = lookup.calc_filters(vsize_sp, energy)
    real_bs = lookup.calc_beamsize_from_lenses(n_lenses, energy)
    return {
        "flux": flux,
        "flux_sn": flux_sn,
        "real_h_size": real_bs[0],
        "real_v_size": real_bs[1],
        "extra": {
            "n_lenses": n_lenses,
            "input_energy": energy,
            "input_v_size": vsize_sp,
        },
    }


def run_raddose3d(**kargs):
    print(f"kargs are: {kargs}")
    new_temp_folder_name = uuid.uuid4().hex
    new_temp_folder = os.path.join(DLS_scratch_folder, new_temp_folder_name)

    rp = raddose(output_directory=new_temp_folder, **kargs)
    if not rp.check_if_already_in_redis():
        if make_temporary_folder(new_temp_folder):
            rp.run(redis_timedelta=timedelta(days=15))
    return rp.data


def make_temporary_folder(temp_folder):
    try:
        os.makedirs(temp_folder)
        return temp_folder
    except Exception as e:
        print(f"Error creating directory {temp_folder}. Error was {e}")
        return False


def calculate_exposure_from_dose(initial_exposure, initial_dose, required_dose):
    new_exposure = required_dose * initial_exposure / initial_dose
    return new_exposure


def loop_raddose_until_target_dose(
    total_dose,
    dose_method,
    starting_exposure=10.0,
    number_of_iterations=10,
    deadband=0.1,
    **kargs,
):
    # running first time with fixed exposure time
    kargs["total_exposure_time"] = starting_exposure
    new_exposure = starting_exposure
    new_result = run_raddose3d(**kargs)

    # Checking if dose that came back is inside deadbank from requested (almost for sure not)
    for n in range(number_of_iterations):
        lower_limit = total_dose - deadband
        upper_limit = total_dose + deadband
        print(f"here: {lower_limit}, {new_result[dose_method]}, {upper_limit}")
        if not lower_limit < new_result[dose_method] < upper_limit:
            print("there")
            new_exposure = round(
                calculate_exposure_from_dose(
                    new_exposure, new_result[dose_method], total_dose
                ),
                1,
            )
            kargs["total_exposure_time"] = new_exposure
            # Running raddose3d again
            new_result = run_raddose3d(**kargs)
        else:
            break

    new_result["total_exposure"] = new_exposure
    new_result["input_parameters"]["requested_dose"] = total_dose
    new_result["input_parameters"]["dose_method"] = dose_method
    return new_result
