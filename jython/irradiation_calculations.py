

#@David 20201217 I don't know if there is a better way to obtain 
#flux_utils without importing. Maybe already available somewhere? maybe jythonNameMap?

from gdascripts.parameters import beamline_parameters
jythonNameMap = beamline_parameters.JythonNameSpaceMapping()

flux_utils = jythonNameMap.flux_utils

from org.slf4j import LoggerFactory

# jythonNameMap = beamline_parameters.JythonNameSpaceMapping() ## might be needed later


def calculateDatasetDose(exposureSeconds, 
                         transmission, 
                         energyElectronVolts, 
                         horizDiameterMicrons, 
                         vertDiameterMicrons,
                         absortionCoefficient=False):

    flux = calculatePredictedFlux(energyElectronVolts, 
                                  transmission, 
                                  horizDiameterMicrons, 
                                  vertDiameterMicrons)

    return flux_utils.dose_utils._dose_rate(flux, 
                                            horizDiameterMicrons, 
                                            vertDiameterMicrons, 
                                            energyElectronVolts,)*exposureSeconds
    
def calculatePredictedFlux(energyElectronVolts, 
                           Transmission, 
                           horizDiameterMicrons, 
                           vertDiameterMicrons):

    return flux_utils.predict_flux_by_beamsize(energyElectronVolts,
                                               Transmission,
                                               horizDiameterMicrons,
                                               vertDiameterMicrons)
    
def calculateAbsortionCoefficient(energyElectronVolts):
    return flux_utils.dose_utils._muAbs(energyElectronVolts)
    
