import math, json

from gda.configuration.properties.LocalProperties import isDummyModeEnabled
from gda.factory import Finder
from gdascripts.parameters import beamline_parameters
from gda.util import QuantityFactory
from org.slf4j import LoggerFactory
from gda.epics import LazyPVFactory
from com.google.common.base import Optional # TODO replace with java Optional, widely used by many scripts via get_current_flux
from tec.units.indriya.unit import Units

from dose_utils import DoseUtils
from irradiation_utils import kilo_electron_volts_of

logger = LoggerFactory.getLogger("FluxScannable")

flux_ce_converter = Finder.find("flux_ce_converter")
flux_i0_converter = Finder.find("flux_i0_converter")

dummy = True if isDummyModeEnabled() else False
if dummy:
	class ShutterStatusPv(object):
		def get(self):
			return 0
	eh_shutter_status_pv = ShutterStatusPv()
else:
	i0_gain_pv_template = "BL04I-EA-I0M-01:%s:GAIN"
	i0_upper_gain_pv_name = i0_gain_pv_template % "UPPER"
	i0_lower_gain_pv_name = i0_gain_pv_template % "LOWER"
	i0_upper_gain_pv = LazyPVFactory.newReadOnlyStringFromEnumPV(i0_upper_gain_pv_name)
	i0_lower_gain_pv = LazyPVFactory.newReadOnlyStringFromEnumPV(i0_lower_gain_pv_name)

	eh_shutter_status_pv_name = "BL04I-PS-SHTR-01:STA"
	eh_shutter_status_pv = LazyPVFactory.newIntegerFromEnumPV(eh_shutter_status_pv_name)

USE_I0_FROM_LOOKUP_TABLE_IF_REAL_I0_IS_LOW = False

# access scannables which track live beam status
flux_scannable = Finder.find("flux")
flux_density_scannable = Finder.find("flux_density")
beam_size_x_scannable = Finder.find("beamSizeX")
beam_size_y_scannable = Finder.find("beamSizeY")
dose_rate = Finder.find("dose_rate")

jythonNameMap = beamline_parameters.JythonNameSpaceMapping()

EQUALITY_THRESHOLD = 1.0e-12
MICRO_PER_UNIT = 1.0e6
FULL_TRANSMISSION = 100.0

def _interpolate(d_val,d_start,d_end,r_start,r_end):
	if abs(d_end-d_start) < EQUALITY_THRESHOLD:
		return r_start
	fraction = (d_val-d_start) / (d_end-d_start)
	interval = fraction * (r_end-r_start)

	return r_start + interval


def actual_flux():
	eh_shutter_state = eh_shutter_status_pv.get()
	eh_shutter_open = (eh_shutter_state == 1)
	reading = 0.0
	if eh_shutter_open:
		reading = read_flux()
	return reading


def actual_energy():
	# get current energy
	bl = jythonNameMap.bl
	energy = bl()
	return energy


def read_flux(debug=False):

	energy = actual_energy()
	# get current i0 reading
	i0 = jythonNameMap.i0 # reads XBPM2 intensity
	i0_reading = i0()

	if debug:
		message = "actual XBPM2 reading is %.10f" % i0_reading
		print(message)
		logger.debug(message)
	i0_reading = max(0, i0_reading) # * i0_multiplier

	if i0_reading < EQUALITY_THRESHOLD:
		i0_reading = 0.0

	if debug:
		message = "i0 %g" % i0()
		print(message)

		message = "adjusted XBPM2 reading is %g" % i0_reading
		logger.debug(message)
		print(message)

	# actual flux on sample is scaled by aperture or focal size - often beamline specific
	flux_scale_factor = get_flux_scale_factor()
	flux_reading = _flux(i0_reading, energy, flux_scale_factor, debug)

	if debug:
		message =  "flux reading %g" % flux_reading
		print message

	return flux_reading


def _predicted_i0(energy):

	# get expected intensity reading for specified energy
	energyEV = QuantityFactory.createFromObject(energy, QuantityFactory.createUnitFromString("eV"))
	flux_i0_converter.reloadConverter()
	i0_quantity = flux_i0_converter.toTarget(energyEV)
	i0_in_amps = i0_quantity.doubleValue(Units.AMPERE)
	i0_in_ua = i0_in_amps * MICRO_PER_UNIT

	logger.debug("at %d eV expected i0 is %.10f uA" % (energy, i0_in_ua))
	return i0_in_ua


def predict_flux_by_beamsize(energy,transmission,x_size,y_size):
	#TODO in the future adjust scale factor based on beamsize
	scale_factor = 0.372

	#pd = predicted_flux(energy, transmission, scale_factor)
	pd = predict_flux_from_polynomial_fit(energy,y_size) #I04-521

	#To investigate applying a correction factor based on today's beam current energy
	#current_flux_is = actual_flux()
	#current_flux_should_be = predict_flux_for_current_settings()
	#ratio = current_flux_is / current_flux_should_be


	return pd


