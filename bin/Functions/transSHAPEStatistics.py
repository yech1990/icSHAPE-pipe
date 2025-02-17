import pandas as pd
import seaborn as sns
import os, sys
import matplotlib.pyplot as plt
import matplotlib
import getopt
import numpy as np
import re
import random
import version

font = {"size": 12}
matplotlib.rc("font", **font)
matplotlib.use("Agg")

dirname = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, dirname + "/../../GAP")
import GAP

Usage = """
transSHAPEStatistics - Statistics the RNA distribution of transcript-based SHAPE
================================================================================
\x1b[1mUSAGE:\x1b[0m 
  %s -g genomeCoor.bed -i transSHAPE.out -o report.pdf

\x1b[1mHELP:\x1b[0m        
  -g                    <String>
                                A genome-coor based annotation file: hg38.genomeCoor.bed (generated by parseGTF)

  -i                    <String>
                                Input a transSHAPE file produced by genSHAPEToTransSHAPE
  -o                    <String>
                                Output statistics to PDF file (default: report.pdf)

\x1b[1mVERSION:\x1b[0m
    %s

\x1b[1mAUTHOR:\x1b[0m
    Li Pan

""" % (
    sys.argv[0],
    version.Version,
)


def init():
    params = {"inFile": None, "outFolder": None, "annotation": None}
    opts, args = getopt.getopt(sys.argv[1:], "hi:o:g:")
    for op, value in opts:
        if op == "-h":
            print(Usage)
            sys.exit(-1)
        # Basic Parameters
        elif op == "-i":
            params["inFile"] = os.path.abspath(value)
        elif op == "-o":
            params["outFolder"] = os.path.abspath(value).rstrip("/") + "/"
        elif op == "-g":
            params["annotation"] = os.path.abspath(value)
        else:
            sys.stderr.writelines("Error: unrecognized parameter: " + op + "\n")
            print(Usage)
            sys.exit(-1)

    # check
    if (
        (not params["inFile"])
        or (not params["outFolder"])
        or (not params["annotation"])
    ):
        sys.stderr.writelines("Error: Please specify -i -o and -g" + "\n")
        print(Usage)
        sys.exit(-1)

    return params


def load_shape(ShapeFn, rem_tVersion=False, min_RPKM=None):
    """
    ShapeFn             -- Standard icSHAPE file
    rem_tVersion        -- Remove version information. ENST000000022311.2 => ENST000000022311
    min_RPKM            -- Minimum RPKM
    """
    SHAPE = {}

    for line in open(ShapeFn):
        data = line.strip().split()
        transID, transLen, transRPKM = data[0], int(data[1]), data[2]
        if rem_tVersion and "." in transID:
            transID = ".".join(transID.split(".")[:-1])

        if min_RPKM and float(transRPKM) < minRPKM:
            continue

        SHAPE[transID] = data[3:]

    return SHAPE


params = init()
if not os.path.exists(params["outFolder"]):
    os.mkdir(params["outFolder"])

if not os.path.exists(params["outFolder"] + "img"):
    os.mkdir(params["outFolder"] + "img")

print("Start load icSHAPE file...")
SHAPE = load_shape(params["inFile"])

print("Start load annotation file...")
Parser = GAP.init(params["annotation"], showAttr=False)


def classify_transcript(SHAPE, Parser):
    classified_shape = {}
    for tid in SHAPE:
        try:
            gene_type = Parser.getTransFeature(tid)["gene_type"]
        except KeyError:
            sys.stderr.writelines("Warning: " + tid + " not found in annotation file")
            continue
        shape_list = SHAPE[tid]
        try:
            classified_shape[gene_type][tid] = shape_list
        except KeyError:
            classified_shape[gene_type] = {tid: shape_list}
    return classified_shape


classified_shape = classify_transcript(SHAPE, Parser)


def count_trans_for_genetype(classified_shape):
    genetypecount = []
    for genetype in classified_shape:
        genetypecount.append([genetype, len(classified_shape[genetype])])
    genetypecount.sort(key=lambda x: x[1], reverse=True)
    return genetypecount


