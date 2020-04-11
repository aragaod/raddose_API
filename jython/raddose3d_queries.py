import json
import httplib

import flux_utils
import logging


# GDA Jyhton code to interact with a RESTfull API that runs raddose3d to obtain dose
# v0.1 by DGA, 2020/04/11 during SARS-Cov2 pandemic

class Raddose_API_client(object):
    '''
    API client to the RESTfull APi that runs raddose3d and gets dose calculations back

    '''

    def __init__(self):

        ###start a log file
        self.logger = logging.getLogger('Raddose3d_client')
        if len(self.logger.handlers) < 1:
            formatter = logging.Formatter('%(asctime)s: %(levelname)s: %(module)s: %(message)s',"[%Y-%m-%d %H:%M:%S]")
            streamhandler = logging.StreamHandler()
            streamhandler.setFormatter(formatter)
            self.logger.addHandler(streamhandler)

        self.setLogLevel('info')


        self.raddose3d_api_server_url = 'i04-ws004.diamond.ac.uk'
        self.raddose3d_api_server_port = 8000

        self.raddose3d_api_url = '/api/v1.0/getdose?flux={flux}&beam_size_x={beamsize_x}&beam_size_y={beamsize_y}&xtal_size_x={xtalsize_x}&xtal_size_y={xtalsize_y}&xtal_size_z={xtalsize_z}&oscillation_start={oscillation_start}&oscillation_end={oscillation_end}&total_exposure_time={total_exposure_time}&energy_kev={energy_kev}'


    def setLogLevel(self, level='info'):
        level = str(level).lower()
        levels = {'none': None,
                  'debug': logging.DEBUG,
                  'info': logging.INFO,
                  'warning': logging.WARNING,
                  'error': logging.ERROR,
                  'critical': logging.CRITICAL}
        if level in levels.keys():
            if level == 'none':
                self.logger.info('Disabling logging')
                logging.disable(logging.CRITICAL)
            else:
                logging.disable(logging.NOTSET)
                self.logger.setLevel(levels[level])
                self.logger.info('Set log level to '+level)
        else:
            self.logger.error('Log level should be: '+','.join(levels.keys()))

    def get_dose(self,flux,beamsize_x,beamsize_y,xtalsize_x, xtalsize_y,xtalsize_z, oscillation_start, oscillation_end, total_exposure_time,energy_kev):
        input_parameters = {'flux': flux, 'beamsize_x': beamsize_x,'beamsize_y':beamsize_y,'xtalsize_x':xtalsize_x,'xtalsize_y':xtalsize_y,'xtalsize_z':xtalsize_z,'oscillation_start': oscillation_start,'oscillation_end': oscillation_end, 'energy_kev': energy_kev,'total_exposure_time':total_exposure_time}
        try:
            self.conn = httplib.HTTPConnection(host=self.raddose3d_api_server_url,port=self.raddose3d_api_server_port)
            self.conn.set_debuglevel(0)
            self.conn.request('GET', self.raddose3d_api_url.format(**input_parameters))
            self.response = self.conn.getresponse()
            self.data = json.loads(self.response.read())
            self.conn.close()
            if self.response.status == 200 and self.response.reason == 'OK':
                self.logger.debug('Got correct HTTPS code from querying raddose3d API')
                self.logger.debug(self.data)
                return self.data
            else:
                self.logger.warning('Failed to query raddose API')
                return False
                
        except Exception as  e:
            self.logger.warning('query to raddose API failed with error: %s' %(e))
            return False

    def get_dose_with_assumptions(self,total_exposure_time,flux,energy_kev, beamsize_x,beamsize_y,dose_method='Max Dose'):
        input_parameters = {'total_exposure_time':total_exposure_time,'flux': flux, 'beamsize_x': beamsize_x,'beamsize_y':beamsize_y,'xtalsize_x':beamsize_x,'xtalsize_y':beamsize_y,'xtalsize_z':beamsize_y,'oscillation_start': 0.0,'oscillation_end': 360.0, 'energy_kev': energy_kev}
        return self.get_dose(**input_parameters)[dose_method]

#raddose_test = Raddose_API_client()