def predict_flux_from_polynomial_fit(energy_eV,y_size): #I04-521
	params = beamline_parameters.Parameters()
	if int(y_size) in [5,10,15,20,30,40,50,75,100] and 5999 < energy_eV < 18001 :
		poly = json.loads(params.__getitem__('flux_predict_polynomial_coeficients_%s' %(int(y_size))))
		return poly[0] * pow(energy_eV,4) + poly[1] * pow(energy_eV,3) + poly[2] * pow(energy_eV,2) + poly[3] * pow(energy_eV,1) + poly[4]
	else:
		return 0


def predict_flux_for_current_settings():
	energy = actual_energy()
	scale_factor = 0.372
	return predicted_flux(energy, FULL_TRANSMISSION, scale_factor)


def predicted_flux_by_aperture(energy, transmission, aperture_label):
	params = beamline_parameters.Parameters()
	flux_scale_factor = params['flux_scale_factor']
	aperture_factor = _get_aperture_factor(aperture_label)
	scale_factor = aperture_factor*float(flux_scale_factor)

	return predicted_flux(energy, transmission, scale_factor)


def predicted_flux(energy, transmission, flux_scale_factor, debug=False):
	# transmission supplied is in range 0..100
	intensity = _predicted_i0(energy)
	if debug:
		print ("intensity: %g" % (intensity))

	# adjust intensity value to account for transmission losses
	transmission_factor = transmission / FULL_TRANSMISSION
	intensity *= transmission_factor
	logger.debug("with %.2f transmission, intensity is reduced to %.2f" % (transmission, intensity))

	predicted_flux = _flux(intensity, energy, flux_scale_factor)
	if debug:
		print ("predicted flux: %g" % (predicted_flux))

	return predicted_flux


def _get_aperture_factor(aperture_label):
	params = beamline_parameters.Parameters()
	aperture_factor = float(params["flux_factor_" + aperture_label])
	logger.debug("aperture conversion factor for %s is %.2f" % (aperture_label, aperture_factor))
	return aperture_factor


def get_current_aperture_factor():
	from gdaserver import aperture
	return _get_aperture_factor(aperture())


def get_flux_scale_factor():
	''' flux_scale_factor is proportion of measured flux that impinges on the sample
	usually limited by focal size or aperture '''
	params = beamline_parameters.Parameters()
	flux_scale_factor = float(params["flux_scale_factor"])
	return flux_scale_factor


def _flux(intensity, energy, flux_scale_factor,debug=False):
	calc_flux = 0.0
	try:
		# MXGDA-2681 intensity = XBPM2 current for i04
		calib_flux = _lookup_flux(intensity,energy,debug)
		if debug:
			print ("calib_flux : %g" % calib_flux)

		aperture_scale_factor = get_current_aperture_factor()
		if debug:
			print ("aperture scale factor : %g" % aperture_scale_factor)
			print ("flux scale factor : %g" % flux_scale_factor)

		calc_flux = calib_flux * aperture_scale_factor * flux_scale_factor
		if debug:
			print ("calc_flux : %g" % calc_flux)

	except:
		# return zero flux on error
		calc_flux = 0.0

	return calc_flux


# see flux.xml : This function is used by "Flux", "Flux Density" and "Dose Rate" displays in upper GDA UI
def update_flux_dose_display_scannables():
	beam_flux = 0.0
	try:
		beam_flux = actual_flux()
	except:
		if not isDummyModeEnabled():
			logger.debug("Unable to read current flux level")

	update_current_flux_display(beam_flux)
	beam_flux_density = calculate_current_flux_density(beam_flux)
	update_current_flux_density_display(beam_flux_density)

	update_current_dose_rate() #I04-430

def update_current_flux_display(beam_flux):
	try:
		flux_scannable.moveTo(beam_flux)
	except:
		logger.debug("Unable to update flux display to %f " % beam_flux)


def update_current_flux_density_display(beam_flux_density):
	try:
		flux_density_scannable.moveTo(beam_flux_density)
	except:
		logger.debug("Unable to update flux density display %f " % beam_flux_density)


def update_current_dose_rate():
	try:
		dose_utils.update_current_dose_rate() #I04-430
	except:
		if not isDummyModeEnabled():
			logger.debug("Unable to update dose rate")


def calculate_current_flux_density(beam_flux):
	beam_area = _get_current_beam_area()
	if beam_area < EQUALITY_THRESHOLD:
		logger.debug("Flux density unavailable as beam area is invalid %f " % beam_area)
		return 0.0
	return beam_flux / beam_area


def _get_current_beam_area():
	beam_width_microns = beam_size_x_scannable.getPosition()
	beam_height_microns = beam_size_y_scannable.getPosition()
	from irradiation_utils import elliptical_area
	return elliptical_area(beam_width_microns,beam_height_microns)


def get_current_flux():
	try:
		return Optional.of(actual_flux())
	except:
		logger.error("Unable to record flux for data collection")
		return Optional.absent()