trans_genetype_count = count_trans_for_genetype(classified_shape)


def count_base_for_genetype(classified_shape):
    genetypecount = []
    for genetype in classified_shape:
        genetypecount_tmp = 0
        for tid in classified_shape[genetype]:
            genetypecount_tmp += len(
                classified_shape[genetype][tid]
            ) - classified_shape[genetype][tid].count("NULL")
        genetypecount.append([genetype, genetypecount_tmp])
    genetypecount.sort(key=lambda x: x[1], reverse=True)
    return genetypecount


base_genetype_count = count_base_for_genetype(classified_shape)


def count_trans_cov_ratio(SHAPE):
    ratio_list = []
    for tid in SHAPE:
        shape_list = SHAPE[tid]
        valid_count = len(shape_list) - shape_list.count("NULL")
        ratio = round(1.0 * valid_count / len(shape_list), 3)
        ratio_list.append(ratio)
    return ratio_list


ratio_list = count_trans_cov_ratio(SHAPE)


def cdf(data_list, color="red", topdown=False, label=None, plotMedian=True):

    data_list = np.sort(data_list)
    if topdown:
        p = 1 - 1.0 * np.arange(len(data_list)) / (len(data_list) - 1)
    else:
        p = 1.0 * np.arange(len(data_list)) / (len(data_list) - 1)
    plt.plot(data_list, p, color=color, label=label)
    if plotMedian:
        median_x = data_list[int(len(data_list) / 2)]
        median_y = p[int(len(p) / 2)]
        plt.plot([median_x], [median_y], "bo", color="#e91e63")
        plt.axvline(
            x=median_x,
            ymin=0,
            ymax=1,
            linewidth=1,
            color="#e91e63",
            linestyle="--",
            label="median",
        )


plt.figure(figsize=(6, 5))
cdf(ratio_list, color="black", topdown=True, label=None, plotMedian=True)
plt.xlabel("Rate of transcript coverage")
plt.ylabel("Fraction of transcript")
plt.legend(frameon=False, fancybox=False)
plt.tight_layout()
plt.savefig(params["outFolder"] + "img/ratio-cdf.png")
plt.close()


def calc_gini(list_of_values):
    """
    list_of_values          -- A list of float values

    Return -1 if failed
    """
    length = len(list_of_values)
    total = sum(list_of_values)
    if total == 0:
        return -1

    Sorted_Array = sorted(list_of_values)
    accum, giniB = 0, 0

    for i in Sorted_Array:
        accum += i
        giniB += accum - i / 2.0

    fair_area = accum * length / 2.0
    return (fair_area - giniB) / fair_area


def calc_sliding_gini(shape_list, winSize=30):
    start = 0
    gini_list = []
    while start + winSize < len(shape_list):
        gini = calc_gini(shape_list[start : start + winSize])
        if gini != -1:
            gini_list.append(gini)
        start += winSize
    if gini_list:
        return np.mean(gini_list)
    else:
        return -1


def calc_shape_gini(shape_list, min_num=30):
    """
    shape_list          -- A list of SHAPE scores
    min_num             -- Miminum number of scores

    Return -1 if failed
    """
    float_shape = [float(shape) for shape in shape_list if shape != "NULL"]

    if len(float_shape) > min_num:
        return round(calc_sliding_gini(float_shape, min_num), 3)

    return -1


def gene_type(raw_type):
    valid_gene_type = (
        "pseudogene",
        "snoRNA",
        "snRNA",
        "miRNA",
        "misc_RNA",
        "rRNA",
        "mRNA",
    )
    lncRNA_class = (
        "3prime_overlapping_ncrna",
        "antisense",
        "lincRNA",
        "non_coding",
        "sense_intronic",
        "sense_overlapping",
        "processed_transcript",
    )
    if raw_type in valid_gene_type:
        return raw_type
    if re.match(".*pseudogene", raw_type):
        return "pseudogene"
    if raw_type == "protein_coding":
        return "mRNA"
    if raw_type in lncRNA_class:
        return "lncRNA"
    return "other"


