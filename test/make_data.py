import os
import datetime
import polars as pl
import numpy as np


WDIR = 'samples'
ε = 1e-12


t0 = datetime.datetime(2025, 6, 6, 12, 0, 0)
for i_file in range(3):
    t1 = t0 - datetime.timedelta(days=7) + datetime.timedelta(minutes=i_file*10)
    filename = f'{WDIR}/{t1.strftime("%Y-%m-%d_%H-%m-%S")}_data_{i_file+1}.csv'
    print(f'Creating <{filename}>...')

    data_freq, data_power, data_xparam = (mesh.ravel() for mesh in np.meshgrid(
        np.arange(1e9, 20e9+ε, 0.1e9), # frequency
        np.arange(-30, +10+ε, 10), # power
        np.arange(-1, +1+ε, 0.2), # X
    ))
    data_p_meas = data_power + 5 - np.sqrt(data_freq/1e9) + 0.9*data_xparam + np.random.normal(0, 0.02, data_freq.shape)
    df = pl.DataFrame({
        'f/GHz': data_freq/1e9,
        'PSet/dBm': data_power,
        'XParam': data_xparam,
        'PMeas/dBm': data_p_meas,
    })
    with open(filename, 'w') as fp:
        fp.write('# automatically generated file for testing purposes\n')
        df.write_csv(fp, separator=';')

print('Done.')
