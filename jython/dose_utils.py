import math
from gda.factory import Finder
from org.slf4j import LoggerFactory
from gda.px.flux import DoseEstimateProvider
from gdascripts.parameters import beamline_parameters



jythonNameMap = beamline_parameters.JythonNameSpaceMapping()

#fswitch_tool = jythonNameMap.beam_size
import fswitch as fswitch_tool

def actual_energy():
	# get current energy
	bl = jythonNameMap.bl
	energy = bl()
	return energy

logger = LoggerFactory.getLogger(__name__)

flux = Finder.find("flux")
dose_rate = Finder.find("dose_rate")
dose_rate_calculator = Finder.find("dose_rate_calculator")

import fswitch as beam_size

# Alias for convenience
dose = dose_rate_calculator

#@DavidAragao, 20201217
#Many changes as part of epics ticket MXGDA-2266

class DoseUtils():
        def __init__(self):
                self.actual_energy = actual_energy

        def _dose_rate(self,
                       flux, 
                       beamWidthInMicrons, 
                       beamHeightInMicrons, 
                       energyInEv, 
                       method='muAbs'): #Options are muAbs or raddose
                
                if method == "muAbs":
                        muAbs = self._muAbs(energyInEv)
                        rate = self.calculate_dose_via_muAbs(1,
                                                             flux,
                                                             muAbs,
                                                             beamWidthInMicrons,
                                                             beamHeightInMicrons,
                                                             energyInEv)
                elif method == "raddose":
                        flux=int(flux)
                        rate = self.calculate_dose_via_raddose3d(1, 
                                                                 flux, 
                                                                 energyInEv, 
                                                                 beamWidthInMicrons, 
                                                                 beamHeightInMicrons)
                return rate

        def calculate_dose_via_muAbs(self,
                                     seconds,
                                     flux,
                                     muAbs,
                                     beamWidthInMicrons,
                                     beamHeightInMicrons,
                                     energyInEv):

                beamWidthInMm = beamWidthInMicrons/1000.0
                beamHeightInMm = beamHeightInMicrons/1000.0
                energyInKev = energyInEv/1000.0

                beamAreaInSquareMm = math.pi * (beamWidthInMm/2.0) * (beamHeightInMm/2.0)

                dose_rate = muAbs * flux * energyInKev / beamAreaInSquareMm * 1.23e-10 / 1e6 

                #Below calls DoseCalculator.java when we want to keep the logic back here in Jython
                #dose_rate = dose_rate_calculator.calculateDosePerSecond(flux,
                #                                                  muAbs,
                #                                                  beamWidthInMicrons,
                #                                                  beamHeightInMicrons,
                #                                                  energyInEv)*seconds

                return  dose_rate
    
        def calculate_dose_via_raddose3d(self,
                                         total_exposure,
                                         flux_reading=False,
                                         energy=False, 
                                         beamsize_x=False, 
                                         beamsize_y=False,
                                         dose_method='Max Dose'):
                if energy == False:
                        energy = self.actual_energy()
                if flux_reading == False:
                        flux_reading = int(flux.rawGetPosition())
                try:
                        if beamsize_x == False or beamsize_y == False:
                                beamsize_x, beamsize_y = fswitch_tool.calc_beamsize_from_lenses()
                                import raddose3d_queries
                                raddose_client = raddose3d_queries.Raddose_API_client()
                                
                                return raddose_client.get_dose_with_assumptions(total_exposure_time=total_exposure,
                                                                                flux=flux_reading, 
                                                                                beamsize_x=beamsize_x, 
                                                                                beamsize_y=beamsize_y, 
                                                                                energy_kev=energy/1000)
    
                except Exception as e:
                        print('Failed to calculate dose via raddose3d with error %s' %(e))
                        return 0.0
                        
                        
        def actual_dose_rate(self,method='muAbs'):
                energy = self.actual_energy()
                # get beam size
                beamSizeXObject = Finder.find("beamSizeX")
                beamSizeYObject = Finder.find("beamSizeY")
                realBeamSizeX, realBeamSizeY = beam_size.calc_beamsize_from_lenses()
                #realBeamSizeX = beamSizeXObject.getPosition()
                #realBeamSizeY = beamSizeYObject.getPosition()
                flux_reading = flux.rawGetPosition()
                return self._dose_rate(flux_reading,realBeamSizeX,realBeamSizeY,energy,method)
                
                
        def calculate_current_dose_rate(self,method='muAbs'): #Options are muAbs or raddose
                try:
                        current_dose_rate = self.actual_dose_rate(method)
                        dose_rate.moveTo(current_dose_rate)
                        return current_dose_rate
                except:
                        logger.error("Unable to calculate dose rate")
    
    
        def _muAbs(self,energy):
                #logger.debug("current energy is %d eV" % energy)
                muAbsObject = Finder.find("muAbs")
                if (muAbsObject.isUseDefault()):
                        muAbsValue = dose_rate_calculator.muAbsForAverageSample(energy)
                        muAbsObject.moveTo(muAbsValue)
                else:
                        muAbsValue = muAbsObject.getPosition()
                #logger.debug("Using muAbs = %g" % muAbsValue)
                return muAbsValue
    
    
        def calculate_current_dose_per_frame(self,exposure):
                try:
                        dose_rate = self.calculate_current_dose_rate()
                        return dose_rate * exposure
                except:
                        logger.error("Unable to calculate dose per frame")
                        
                        
        def calculate_exposure_via_raddose3d(self,
                                             total_dose,
                                             flux_reading=False,
                                             energyInEv=False,
                                             beamsize_x=False,
                                             beamsize_y=False,
                                             dose_method='Max Dose'):
    
                if energyInEv == False:
                        energyInEv = self.actual_energy()
                if flux_reading == False:
                        flux_reading = int(flux.rawGetPosition())
                        
                try:
                        if beamsize_x == False or beamsize_y == False:
                                beamsize_x, beamsize_y = fswitch_tool.calc_beamsize_from_lenses()
                        import raddose3d_queries
                        self.raddose_client = raddose3d_queries.Raddose_API_client()
                        energyInKev = energyInEv /1000


                        return self.raddose_client.get_exposure_with_assumptions(total_dose=total_dose,
                                                                            flux=flux_reading, 
                                                                            beamsize_x=beamsize_x, 
                                                                            beamsize_y=beamsize_y, 
                                                                            energy_kev=energyInKev)
                        
                except Exception as e:
                        print('Failed to exposure dose via raddose3d with error %s' %(e))
                        return 0.0
    