def genetype_gini(classified_shape, Parser):
    GINI = {
        "pseudogene": [],
        "snoRNA": [],
        "snRNA": [],
        "miRNA": [],
        "misc_RNA": [],
        "mRNA": [],
        "lncRNA": [],
        "5'UTR": [],
        "CDS": [],
        "3'UTR": [],
    }
    for gtype in classified_shape:
        transformed_gtype = gene_type(gtype)
        if transformed_gtype in GINI:
            for tid in classified_shape[gtype]:
                shape_list = classified_shape[gtype][tid]
                gini = calc_shape_gini(shape_list, min_num=30)
                if gini != -1:
                    GINI[transformed_gtype].append(gini)
                if transformed_gtype == "mRNA":
                    ft = Parser.getTransFeature(tid)
                    cds_start = ft["cds_start"]
                    cds_end = ft["cds_end"]
                    shape_utr5 = shape_list[:cds_start]
                    shape_cds = shape_list[cds_start:cds_end]
                    shape_utr3 = shape_list[cds_end:]
                    gini_5 = calc_shape_gini(shape_utr5)
                    gini_cds = calc_shape_gini(shape_cds)
                    gini_3 = calc_shape_gini(shape_utr3)
                    if gini_5 != -1:
                        GINI["5'UTR"].append(gini_5)
                    if gini_cds != -1:
                        GINI["CDS"].append(gini_cds)
                    if gini_3 != -1:
                        GINI["3'UTR"].append(gini_3)
        else:
            sys.stderr.writelines(
                "Warning: ["
                + gtype
                + " => "
                + transformed_gtype
                + "] won't be counted. Skip it\n"
            )
            continue
    return GINI


GINI = genetype_gini(classified_shape, Parser)


def adjacent_values(vals, q1, q3):
    import numpy

    vals = sorted(vals)

    upper_adjacent_value = q3 + (q3 - q1) * 1.5
    upper_adjacent_value = numpy.clip(upper_adjacent_value, q3, vals[-1])

    lower_adjacent_value = q1 - (q3 - q1) * 1.5
    lower_adjacent_value = numpy.clip(lower_adjacent_value, vals[0], q1)
    return lower_adjacent_value, upper_adjacent_value


def set_axis_style(ax, labels):
    import numpy

    ax.get_xaxis().set_tick_params(direction="out")
    ax.xaxis.set_ticks_position("bottom")
    ax.set_xticks(numpy.arange(1, len(labels) + 1))
    ax.set_xticklabels(labels)
    ax.set_xlim(0.25, len(labels) + 0.75)


def violin(ax, data_list, labels, colors=None, rem_ext=0):
    """
    fig, axs = plt.subplots(nrows=5, ncols=1, figsize=(6, 12), sharey=True)

    axs[0].set_title('smartSHAPE 1 ng')
    axs[0].set_ylabel('smart SHAPE score')
    data = [ [],[],[],[] ]
    violin(axs[0], data, ['A', 'T', 'C', 'G'])

    fig.tight_layout()
    fig.show()
    """
    import numpy

    if colors == None:
        colors = ["#D43F3A"] * len(data_list)
    else:
        assert len(colors) == len(data_list)
        colors = colors[::-1]

    if rem_ext:
        assert 0.0 <= rem_ext <= 0.5
        import copy

        data_list = copy.deepcopy(data_list)
        for idx in range(len(data_list)):
            data_list[idx].sort()
            remNum = int(len(data_list[idx]) * rem_ext)
            start = remNum
            end = len(data_list[idx]) - remNum
            data_list[idx] = data_list[idx][start:end]

    parts = ax.violinplot(
        data_list, showmeans=False, showmedians=False, showextrema=False
    )

    for pc in parts["bodies"]:
        pc.set_facecolor(colors.pop())
        pc.set_edgecolor("black")
        pc.set_alpha(1)

    quartile1 = []
    medians = []
    quartile3 = []
    for data in data_list:
        quartile1.append(numpy.percentile(data, 25))
        medians.append(numpy.percentile(data, 50))
        quartile3.append(numpy.percentile(data, 75))

    whiskers = numpy.array(
        [
            adjacent_values(sorted_array, q1, q3)
            for sorted_array, q1, q3 in zip(data_list, quartile1, quartile3)
        ]
    )

    whiskersMin, whiskersMax = whiskers[:, 0], whiskers[:, 1]

    inds = numpy.arange(1, len(medians) + 1)
    ax.scatter(inds, medians, marker="o", color="white", s=20, zorder=3)
    ax.vlines(inds, quartile1, quartile3, color="k", linestyle="-", lw=8)
    ax.vlines(inds, whiskersMin, whiskersMax, color="k", linestyle="-", lw=1)

    set_axis_style(ax, labels)


