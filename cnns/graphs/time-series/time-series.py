import matplotlib
# matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import csv
import os

print(matplotlib.get_backend())

plt.interactive(True)
# http://ksrowell.com/blog-visualizing-data/2012/02/02/optimal-colors-for-graphs/
MY_BLUE = (56, 106, 177)
MY_RED = (204, 37, 41)
MY_ORANGE = (218, 124, 48)
MY_GREEN = (62, 150, 81)
MY_BLACK = (83, 81, 84)


def get_color(COLOR_TUPLE_255):
    return [x / 255 for x in COLOR_TUPLE_255]


font = {'size': 20}
matplotlib.rc('font', **font)

dir_path = os.path.dirname(os.path.realpath(__file__))

GPU_MEM_SIZE = 16280


def read_columns(dataset, columns=7):
    file_name = dir_path + "/" + dataset + ".csv"
    with open(file_name) as csvfile:
        data = csv.reader(csvfile, delimiter=",", quotechar='|')
        cols = []
        for column in range(columns):
            cols.append([])

        for i, row in enumerate(data):
            if i > 1:  # skip header
                for column in range(columns):
                    print(row[column + 1])
                    cols[column].append(float(row[column + 1]))
    return cols


fig = plt.figure(figsize=(10, 8))

dataset = "data"
labels = ["", "80", "90", "95"]
legend_pos = ["center left", "upper left"]
columns = 7
colors = [get_color(color) for color in
          ["", MY_GREEN, MY_BLUE, MY_ORANGE, MY_RED, MY_BLACK]]
markers = ["+", "o", "v", "s", "D", "^"]
linestyles = ["", "-", "--", ":"]

cols = read_columns(dataset, columns=columns)

print("col 0: ", cols[0])
print("col 1: ", cols[1])

# blue main points
# Accurayc of model at 99% energy preserved level against accuracy of model at 100% energy preserved level
plt.plot(cols[0], cols[1],
         label="Accuracy of model at 99% energy\n"
               "preserved vs. accuracy of model\n"
               "at 100% energy preserved", lw=3,
         color=get_color(MY_BLUE), linestyle="", marker="o", markersize=10)

# red middle line
plt.plot(cols[0], cols[2], label="+/- 0.00 (accuracy difference)", lw=3,
         color=get_color(MY_RED), linestyle="-")

# green line
plt.plot(cols[0], cols[3], label="+/- 0.05", lw=3, color=get_color(MY_GREEN),
         linestyle="-")

# yellow line
plt.plot(cols[0], cols[4], label="+/- 0.10", lw=3, color=get_color(MY_ORANGE),
         linestyle=":")

# 2nd yellow line
plt.plot(cols[0], cols[5], lw=3, color=get_color(MY_ORANGE), linestyle=":")

# 2nd green line
plt.plot(cols[0], cols[6], lw=3, color=get_color(MY_GREEN),
         linestyle="-")

plt.grid()
plt.legend(loc="upper left", ncol=1, frameon=False,
           prop={'size': 18}, bbox_to_anchor=(0.0, 1.025))
plt.xlabel('Epoch')
plt.xlabel('100% energy preserved')
plt.ylabel('99% energy preserved')
plt.xlim(50, 100)
plt.ylim(50, 100)

# plt.gcf().autofmt_xdate()
# plt.xticks(rotation=0)
# plt.interactive(False)
# plt.imshow()
plt.show(block=True)
plt.interactive(False)
format="png" # "pdf" or "png"
fig.savefig(dir_path + "/" + "time-series." + format,
            bbox_inches='tight', transparent=True)