def actual_dose_rate():
	# get beam size x (in microns, width a.k.a. horizontal diameter)
	beam_width_microns = beam_size_x_scannable.getPosition()

	# get beam size y (in microns, height a.k.a. vertical diameter)
	beam_height_microns = beam_size_y_scannable.getPosition()

	flux_reading = flux_scannable.rawGetPosition()
	energy_in_electron_volts = actual_energy()
	return DoseUtils.calculate_dose_rate(flux_reading, beam_width_microns, beam_height_microns, energy_in_electron_volts)


# see flux.xml : This function is used by "Dose Rate" display in upper GDA UI
def calculate_current_dose_rate():
	try:
		current_dose_rate = actual_dose_rate() # rate in MGy/s
		dose_rate.moveTo(current_dose_rate)
		return current_dose_rate
	except:
		logger.error("Unable to calculate dose rate")


def _get_i_bounds(i_read,e_col,debug=False):
	i_lower = 0.0
	i_upper = 0.0
	i_key = 0.0
	j_key = 0.0
	try:
		# The required configured LookupTable (MXGDA-2681)
		lut = Finder.find("flux_xbpm2_calibration")
	except:
		pass # return zeroes

	if lut:
		keys = lut.getLookupKeys()
		size = len(keys)
		i_key = 0.0
		j_key = 0.0
		i_value = 0.0
		index = 0
		for key in keys:
			i_value = lut.lookupValue(key, e_col)

			if i_value < i_read:
				i_lower = max(i_lower,i_value)
				i_upper = max(i_upper,i_value)

			if i_value > i_read:
				i_upper = i_value

			if debug:
				print "%g %s key %g val %g (%g,%g)" % (i_read, e_col, key, i_value, i_lower, i_upper)

			if i_value > i_read:
				break;

			i_key = key
			j_key = keys[min(index+1,size)]
			index = index + 1

		if debug:
			print "i_read, (i_lower,i), (i_upper,j) : %g, (%g, %g), (%g, %g)" % (i_read, i_lower, i_key, i_upper, j_key)
	return i_lower, i_upper, i_key, j_key


def _lookup_flux(i_read,energy,debug=False):
	e_reading = kilo_electron_volts_of(energy)
	e_lower = min(max(math.floor(e_reading), 1.0), 29.0)
	e_upper = e_lower + 1.0

	e_lower_col = "%.1f" % e_lower
	e_upper_col = "%.1f" % e_upper

	e_lo_i_lo_bound, e_lo_i_hi_bound, key_e_lo_f_lo, key_e_lo_f_hi = _get_i_bounds(i_read,e_lower_col)
	e_hi_i_lo_bound, e_hi_i_hi_bound, key_e_hi_f_lo, key_e_hi_f_hi = _get_i_bounds(i_read,e_upper_col)

	i_lo = max(e_lo_i_lo_bound,e_hi_i_lo_bound)
	i_hi = min(e_lo_i_hi_bound,e_hi_i_hi_bound)

	if e_lo_i_lo_bound < e_hi_i_lo_bound:
		f_hi_i_lo = key_e_hi_f_lo
		f_lo_i_lo = _interpolate(i_lo,e_lo_i_lo_bound,e_lo_i_hi_bound,key_e_lo_f_lo,key_e_lo_f_hi)

	else:
		f_lo_i_lo = key_e_lo_f_lo
		f_hi_i_lo = _interpolate(i_lo,e_hi_i_lo_bound,e_hi_i_hi_bound,key_e_hi_f_lo,key_e_hi_f_hi)

	if e_lo_i_hi_bound < e_hi_i_hi_bound:
		f_lo_i_hi = key_e_lo_f_hi
		f_hi_i_hi = _interpolate(i_hi,e_hi_i_lo_bound,e_hi_i_hi_bound,key_e_hi_f_lo,key_e_hi_f_hi)

	else:
		f_hi_i_hi = key_e_hi_f_hi
		f_lo_i_hi = _interpolate(i_hi,e_lo_i_lo_bound,e_lo_i_hi_bound,key_e_lo_f_lo,key_e_lo_f_hi)

	if debug:
		print ("(i_lo,f_lo_i_lo) = (%g,%g)" % (i_lo,f_lo_i_lo))
		print ("(i_lo,f_hi_i_lo) = (%g,%g)" % (i_lo,f_hi_i_lo))
		print ("(i_hi,f_lo_i_hi) = (%g,%g)" % (i_hi,f_lo_i_hi))
		print ("(i_hi,f_hi_i_hi) = (%g,%g)" % (i_hi,f_hi_i_hi))

	f_e_calc_i_lo = _interpolate(e_reading,e_lower,e_upper,f_lo_i_lo, f_hi_i_lo)
	f_e_calc_i_hi = _interpolate(e_reading,e_lower,e_upper,f_lo_i_hi, f_hi_i_hi)

	if debug:
		print ("(f_e_calc_i_lo,f_e_calc_i_hi) = (%g,%g)" % (f_e_calc_i_lo,f_e_calc_i_hi))

	try:
		flux = _interpolate(i_read,i_lo,i_hi,f_e_calc_i_lo, f_e_calc_i_hi)
		if debug:
			print ("flux : %g" % (flux))

	except:
		flux = 0.0

	return flux


# Alias for convenience
dose_utils = DoseUtils()