labels = [
    "mRNA",
    "5'UTR",
    "CDS",
    "3'UTR",
    "pseudogene",
    "lncRNA",
    "miRNA",
    "snoRNA",
    "misc_RNA",
]
ave_gini = np.mean([np.mean(GINI[t]) for t in GINI if GINI[t]])
gini_list = [GINI[t] if len(GINI[t]) > 30 else [ave_gini] * 30 for t in labels]
colors = [
    "#f44336",
    "#9c27b0",
    "#3f51b5",
    "#009688",
    "#ff5722",
    "#795548",
    "#ff9800",
    "#673ab7",
    "#cddc39",
]
show_labels = [l + "\n(" + str(len(GINI[l])) + ")" for l in labels]

fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(8, 4), sharey=True)
ax.set_ylabel("Gini (reactivity score)")
violin(ax, gini_list, show_labels, colors=colors, rem_ext=0.05)
plt.axvline(x=4.5, ymin=0, ymax=1, linewidth=1, color="black", linestyle="--")
plt.xticks(rotation=45)
fig.tight_layout()
plt.savefig(params["outFolder"] + "img/gini-violin.png")
plt.close()


def count_mRNA_period(mRNA_shape, Parser):
    start_codon = []
    stop_codon = []

    for i in range(51):
        start_codon.append([])
        stop_codon.append([])

    for tid in mRNA_shape:
        ft = Parser.getTransFeature(tid)
        shape_list = mRNA_shape[tid]
        Len = len(shape_list)
        cds_s, cds_e = ft["cds_start"], ft["cds_end"]
        if Len < 150:
            continue
        if cds_s < 25 or cds_s + 25 > cds_e - 25 or cds_e < 75 or cds_e + 25 > Len - 35:
            continue
        for i in range(cds_s - 25, cds_s + 26):
            if shape_list[i] != "NULL":
                start_codon[i - (cds_s - 25)].append(float(shape_list[i]))
        for i in range(cds_e - 25, cds_e + 26):
            if shape_list[i] != "NULL":
                stop_codon[i - (cds_e - 25)].append(float(shape_list[i]))

    for i in range(51):
        if len(start_codon[i]) < 20:
            start_codon[i] = [0.2] * 20
        if len(stop_codon[i]) < 20:
            stop_codon[i] = [0.2] * 20

    return start_codon, stop_codon


mRNA_shape = classified_shape.get("protein_coding", {})
mRNA_shape.update(classified_shape.get("mRNA", {}))

start_codon_profile, stop_codon_profule = count_mRNA_period(mRNA_shape, Parser)

tmp = plt.figure(figsize=(15, 4))
last_v = np.nan
for x, shape_list in enumerate(start_codon_profile):
    if len(shape_list) > 100:
        value = np.mean(shape_list)
        tmp = plt.plot(x + 1, value, "o", color="#2196f3")
        if not np.isnan(last_v):
            tmp = plt.plot((x, x + 1), (last_v, value), linestyle="-", color="#9e9e9e")
        last_v = value
    else:
        last_v = np.nan

