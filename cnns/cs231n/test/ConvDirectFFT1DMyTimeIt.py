# As usual, a bit of setup
from __future__ import print_function

from cs231n.layers import *
# from cs231n.fast_layers import conv_forward_fft

import time

from scipy import signal

import torch
import torch.nn.functional as F


def reshape(x):
    return x.reshape(1, 1, -1)


def rel_error(x, y):
    """ returns relative error """
    return np.max(np.abs(x - y) / (np.maximum(1e-8, np.abs(x) + np.abs(y))))


def abs_error(x, y):
    """ return the absolute error """
    return np.sum(np.abs(x - y))


print("timeit: simple direct and FFT convolution for 1D")

cuda_id = 2
device = torch.device("cuda:2")

np.random.seed(231)

num_channels = 1

input_size = 256
filter_size = 2

x = np.random.randn(input_size)
filters = np.random.randn(filter_size)

# b = np.random.randn(1)
b = np.array([0])

stride = 1

mode = "full"
if mode == "valid":
    padding = 0
elif mode == "full":
    padding = len(filters) - 1

exec_number = 10  # number which is the number of executions you'd like to run
repetitions = 200

# decorator - to time the functions with arguments
def wrapper(func, *args, **kwargs):
    def wrapped():
        return func(*args, **kwargs)

    return wrapped


def conv_naive():
    return conv_forward_naive_1D(reshape(x), reshape(filters), b, conv_param)[0]


def conv_fft():
    return conv_forward_fft_1D(reshape(x), reshape(filters), b, conv_param)[0]


def timeit(statement, number=1):
    t0 = time.time()
    for _ in range(number):
        result = statement()
    t1 = time.time()
    return t1 - t0, result


def timeitrep(statement, number=1, repetition=1):
    """
    Time the execution of the statement `number` of times and repeat it number of `repetitions`.
    The returned timing is the all recorded `repetitions` with discarded potential outliers with the highest and lowest
    times, then averaged. The statement is executed number of times for each repetition and for each repetition we
    record the result from the last run (for a given repetition). The result is averaged across all the repetitions.

    :param statement: statement to be executed
    :param number: number of runs in each repetitions
    :param repetition: how many time to repeat the experiment
    :return: averge timing (with min, max timings discarded), average value of the results (from each repetition, we
    record the last result, and then average the results).
    """
    timings = []
    results = []
    for _ in range(repetition):
        t0 = time.time()
        statement_result = None
        for _ in range(number):
            statement_result = statement()
        t1 = time.time()
        timings.append(t1 - t0)
        if len(timings) > 3:
            # remove the highest and the lowest time values
            timings.remove(max(timings))
            timings.remove(min(timings))
        results.append(statement_result)
    # meaned_results = np.mean(results, axis=0)
    return np.average(timings), statement_result


conv_param = {'stride': stride, 'pad': padding}
# conv_naive_time, result_naive = timeit(conv_naive, number=exec_number)
conv_naive_time, (result_naive, _) = timeit(
    wrapper(conv_forward_naive_1D, reshape(x), reshape(filters), b, conv_param),
    number=exec_number)
print("result naive: ", result_naive)
print("result naive shape: ", result_naive.shape)
print("conv naive time: ", conv_naive_time)
# conv_fft_time, result_fft = timeit(conv_fft, number=exec_number)
conv_fft_time, (result_fft, _) = timeit(wrapper(conv_forward_fft_1D, reshape(x), reshape(filters), b, conv_param),
                                        number=exec_number)
# print("result_fft: ", result_fft)
are_close = np.allclose(result_fft, result_naive)
print("conv fft time: ", conv_fft_time, ",are close: ", are_close, ", absolute error: ",
      np.sum(np.abs(result_fft - result_naive)), ", relative error: ", rel_error(result_fft, result_naive))
# print("abs: ", np.abs(result_fft - result_naive))
torch_time, result_torch = timeitrep(
            wrapper(F.conv1d, torch.from_numpy(reshape(x)), torch.from_numpy(reshape(filters)), None,
                    stride, padding, 1, 1),
            number=exec_number, repetition=repetitions)
result_torch = result_torch.numpy()
print("torch time: ", torch_time, ", abs error: ", abs_error(result_torch, result_naive))

# torch gpu
result_torch_gpu = np.zeros(result_torch.shape)
torch_gpu_time = 0
# let us run it only if CUDA is available
if torch.cuda.is_available():
    xtorch_gpu = torch.from_numpy(reshape(x))
    xtorch_gpu = xtorch_gpu.to(device=device)
    filterstorch_gpu = torch.from_numpy(reshape(filters))
    filterstorch_gpu = filterstorch_gpu.to(device=device)
    result_torch_gpu = np.zeros(result_torch.shape)
    result_torch_gpu = torch.from_numpy(result_torch_gpu)
    result_torch_gpu = result_torch_gpu.to(device=device)
    torch_gpu_time, result_torch_gpu = timeitrep(
        wrapper(F.conv1d, xtorch_gpu, filterstorch_gpu, None, stride, padding, 1, 1), number=exec_number, repetition=repetitions)
    result_torch_gpu = result_torch_gpu.to(device=torch.device("cpu")).numpy()
print("torch gpu time: ", torch_gpu_time, ", abs error: ", abs_error(result_torch_gpu, result_naive))
                                           
