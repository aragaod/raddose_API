import math

from gda.configuration.properties.LocalProperties import isDummyModeEnabled
from gda.factory import Finder
from gdascripts.parameters import beamline_parameters
from gda.util import QuantityFactory
from org.slf4j import LoggerFactory
from gda.epics import LazyPVFactory
from com.google.common.base import Optional
from javax.measure.unit import SI
import fswitch as fswitch_tool

logger = LoggerFactory.getLogger("FluxScannable")

flux_ce_converter = Finder.getInstance().find("flux_ce_converter")
flux_i0_converter = Finder.getInstance().find("flux_i0_converter")

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

flux = Finder.getInstance().find("flux")

USE_I0_FROM_LOOKUP_TABLE_IF_REAL_I0_IS_LOW = False

jythonNameMap = beamline_parameters.JythonNameSpaceMapping()

dose_rate = Finder.getInstance().find("dose_rate")
#dose_rate_calculator = jythonNameMap.dose_rate_calculator
dose_rate_calculator = Finder.getInstance().find("dose_rate_calculator")

def actual_flux():
	eh_shutter_state = eh_shutter_status_pv.get()
	eh_shutter_open = (eh_shutter_state == 1)
	reading = 0.0
	if eh_shutter_open:
		reading = read_flux()
	return reading


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
	
	threshold = 1e-12
	if i0_reading < threshold:
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
	i0_in_amps = i0_quantity.doubleValue(SI.AMPERE)
	i0_in_ua = i0_in_amps * 1e6
	
	logger.debug("at %d eV expected i0 is %.10f uA" % (energy, i0_in_ua))
	return i0_in_ua

def predicted_flux_by_aperture(energy, transmission, aperture_label):
	params = beamline_parameters.Parameters()
	flux_scale_factor = params['flux_scale_factor']
	aperture_factor = _get_aperture_factor(aperture_label)
	scale_factor = aperture_factor*float(flux_scale_factor)
        pd = predicted_flux(energy, transmission, scale_factor)

        #****START OF SECTION TO REMOVE LATER
        #Adding fudge factor that will mean the results is not longer a predicted flux but a fix for an error under 
        #/dls_sw/i04/software/gda_versions/gda_9_14/workspace_git/gda-mx.git/plugins/uk.ac.gda.px/src/gda/px/flux/DoseCalculator.java
        #where beamsize is being taken from the appertures rather than the lenses. When we edit the java we should fix this

        #****Reminder to remove import fswitch when the line below is removed****
        Xsize, Ysize = fswitch_tool.calc_beamsize_from_lenses()
        #print "beamX,beamY"
        #print  Xsize, Ysize

        #area = PI * X in mm / 2 * Y in mm / 2
        beamareainsquaremm = float(3.1416*(Xsize/1e3/2)*(Ysize/1e3/2))
        #print beamareainsquaremm

        fudge_factor = 0.0314 / beamareainsquaremm

        #****END OF SECTION REMOVE LATER but dont forget to remove fudge factor below

	return pd * fudge_factor

def predicted_flux(energy, transmission, flux_scale_factor, debug=False):
	# transmission supplied is in range 0..100
	intensity = _predicted_i0(energy)
	if debug:
		print ("intensity: %g" % (intensity))
	
	# adjust intensity value to take transmission into account
	intensity *= transmission/100.0
	logger.debug("with %.2f transmission intensity is reduced to %.2f" % (transmission, intensity))
	predicted_flux = _flux(intensity, energy, flux_scale_factor)
	if debug:
		print ("predicted flux: %g" % (predicted_flux))
	
	return _flux(intensity, energy, flux_scale_factor)

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
			print ("calib_flux : %g" % (calib_flux))

		aperture_scale_factor = get_current_aperture_factor()
		if debug:
			print ("aperture scale factor : %g" % (aperture_scale_factor))
			print ("flux scale factor : %g" % (flux_scale_factor))
		
		calc_flux = calib_flux * aperture_scale_factor * flux_scale_factor
		if debug:
			print ("calc_flux : %g" % (calc_flux))
	
	except:
		# return zero flux on error
		calc_flux = 0.0
	
	return calc_flux