last_v = np.nan
for x, shape_list in enumerate(stop_codon_profule):
    if len(shape_list) > 100:
        value = np.mean(shape_list)
        tmp = plt.plot(x + 61, value, "o", color="#2196f3")
        if not np.isnan(last_v):
            tmp = plt.plot(
                (x + 60, x + 61), (last_v, value), linestyle="-", color="#9e9e9e"
            )
        last_v = value
    else:
        last_v = np.nan


tmp = plt.xticks(
    [1, 26, 51, 61, 86, 111], ["-25", "start codon", "25", "-25", "stop codon", "25"]
)
tmp = plt.xlabel("Nucleotide position")
tmp = plt.ylabel("Reactivity scoore")
tmp = plt.tight_layout()
tmp = plt.savefig(params["outFolder"] + "img/profile.png")
tmp = plt.close()


html = """
<!DOCTYPE html>
<html>
<head>
<title>Transcript reactivity score</title>
<meta http-equiv=Content-Type content="text/html;charset=utf-8">
<meta name="viewport" content="width=device-width;initial-scale=1.0">
<link rel="stylesheet" type="text/css" href="https://www.w3schools.com/w3css/4/w3.css">
</head>
<body>
<div class="w3-content" style="max-width: 1000px">
    <div class="w3-panel w3-pink w3-center"><h3>{0}</h3></div>
    <p>command: {1}</p>
    
    <div class="w3-container w3-section">
        <h3>1. Number of transcript</h3>
        <p>The table below counts the number of transcripts for each type of gene.</p>
        <table class="w3-table-all" style="width:100%">
            <tr>
                <th>Type</th>
                <th>Number</th>
                <th>Ratio</th>
            </tr>
            {2}
        </table>
    </div>

    <div class="w3-container w3-section">
        <h3>2. Number of bases</h3>
        <p>The table below counts the number of bases for each type of gene.</p>
        <table class="w3-table-all" style="width:100%">
            <tr>
                <th>Type</th>
                <th>Number</th>
                <th>Ratio</th>
            </tr>
            {3}
        </table>
    </div>

    <div class="w3-container w3-section">
        <h3>3. Coverage of transcript</h3>
        <p>The figure below shows the distribution of the coverage of the reactivity score on transcripts.</p>
        <div style="width:100%">
            <img src="img/ratio-cdf.png" alt="Coverage of transcript" style="max-width:500px"/>
        </div>
    </div>

    <div class="w3-container w3-section">
        <h3>4. Gini index</h3>
        <p>The figure below shows the distribution of the Gini Index for each type of RNA.</p>
        <div style="width:100%">
            <img src="img/gini-violin.png" alt="Gini index" style="width:100%"/>
        </div>
    </div>

    <div class="w3-container w3-section">
        <h3>5. Periodicity</h3>
        <p>The figure below shows The periodicity of the reactivity score around the start codon and the stop codon.</p>
        <div style="width:100%">
            <img src="img/profile.png" alt="Periodicity" width="100%" />
        </div>
    </div>

</div>
</body>
</html>
"""


html_table_row_temp = "                <tr><td>%s</td><td>%s</td><td>%.2f%%</td></tr>\n"

trans_row = ""
total = sum([it[1] for it in trans_genetype_count])
for gene_type, count in trans_genetype_count:
    trans_row += html_table_row_temp % (
        gene_type,
        "{:,}".format(int(count)),
        100.0 * count / total,
    )

base_row = ""
total = sum([it[1] for it in base_genetype_count])
for gene_type, count in base_genetype_count:
    base_row += html_table_row_temp % (
        gene_type,
        "{:,}".format(int(count)),
        100.0 * count / total,
    )

pure_file = params["inFile"].split("/")[-1]
command = " ".join(sys.argv)

OUT = open(params["outFolder"] + "report.html", "w")
OUT.writelines(html.format(pure_file, command, trans_row, base_row))
OUT.close()