numpy_time, result_numpy = timeit(wrapper(np.correlate, x, filters, mode=mode), number=exec_number)
print("numpy time: ", numpy_time, ", abs error: ", abs_error(result_numpy, result_naive))
print("numpy result: ", result_numpy)
print("numpy result shape: ", result_numpy.shape)
scipy_time, result_scipy = timeit(wrapper(signal.correlate, x, filters, mode=mode), number=exec_number)
print("scipy time: ", scipy_time, ", abs error: ", abs_error(result_scipy, result_naive))
scipy_time, result_scipy = timeit(wrapper(signal.correlate, x, filters, mode=mode), number=exec_number)
print("scipy time: ", scipy_time, ", abs error: ", abs_error(result_scipy, result_naive))
scipy_time_fft, result_scipy_fft = timeit(wrapper(signal.correlate, x, filters, mode=mode, method="fft"),
                                          number=exec_number)
print("scipy time fft: ", scipy_time_fft, ", abs error fft: ", abs_error(result_scipy_fft, result_naive))

with open("results/conv_timimg" + time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime()) + ".csv", "w+") as out_file:
    out_file.write(
        "filter_size, naive time (sec), fft time (sec), fftw time (sec), torch time (sec), numpy time (sec), " +
        "scipy time (sec), scipy fft time (sec), " +
        "err naive, err fft, err fftw, err numpy, err scipy, err scipy fft\n")

    for filter_size in range(1, input_size):
        print("filter size: ", filter_size)
        filters = np.random.randn(filter_size)
        mode = "full"
        if mode == "valid":
            padding = 0
        elif mode == "full":
            padding = len(filters) - 1
        conv_param = {'stride': stride, 'pad': padding}
        conv_naive_time, (result_naive, _) = timeitrep(
            wrapper(conv_forward_naive_1D, reshape(x), reshape(filters), b, conv_param),
            number=exec_number, repetition=repetitions)
        conv_fft_time, (result_fft, _) = timeitrep(
            wrapper(conv_forward_fft_1D, reshape(x), reshape(filters), b, conv_param),
            number=exec_number, repetition=repetitions)
        conv_fftw_time, (result_fftw, _) = timeitrep(
            wrapper(conv_forward_fftw_1D, reshape(x), reshape(filters), b, conv_param),
            number=exec_number, repetition=repetitions)
        xtorch = torch.from_numpy(reshape(x))
        filterstorch = torch.from_numpy(reshape(filters))
        torch_time, result_torch = timeitrep(
            wrapper(F.conv1d, xtorch, filterstorch, None,
                    stride, padding, 1, 1),
            number=exec_number, repetition=repetitions)
        result_torch = result_torch.numpy()
        # be default it is the same timing (cpu, gpu)
        result_torch_gpu = np.zeros(result_torch.shape)
        result_torch_gpu = torch.from_numpy(result_torch_gpu)
        result_torch_gpu = result_torch_gpu.to(device=device)
        torch_gpu_time = 0
        # let us run it only if CUDA is available
        if torch.cuda.is_available():
            # creates a LongTensor and transfers it to GPU as torch.cuda.LongTensor
            xtorch_gpu = torch.from_numpy(reshape(x))
            xtorch_gpu = xtorch_gpu.to(device=device)
            filterstorch_gpu = torch.from_numpy(reshape(filters))
            filterstorch_gpu = filterstorch_gpu.to(device=device)
            torch_gpu_time, result_torch_gpu = timeitrep(
                wrapper(F.conv1d, xtorch_gpu, filterstorch_gpu, None,
                        stride, padding, 1, 1),
                number=exec_number, repetition=repetitions)
            # go back to cpu to display the results
            result_torch_gpu = result_torch_gpu.to(torch.device("cpu")).numpy()

        # conv_stanford_time, (result_stanford, _) = timeitrep(
        #     wrapper(conv_forward_fftw_1D, reshape(x), reshape(filters), b, conv_param),
        #     number=exec_number, repetition=repetitions)
        numpy_time, result_numpy = timeitrep(wrapper(np.correlate, x, filters, mode=mode), number=exec_number,
                                             repetition=repetitions)
        scipy_time, result_scipy = timeitrep(wrapper(signal.correlate, x, filters, mode=mode), number=exec_number,
                                             repetition=repetitions)
        scipy_fft_time, result_scipy_fft = timeitrep(wrapper(signal.correlate, x, filters, mode=mode, method="fft"),
                                                     number=exec_number, repetition=repetitions)
        # print("result naive shape: ", result_naive.shape)
        # print("result fft shape: ", result_fft.shape)
        # print("result torch shape: ", result_torch.shape)
        # print("result numpy shape: ", result_numpy.shape)
        # print("result scipy shape: ", result_numpy.shape)
        # print("result scipy fft shape: ", result_scipy_fft.shape)
        result = [filter_size, conv_naive_time, conv_fft_time, conv_fftw_time, torch_time, torch_gpu_time, numpy_time,
                  scipy_time,
                  scipy_fft_time,
                  abs_error(result_naive, result_naive),
                  abs_error(result_naive, result_fft),
                  abs_error(result_naive, result_fftw),
                  abs_error(result_naive, result_torch),
                  abs_error(result_naive, result_torch_gpu),
                  abs_error(result_naive, result_numpy),
                  abs_error(result_naive, result_scipy),
                  abs_error(result_naive, result_scipy_fft)]
        out_file.write(",".join([str(x) for x in result]) + "\n")