def calculate_current_flux():
	try:
		current_flux = actual_flux()
		flux.moveTo(current_flux)
	except:
		if not isDummyModeEnabled():
			flux.moveTo(0.0)
			logger.debug("Unable to calculate flux")

def get_current_flux():
	try:
		return Optional.of(actual_flux())
	except:
		logger.error("Unable to record flux for data collection")
		return Optional.absent()

def _dose_rate(flux,muAbs,beamWidthInMicrons,beamHeightInMicrons,energyInEv):
	rate = dose_rate_calculator.calculateDosePerSecond(flux,muAbs,beamWidthInMicrons,beamHeightInMicrons,energyInEv)
	return rate

def actual_dose_rate():
	energy = actual_energy()
	muAbsValue = _muAbs(energy)
	# get beam size
	beamSizeXObject = Finder.getInstance().find("beamSizeX")
	beamSizeYObject = Finder.getInstance().find("beamSizeY")
	realBeamSizeX = beamSizeXObject.getPosition()
	realBeamSizeY = beamSizeYObject.getPosition()
	flux_reading = flux.rawGetPosition()
	return _dose_rate(flux_reading,muAbsValue,realBeamSizeX,realBeamSizeY,energy)
			
def calculate_current_dose_rate():
	try:
		current_dose_rate = actual_dose_rate() # rate in MGy/s
		dose_rate.moveTo(current_dose_rate)
		return current_dose_rate
	except:
		logger.error("Unable to calculate dose rate")

def actual_energy():
	jythonNameMap = beamline_parameters.JythonNameSpaceMapping()
	# get current energy
	bl = jythonNameMap.bl
	energy = bl()
	return energy

def _muAbs(energy):
	logger.debug("current energy is %d eV" % energy)
	muAbsObject = Finder.getInstance().find("muAbs")
	if (muAbsObject.isUseDefault()):
		muAbsValue = dose_rate_calculator.muAbsForAverageSample(energy)
		muAbsObject.moveTo(muAbsValue)
	else:
		muAbsValue = muAbsObject.getPosition()
	logger.debug("Using muAbs = %g" % muAbsValue)
	return muAbsValue
	
def calculate_current_dose_per_frame(exposure):
	try:
		dose_rate = calculate_current_dose_rate()
		return dose_rate * exposure
	except:
		logger.error("Unable to calculate dose per frame")


def _get_i_bounds(i_read,e_col,debug=False):
	i_lower = 0.0
	i_upper = 0.0
	i_key = 0.0
	j_key = 0.0
	try:
		# The required configured LookupTable (MXGDA-2681)
		lut = Finder.getInstance().find("flux_xbpm2_calibration")
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


def _interpolate(d_val,d_start,d_end,r_start,r_end):
	if abs(d_end-d_start) < 1e-12:
		return r_start
	fraction = (d_val-d_start) / (d_end-d_start)
	interval = fraction * (r_end-r_start)
	return r_start + interval


def _lookup_flux(i_read,energy,debug=False):
	e_reading = energy/1000.0
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

def calculate_dose_via_raddose3d(total_exposure,flux,energy, beamsize_x=False, beamsize_y=False,dose_method='Max Dose'):
        '''
        Development in progress by David Aragao 2020 April 11: using Raddose3d via a RESTfull API to calculate dose deposited on a protein crystal
        '''
        try:
                if beamsize_x == False or beamsize_y == False:
                        beamsize_x, beamsize_y = fswitch_tool.calc_beamsize_from_lenses()
                import raddose3d_queries
                raddose_client = raddose3d_queries.Raddose_API_client()
                return raddose_client.get_dose_with_assumptions(total_exposure_time=total_exposure,flux=flux, beamsize_x=beamsize_x, beamsize_y=beamsize_y, energy_kev=energy)
        except Exception as e:
                print('Failed to calculate dose via raddose3d with error %s' %(e))
                return 0.0

# Alias for convenience
dose = dose_rate_calculator
