from fastapi import FastAPI
import subprocess, sys, json
from libs.raddose_wrapper import raddose

app = FastAPI()


methods = {"getdose": "-get_dose", "getexposure": "-getexposure"}


@app.get("/api/v1.0/{method}")
def read_item(method: str, flux: float = None, dose: float = None):

    result = run_raddose3d(flux, dose,get_method=method)
    return result
    #return fake_items_db[skip : skip + limit]

def run_raddose3d(*args,get_method):
    print(args)
    p = subprocess.Popen(['bash',"./dummy_process.sh", get_method ,f"{args[0]}"],
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE)
    out, _ = p.communicate()
    #print(out)
    return(out.decode())
