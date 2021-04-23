from gda.factory import Finder
from org.slf4j import LoggerFactory

from gdascripts.parameters import beamline_parameters

jythonNameMap = beamline_parameters.JythonNameSpaceMapping()

import fswitch as fswitch_tool
import math
from irradiation_utils import kilo_electron_volts_of, square_millimetre_ellipse_area

logger = LoggerFactory.getLogger(__name__)

flux_scannable = Finder.find("flux")
ui_dose_rate_scannable = Finder.find("dose_rate")


def actual_energy():
	# get current energy
	bl = jythonNameMap.bl
	energy = bl()
	return energy


def read_latest_flux():
	return flux_scannable.rawGetPosition()


def latest_flux_as_rounded_int():
	rounded_flux = round(read_latest_flux())
	return int(rounded_flux)


class DoseUtils():

	def __init__(self):
		self.actual_energy = actual_energy


	def _dose_rate_via_mu_absorption(self, flux, mu_absorption, beam_width_in_microns, beam_height_in_microns, energy_in_electron_volts):

		energy_kilo_electron_volts = kilo_electron_volts_of(energy_in_electron_volts)
		beam_area_square_mm = square_millimetre_ellipse_area(beam_width_in_microns, beam_height_in_microns)
		rate_conversion_constant = 1.23e-16 # 1.23e-10 divided by 1e6 for Gy to MGy

		return rate_conversion_constant * mu_absorption * flux * energy_kilo_electron_volts / beam_area_square_mm


	def calculate_dose_rate(self, flux, beam_width_in_microns, beam_height_in_microns, energy_in_electron_volts, method='mu_absorption'): #Options are mu_absorption or raddose

		if method == "mu_absorption":
			mu_absorption = self.calculate_mu_absorption(energy_in_electron_volts)
			return self._dose_rate_via_mu_absorption(flux, mu_absorption, beam_width_in_microns, beam_height_in_microns, energy_in_electron_volts)
		elif method == "raddose":
			flux=round(flux)
			unit_time = 1.0
			return self.calculate_dose_via_raddose3d(unit_time, flux, energy_in_electron_volts, beam_width_in_microns, beam_height_in_microns)
		else:
			logger.debug("Cannot calculate dose rate using unrecognised method %s: Only mu_absorption or raddose are recognised. " % method)
			return 0.0


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
			flux_reading = latest_flux_as_rounded_int()
		try:
			if beamsize_x == False or beamsize_y == False:
				beamsize_x, beamsize_y = fswitch_tool.calc_beamsize_from_lenses()

			import raddose3d_queries
			raddose_client = raddose3d_queries.Raddose_API_client()

			return raddose_client.get_dose_with_assumptions(total_exposure_time=total_exposure,
															flux=flux_reading,
															energy_kev=kilo_electron_volts_of(energy),
															beamsize_x=beamsize_x,
															beamsize_y=beamsize_y,
															dose_method=dose_method)

		except Exception as e:
			print('Failed to calculate dose via raddose3d with error %s' %(e))
			return 0.0


	def actual_dose_rate(self,method='muAbs'):

		energy = self.actual_energy()

		# get beam size
		beam_size = beamline_parameters.JythonNameSpaceMapping().beam_size
		real_beam_size_x, real_beam_size_y = beam_size.calc_beamsize_from_lenses()

		flux_reading = read_latest_flux()
		return self.calculate_dose_rate(flux_reading, real_beam_size_x, real_beam_size_y, energy, method)


	def update_current_dose_rate(self, method='mu_absorption'): #Options are mu_absorption or raddose
		current_dose_rate = self.calculate_current_dose_rate(method)
		try :
			ui_dose_rate_scannable.moveTo(current_dose_rate)
		except:
			logger.error("Unable to update dose rate")


	def calculate_current_dose_rate(self, method='mu_absorption'): #Options are mu_absorption or raddose
		try:
			current_dose_rate = self.actual_dose_rate(method)
			return current_dose_rate
		except:
			logger.error("Unable to calculate dose rate using method %s " % method)
			return 0.0


	def calculate_mu_absorption(self,energy_in_electron_volts):
		energy_kilo_electron_volts_ceiling =  60 # above 60 keV the exponential return is negligible
		absorption_pedestal = 0.074 # lowest absorption possible

		energy_k_electron_volts = kilo_electron_volts_of(energy_in_electron_volts)
		if(energy_k_electron_volts > energy_kilo_electron_volts_ceiling):
			return absorption_pedestal

		natural_energy_scaling = -1.0 / 2.273; # scales the exponential to the absorption curve energy scale
		exponent = energy_k_electron_volts * natural_energy_scaling # applies the rescaling to the input energy
		absorption_scaling = 29.3 # rescales the exponential to give the absorption factor
		return absorption_pedestal + absorption_scaling * math.exp(exponent)


	def calculate_current_dose_per_frame(self, exposure):
		try:
			dose_rate = self.calculate_current_dose_rate()
			return dose_rate * exposure
		except:
			logger.error("Unable to calculate dose per frame")
			return 0.0


	def calculate_exposure_via_raddose3d(self,
										total_dose,
										flux_reading=False,
										energy_in_electron_volts=False,
										beamsize_x=False,
										beamsize_y=False,
										dose_method='Max Dose'):

		if energy_in_electron_volts == False:
			energy_in_electron_volts = self.actual_energy()

		if flux_reading == False:
			flux_reading = latest_flux_as_rounded_int()

		try:
			if beamsize_x == False or beamsize_y == False:
				beamsize_x, beamsize_y = fswitch_tool.calc_beamsize_from_lenses()

			import raddose3d_queries
			self.raddose_client = raddose3d_queries.Raddose_API_client()

			return self.raddose_client.get_exposure_with_assumptions(total_dose=total_dose,
																	flux=flux_reading, 
																	beamsize_x=beamsize_x, 
																	beamsize_y=beamsize_y, 
																	energy_kev=kilo_electron_volts_of(energy_in_electron_volts))

		except Exception as e:
			print('Failed to calculate exposure dose via raddose3d: Error %s' %(e))
			return 0.0
