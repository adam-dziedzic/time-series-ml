import matplotlib

# matplotlib.use('TkAgg')
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42
import matplotlib.pyplot as plt
import csv
import os
import torch
import numpy as np

from cnns.nnlib.pytorch_layers.pytorch_utils import get_full_energy_only
from cnns.nnlib.robustness.utils import to_fft_magnitude

print(matplotlib.get_backend())

# plt.interactive(True)
# http://ksrowell.com/blog-visualizing-data/2012/02/02/optimal-colors-for-graphs/
MY_BLUE = (56, 106, 177)
MY_RED = (204, 37, 41)
MY_ORANGE = (218, 124, 48)
MY_GREEN = (62, 150, 81)
MY_BLACK = (83, 81, 84)


def get_color(COLOR_TUPLE_255):
    return [x / 255 for x in COLOR_TUPLE_255]


# fontsize=20
fontsize = 30
legend_size = 26
font = {'size': fontsize}
matplotlib.rc('font', **font)

dir_path = os.path.dirname(os.path.realpath(__file__))
print("dir path: ", dir_path)

GPU_MEM_SIZE = 16280


def read_columns(dataset, columns=5):
    file_name = dir_path + "/" + dataset + ".csv"
    with open(file_name) as csvfile:
        data = csv.reader(csvfile, delimiter=",", quotechar='|')
        cols = []
        for column in range(columns):
            cols.append([])

        for i, row in enumerate(data):
            if i > 0:  # skip header
                for column in range(columns):
                    cols[column].append(float(row[column]))
    return cols


ylabel = "ylabel"
title = "title"
legend_pos = "upper center"
bbox = "bbox"
file_name = "file_name"

energy = {ylabel: "Amplitude (log scale)",
        file_name: "wifi_energy",
        title: "accuracy",
        legend_pos: "upper center",
        bbox: (0.0, 0.1)}

labels = ["", "0 Wi-Fi", "1 Wi-Fi", "2 Wi-Fis"]
ncols = [3, 3]
columns = 4

colors = [get_color(color) for color in
          ["", MY_GREEN, MY_BLUE, MY_ORANGE, MY_RED, MY_BLACK]]
markers = ["+", "o", "v", "s", "D", "^"]
linestyles = ["", "-", "--", ":"]

datasets = [energy]

# width = 12
# height = 5
# lw = 3

width = 15
height = 7
lw = 4

onesided = False
normalized = True
is_log = True

def to_xfft(signal):
    xfft = torch.rfft(torch.from_numpy(signal), onesided=onesided,
                      signal_ndim=1,
                      normalized=normalized)
    print("Energy in the frequency domain (pytorch): ",
          get_full_energy_only(xfft))
    x_numpy = xfft[..., 0].numpy() + 1.0j * xfft[..., 1].numpy()
    print("Energy in the frequency domain (numpy): ",
          np.sum(np.power(np.absolute(x_numpy), 2)))
    xfft_mag = to_fft_magnitude(xfft, is_log)
    return xfft_mag

fig = plt.figure(figsize=(width, len(datasets) * height))

for j, dataset in enumerate(datasets):
    plt.subplot(len(datasets), 1, j + 1)
    print("dataset: ", dataset)
    cols = read_columns(dataset[file_name], columns=columns)

    print("col 0: ", cols[0])
    print("col 1: ", cols[1])

    for i in range(columns):
        if i > 0:  # skip first column with the epoch number
            signal = cols[i]
            xfft_mag = to_xfft(signal=np.array(signal))
            plt.plot(range(len(signal)),
                     xfft_mag,
                     label=f"{labels[i]}",
                     lw=lw,
                     color=colors[i],
                     linestyle=linestyles[i])

    plt.grid()
    plt.legend(loc=dataset[legend_pos], ncol=ncols[j], frameon=False,
               prop={'size': legend_size},
               # bbox_to_anchor=dataset[bbox]
               )
    plt.xlabel('Frequency (sample number)')
    # plt.title(titles[j], fontsize=16)
    plt.ylabel(dataset[ylabel])
    # plt.ylim(-40, -15)
    # plt.xlim(0, 2048)

# plt.gcf().autofmt_xdate()
# plt.xticks(rotation=0)
# plt.interactive(False)
# plt.imshow()
plt.subplots_adjust(hspace=0.3)
format = "pdf"  # "pdf" or "png"
destination = dir_path + "/" + "wifi-energy-fft." + format
print("destination: ", destination)
fig.savefig(destination,
            bbox_inches='tight',
            # transparent=True
            )
plt.show(block=True)
# plt.interactive(False)
plt.close()


