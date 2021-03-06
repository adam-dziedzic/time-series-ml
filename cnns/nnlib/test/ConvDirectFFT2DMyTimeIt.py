# As usual, a bit of setup
from __future__ import print_function

from nnlib.layers import *
from nnlib.fast_layers import conv_forward_fast

from nnlib.load_time_series import load_data

import time

from scipy import signal

import torch
import torch.nn.functional as F


def reshape(x):
    return x.reshape(1, 1, x.shape[0], x.shape[1])


def rel_error(x, y):
    """ returns relative error """
    return np.max(np.abs(x - y) / (np.maximum(1e-8, np.abs(x) + np.abs(y))))


def abs_error(x, y):
    """ return the absolute error """
    return np.sum(np.abs(x - y))


print("timeit: simple direct and FFT convolution for 1D")

cuda_id = 0
device = torch.device("conv1D_cuda")

np.random.seed(231)

# # dataset = "Adiac"
# dataset = "50words"
# # dataset = "Herring"
# # dataset = "InlineSkate"
# datasets = load_data(dataset)
#
# train_set_x, train_set_y = datasets[0]
# valid_set_x, valid_set_y = datasets[1]
# test_set_x, test_set_y = datasets[2]
#
# x = train_set_x[0]
# filter_size = 4
# full_filter = train_set_x[1]
# filters = full_filter[:filter_size]

num_channels = 1
input_size = 256
filter_size = 2
x = np.random.randn(input_size, input_size)
filters = np.random.randn(filter_size, filter_size)

input_size = len(x)

# b = np.random.randn(1)
b = np.array([0])

stride = 1

mode = "full"
if mode == "valid":
    padding = 0
elif mode == "full":
    padding = len(filters) - 1

exec_number = 1  # number which is the number of executions you'd like to run
repetitions = 10


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
    wrapper(conv_forward_naive, reshape(x), reshape(filters), b, conv_param),
    number=exec_number)
# print("result naive: ", result_naive)
print("result naive shape: ", result_naive.shape)
print("conv naive time: ", conv_naive_time)
# conv_fft_time, result_fft = timeit(conv_fft, number=exec_number)
conv_fft_time, (result_fft, _) = timeit(wrapper(conv_forward_fft, reshape(x), reshape(filters), b, conv_param),
                                        number=exec_number)

stanford_time, (result_stanford, _) = timeit(wrapper(conv_forward_fast, reshape(x), reshape(filters), b, conv_param),
                                             number=exec_number)
print("stanford time: ", stanford_time, ", abs error: ", abs_error(result_stanford, result_naive))

# print("result_fft: ", result_fft)
are_close_fft = np.allclose(result_fft, result_naive)
print("are close: ", are_close_fft)
print("conv fft time: ", conv_fft_time, ", abs error: ",
      np.sum(np.abs(result_fft - result_naive)), ", relative error: ", rel_error(result_fft, result_naive))
conv_fftw_time, (result_fftw, _) = timeit(wrapper(conv_forward_fftw, reshape(x), reshape(filters), b, conv_param),
                                          number=exec_number)
# print("result_fft: ", result_fft)
are_close_fftw = np.allclose(result_fftw, result_naive)
print("conv fftw time: ", conv_fftw_time, ",are close: ", are_close_fftw, ", absolute error: ",
      np.sum(np.abs(result_fftw - result_naive)), ", relative error: ", rel_error(result_fftw, result_naive))
# print("abs: ", np.abs(result_fft - result_naive))
torch_time, result_torch = timeitrep(
    wrapper(F.conv2d, torch.from_numpy(reshape(x)), torch.from_numpy(reshape(filters)), None,
            stride, padding, 1, 1),
    number=exec_number, repetition=repetitions)
result_torch = result_torch.numpy()
print("torch time: ", torch_time, ", abs error: ", abs_error(result_torch, result_naive))
scipy_time, result_scipy = timeit(wrapper(signal.correlate2d, x, filters, mode=mode), number=exec_number)
print("scipy time: ", scipy_time, ", abs error: ", abs_error(result_scipy, result_naive))
# scipy_time_fft, result_scipy_fft = timeit(wrapper(signal.correlate2d, x, filters, mode=mode, method="fft"),
#                                           number=exec_number)
# print("scipy time fft: ", scipy_time_fft, ", abs error fft: ", abs_error(result_scipy_fft, result_naive))
# numpy_time, result_numpy = timeit(wrapper(np.correlate, x, filters, mode=mode), number=exec_number)
# print("numpy time: ", numpy_time, ", abs error: ", abs_error(result_numpy, result_naive))
# print("numpy result: ", result_numpy)
# print("numpy result shape: ", result_numpy.shape)

