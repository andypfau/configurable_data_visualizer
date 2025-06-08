import os
import datetime
import polars as pl
import numpy as np


WDIR = 'samples'
ε = 1e-12


t0 = datetime.datetime(2025, 6, 6, 12, 0, 0)
for i_file in range(5):
    t1 = t0 - datetime.timedelta(days=7) + datetime.timedelta(minutes=i_file*10)
    filename = f'{WDIR}/{t1.strftime("%Y-%m-%d_%H-%m-%S")}_data_{i_file+1}.csv'
    print(f'Creating <{filename}>...')

    freq_hz, p_target_dbm, comp = (mesh.ravel() for mesh in np.meshgrid(
        np.round(np.arange(1e9, 10e9+ε, 100e6), 3), # frequency
        np.round(np.arange(-30, +10+ε, 10), 3), # power
        np.round(np.arange(-0.01, +0.01+ε, 0.002), 5), # X
    ))
    
    def add_in_db(a, b):
        return 10*np.log10(10**(a/10) + 10**(b/10))
    def calc_intermod(fundamental_dbm, toi_dbm):
        return 3 * fundamental_dbm - 2 * toi_dbm
    def calc_toi(fundamental1_dbm, fundamental2_dbm, intermod1_dbm, intermod2_dbm):
        toi1 = 2 * fundamental1_dbm + fundamental2_dbm - intermod1_dbm
        toi2 = 2 * fundamental2_dbm + fundamental1_dbm - intermod2_dbm
        return np.maximum(toi1, toi2)
    
    def calc_fundamental_and_intermod(level_dbm, sat_level_dbm, compensation_c3: float = 1):
        
        level_mw = 10**(level_dbm/10)
        sat_level_mw = 10**(sat_level_dbm/10)

        def compress(x):
            return np.tanh(x / sat_level_mw) * sat_level_mw
        
        compressed_level_mw = compress(level_mw)
        c3 = (compressed_level_mw - level_mw) / (compressed_level_mw**3)
        
        fundamental_level_mw = compress(level_mw + 9/4*c3*level_mw**3)
        intermod_level_mw = compress(3/4*c3*level_mw**3) - compensation_c3*fundamental_level_mw**3

        fundamental_level_dbm = 10*np.log10(np.abs(fundamental_level_mw))
        intermod_level_dbm = 10*np.log10(np.abs(intermod_level_mw))
        
        return fundamental_level_dbm, intermod_level_dbm

    uncertainty_db = 0.1
    p_noisefloor_dbm = np.random.normal(-90, 1, freq_hz.shape)
    p_input_dbm = p_target_dbm - np.sqrt(freq_hz/1e9)*0.01
    p_fundamental_dbm, p_intermod_dbm = calc_fundamental_and_intermod(p_input_dbm, +10, compensation_c3=comp)
    
    p_noisefloor_meas_dbm = p_noisefloor_dbm + np.random.normal(0, uncertainty_db, freq_hz.shape)
    p_fundamental1_meas_dbm = add_in_db(p_noisefloor_dbm, p_fundamental_dbm) + np.random.normal(0, uncertainty_db, freq_hz.shape)
    p_fundamental2_meas_dbm = add_in_db(p_noisefloor_dbm, p_fundamental_dbm) + np.random.normal(0, uncertainty_db, freq_hz.shape)
    p_intermod1_meas_dbm = add_in_db(p_noisefloor_dbm, p_intermod_dbm) + np.random.normal(0, uncertainty_db, freq_hz.shape)
    p_intermod2_meas_dbm = add_in_db(p_noisefloor_dbm, p_intermod_dbm) + np.random.normal(0, uncertainty_db, freq_hz.shape)
    compr_meas_db = p_target_dbm - np.mean([p_fundamental1_meas_dbm, p_fundamental2_meas_dbm], axis=0)
    toi_meas_dbm = calc_toi(p_fundamental1_meas_dbm, p_fundamental2_meas_dbm, p_intermod1_meas_dbm, p_intermod2_meas_dbm)
    snr_meas_db = np.minimum(p_intermod1_meas_dbm, p_intermod2_meas_dbm) - p_noisefloor_meas_dbm
    
    df = pl.DataFrame({
        'f/GHz': freq_hz/1e9,
        'PTarget/dBm': p_target_dbm,
        'Compensation': comp,
        'Fund1Meas/dBm': p_fundamental1_meas_dbm,
        'Fund2Meas/dBm': p_fundamental2_meas_dbm,
        'Imd1Meas/dBm': p_intermod1_meas_dbm,
        'Imd2Meas/dBm': p_intermod2_meas_dbm,
        'Noisefloor/dBm': p_noisefloor_meas_dbm,
        'ToiMeas/dBm': toi_meas_dbm,
        'ComprMeas/dB': compr_meas_db,
        'SnrMeas/dB': snr_meas_db,
    })
    with open(filename, 'w') as fp:
        fp.write('# programmatically generated file for testing purposes\n')
        df.write_csv(fp, separator=';')

print('Done.')
