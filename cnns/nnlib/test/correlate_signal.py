from numpy.fft import fft, ifft
from scipy.stats.mstats import zscore

from nnlib.load_time_series import load_data
from nnlib.utils.general_utils import *

np.random.seed(237)
print("correlate signal")

# dataset = "Adiac"
dataset = "50words"
# dataset = "Earthquakes"
# dataset = "Herring"
# dataset = "InlineSkate"
datasets = load_data(dataset)

train_set_x, train_set_y = datasets[0]
valid_set_x, valid_set_y = datasets[1]

x = train_set_x[0]
x = np.array(x, dtype=np.float64)

repetitions = 1
exec_number = 1

b = np.array([0])

stride = 1

timings = []
errors = []


def correlate_signal(x, energy_rate=None):
    plot_signal(x, "input value")
    x_len = len(x)
    print("input x size: ", len(x))
    # fft_size = 1 << (2 * x_len - 1).bit_length()
    fft_size = next_power2(x_len)
    print("fft size: ", fft_size)
    xfft = fft(x, fft_size)
    print("xfft: ", xfft)
    if energy_rate is not None:
        xfft = preserve_energy(xfft, energy_rate)
    cc = ifft(xfft)
    cc = np.concatenate((cc[-(x_len - 1):], cc[:x_len]))
    return_value = np.real(cc)
    return_value = return_value[-x_len:]
    plot_signal(return_value, "returned value")
    return return_value


def preserve_energy(xfft, energy_rate=None):
    if energy_rate is not None:
        initial_length = len(xfft)
        half_fftsize = initial_length // 2
        print("first half: ", xfft[0:half_fftsize])
        print("second half: ", np.conj(np.flip(xfft[half_fftsize:], axis=0)))
        first_half = xfft[1:half_fftsize]
        second_half = np.conj(np.flip(xfft[half_fftsize+1:], axis=0))
        print("are close: ", np.allclose(first_half, second_half, rtol=1.e-14, atol=1.e-13))
        for i in range(10):
            print("are the same: ", first_half[i], second_half[i], first_half[i] == second_half[i])
        print("rel error: ", rel_error(first_half, second_half))
        print("abs error: ", abs_error(first_half, second_half))
        xfft = xfft[0:half_fftsize]
        squared_abs = np.abs(xfft) ** 2
        full_energy = np.sum(squared_abs)
        current_energy = 0.0
        preserved_energy = full_energy * energy_rate
        index = 0
        while current_energy < preserved_energy and index < len(squared_abs):
            current_energy += squared_abs[index]
            index += 1
        print("index: ", index)
        xfft = np.concatenate((xfft[:index], np.zeros(initial_length - index)))
    return xfft


for energy_rate in [0.99]:  # None, 1.0,
    print("energy rate: ", energy_rate)
    returned_signal = correlate_signal(x, energy_rate=energy_rate)
    plot_signals(x, returned_signal, title="Dataset: " + dataset)
    # print("zscore rel error input output signal float32: ", rel_error(np.array(zscore(x), dtype=np.float32),
    #                                                            np.array(zscore(returned_signal), dtype=np.float32)))
    # print("zscore rel error input output signal float64: ", rel_error(np.array(zscore(x), dtype=np.float64),
    #                                                            np.array(zscore(returned_signal), dtype=np.float64)))
    #
    # print("zscore abs error input output signal float64: ", abs_error(np.array(zscore(x), dtype=np.float64),
    #                                                            np.array(zscore(returned_signal), dtype=np.float64)))


    print("rel error input output signal float32: ", rel_error(np.array(zscore(x), dtype=np.float32),
                                                               np.array(zscore(returned_signal), dtype=np.float32)))
    print("rel error input output signal float64: ", rel_error(np.array(zscore(x), dtype=np.float64),
                                                               np.array(zscore(returned_signal), dtype=np.float64)))

    print("abs error input output signal float64: ", abs_error(np.array(zscore(x), dtype=np.float64),
                                                               np.array(zscore(returned_signal), dtype=np.float64)))