with open("results/conv_timimg" + time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime()) + ".csv", "w+") as out_file:
    out_file.write(
        "filter_size, "
        "naive time (sec), " +
        "stanford time (sec), " +
        "fft time (sec), " +
        "fftw time (sec), " +
        "torch cpu time (sec), " +
        "torch gpu time (sec), " +
        "numpy time (sec), " +
        "scipy direct time (sec), " +
        "scipy fft time (sec), " +
        "scipy auto time (sec), " +
        "err naive, " +
        "err stanford, "
        "err fft, " +
        "err fftw, " +
        "err torch cpu, " +
        "err torch gpu, " +
        "err numpy, " +
        "err scipy direct, " +
        "err scipy fft, " +
        "err scipy auto" +
        "\n")

    for filter_size in range(1, input_size + 1):  # input_size
        print("filter size: ", filter_size)
        filters = np.random.randn(filter_size, filter_size)
        mode = "full"
        if mode == "valid":
            padding = 0
        elif mode == "full":
            padding = len(filters) - 1
        conv_param = {'stride': stride, 'pad': padding}
        reshaped_x = reshape(x)
        reshaped_filters = reshape(filters)
        conv_naive_time, (result_naive, _) = timeitrep(
            wrapper(conv_forward_naive, reshaped_x, reshaped_filters, b, conv_param),
            number=exec_number, repetition=repetitions)
        conv_stanford_time, (result_stanford, _) = timeitrep(
            wrapper(conv_forward_fast, reshaped_x, reshaped_filters, b, conv_param),
            number=exec_number, repetition=repetitions)
        conv_fft_time, (result_fft, _) = timeitrep(
            wrapper(conv_forward_fft, reshaped_x, reshaped_filters, b, conv_param),
            number=exec_number, repetition=repetitions)
        conv_fftw_time, (result_fftw, _) = timeitrep(
            wrapper(conv_forward_fftw, reshaped_x, reshaped_filters, b, conv_param),
            number=exec_number, repetition=repetitions)
        xtorch = torch.from_numpy(reshaped_x)
        filterstorch = torch.from_numpy(reshaped_filters)
        torch_time, result_torch = timeitrep(
            wrapper(F.conv2d, xtorch, filterstorch, None,
                    stride, padding, 1, 1),
            number=exec_number, repetition=repetitions)
        result_torch = result_torch.numpy()
        # be default it is the same timing (cpu, gpu)
        result_torch_gpu = np.zeros(result_torch.shape)
        torch_gpu_time = 0
        # let us run it only if CUDA is available
        if torch.cuda.is_available():
            # creates a LongTensor and transfers it to GPU as torch.conv1D_cuda.LongTensor
            xtorch_gpu = xtorch.to(device=device)
            filterstorch_gpu = filterstorch.to(device=device)
            torch_gpu_time, result_torch_gpu = timeitrep(
                wrapper(F.conv2d, xtorch_gpu, filterstorch_gpu, None,
                        stride, padding, 1, 1),
                number=exec_number, repetition=repetitions)
            # go back to cpu to display the results
            result_torch_gpu = result_torch_gpu.to(torch.device("cpu")).numpy()

        # conv_stanford_time, (result_stanford, _) = timeitrep(
        #     wrapper(conv_forward_fftw_1D, reshape(x), reshape(filters), b, conv_param),
        #     number=exec_number, repetition=repetitions)
        # numpy_time, result_numpy = timeitrep(wrapper(np.correlate, x, filters, mode=mode), number=exec_number,
        #
        #                                  repetition=repetitions)
        scipy_direct_time, result_scipy_direct = 0, result_naive
        scipy_fft_time, result_scipy_fft = 0, result_naive
        scipy_auto_time, result_scipy_auto = timeitrep(wrapper(signal.correlate, x, filters, mode=mode),
                                                       number=exec_number,
                                                       repetition=repetitions)

        # scipy_fft_time, result_scipy_fft = timeitrep(wrapper(signal.correlate, x, filters, mode=mode, method="fft"),
        #                                              number=exec_number, repetition=repetitions)
        # print("result naive shape: ", result_naive.shape)
        # print("result fft shape: ", result_fft.shape)
        # print("result torch shape: ", result_torch.shape)
        # print("result numpy shape: ", result_numpy.shape)
        # print("result scipy shape: ", result_numpy.shape)
        # print("result scipy fft shape: ", result_scipy_fft.shape)
        numpy_time, result_numpy = 0, result_naive
        result = [filter_size,
                  conv_naive_time,
                  stanford_time,
                  conv_fft_time,
                  conv_fftw_time,
                  torch_time,
                  torch_gpu_time,
                  numpy_time,
                  scipy_direct_time,
                  scipy_fft_time,
                  scipy_auto_time,
                  abs_error(result_naive, result_naive),
                  abs_error(result_naive, result_stanford),
                  abs_error(result_naive, result_fft),
                  abs_error(result_naive, result_fftw),
                  abs_error(result_naive, result_torch),
                  abs_error(result_naive, result_torch_gpu),
                  abs_error(result_naive, result_numpy),
                  abs_error(result_naive, result_scipy_direct),
                  abs_error(result_naive, result_scipy_fft),
                  abs_error(result_naive, result_scipy_auto),
                  ]
        out_file.write(",".join([str(x) for x in result]) + "\n")
        out_file.flush()
