import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.ticker as tick
width = 15
height = 10
# plot details
bar_width = 0.15
epsilon = .015
line_width = 1
opacity = 0.6
iso_range = 450

file_walking = "/ors_foot-walking_comparison_categories.geojson"
file_cycling = "/ors_cycling-regular_comparison_categories.geojson"
file = file_walking
gdf = gpd.read_file(file)

gdf.drop(labels=["geometry"], axis=1, inplace=True)

gdf_i = gdf.loc[gdf["range"] == iso_range]
df = pd.DataFrame(gdf_i).reset_index().drop(labels=["index", "id"], axis=1)
cities = list(gdf["city"].unique())

fig, ax = plt.subplots(1, figsize=(12, 10))
plt.subplots_adjust(right=0.75)

# add second and third y axis
ax2 = ax.twinx()
# ax3 = ax.twinx()

# ax3.spines['right'].set_position(('outward', 80))
ax.set_zorder(ax2.get_zorder() + 1)
# ax3.set_zorder(ax2.get_zorder()+1)
ax.patch.set_visible(False)
# ax3.patch.set_visible(False)
bar_width_ratio = 0.05

# change bar location to plot them side by side
br1 = np.arange(len(df["city"].unique()))
br2 = [x + 0.03 + bar_width for x in br1]
br3 = [x + 0.03 + bar_width for x in br2]
# br4 = [x + 0.03 + bar_width for x in br3]

br11 = np.arange(len(df["city"].unique())) + 0.07
br22 = [x + 0.03 + bar_width for x in br11]
br33 = [x + 0.03 + bar_width for x in br22]

greenAreas = df.loc[df["category"] == "greenAreas"]
# greenAreas_total = np.array(greenAreas["population"])
greenAreas_ratio = np.array(greenAreas["total_population_percentage"])
greenAreas_POI_ratio = np.array(greenAreas["population_poi_ratio"])

historic = df.loc[df["category"] == "historic"]
# historic_total = np.array(historic["population"])
historic_ratio = np.array(historic["total_population_percentage"])
historic_POI_ratio = np.array(historic["population_poi_ratio"])

tourism = df.loc[df["category"] == "tourism"]
# tourism_total = np.array(tourism["population"])
tourism_ratio = np.array(tourism["total_population_percentage"])
tourism_POI_ratio = np.array(tourism["population_poi_ratio"])

# water = df.loc[df["category"]== "water"]
# water_total = np.array(water["population"])
# water_ratio = np.array(water["total_population_percentage"])
# water_POI_ratio = np.array(water["population_poi_ratio"])

bar_width_ratio = 0.1

# greenAreas_total_bar = ax2.bar(br1, greenAreas_total, bar_width,
#                                 color="#4CBB17",
#                                 label= "Green Areas [abs]",
#                                 alpha=opacity,
#                                 linewidth=line_width)
# historic_total_bar = ax2.bar(br2, historic_total, bar_width,
#                                 color="lightgrey",
#                                 label= "Historic Areas [abs]",
#                                 linewidth=line_width,
#                                 alpha=opacity)
# tourism_total_bar = ax2.bar(br3, tourism_total, bar_width,
#                                 linewidth=line_width,
#                                 color="indianred",
#                                 alpha=opacity,
#                                 label= "Tourism Areas [abs]")
# water_total_bar = ax2.bar(br4, water_total, bar_width,
#                                 linewidth=line_width,
#                                 color="cornflowerblue",
#                                 alpha=opacity,
#                                 label= "Water Areas [abs]")
plt.xticks([r + bar_width for r in range(len(df["city"].unique()))],
           list(df["city"].unique()))

# Pop / pop_total ratio
line_width = 1.5
bar_width_ratio = 0.05
greenAreas_ratio_bar = ax2.bar(br11,
                               greenAreas_ratio,
                               bar_width_ratio,
                               linewidth=line_width,
                               color="darkgreen",
                               label="Green Areas [%]",
                               edgecolor="darkgreen")
historic_ratio_bar = ax2.bar(br22,
                             historic_ratio,
                             bar_width_ratio,
                             linewidth=line_width,
                             color="dimgrey",
                             edgecolor="dimgrey",
                             label="Historic Areas [%]")
tourism_ratio_bar = ax2.bar(br33,
                            tourism_ratio,
                            bar_width_ratio,
                            linewidth=line_width,
                            edgecolor="darkred",
                            color="darkred",
                            label="Tourism Areas [%]")
# water_ratio_bar = ax2.bar(br4, water_ratio, bar_width_ratio,
#                                 linewidth=line_width,
#                                 edgecolor="darkblue",
#                                 color="none",
#                                 label= "Water Areas [%]")

# Pop / POI Ratio
bar_width_ratio = 0.05
line_width = 1
greenAreas_POI_ratio_bar = ax.bar(br1,
                                  greenAreas_POI_ratio,
                                  bar_width_ratio,
                                  linewidth=line_width,
                                  color="#4CBB17",
                                  alpha=opacity,
                                  hatch="//",
                                  label="Green Areas POI")
# edgecolor="darkgreen")
historic_POI_ratio_bar = ax.bar(
    br2,
    historic_POI_ratio,
    bar_width_ratio,
    linewidth=line_width,
    color="lightgrey",
    hatch="//",
    alpha=opacity,
    # edgecolor="dimgrey",
    label="Historic Areas POI")
tourism_POI_ratio_bar = ax.bar(
    br3,
    tourism_POI_ratio,
    bar_width_ratio,
    linewidth=line_width,
    hatch="//",
    # edgecolor="darkred",
    alpha=opacity,
    color="indianred",
    label="Tourism Areas POI")
# water_POI_ratio_bar = ax.bar(br4, water_POI_ratio, bar_width_ratio,
#                                 linewidth=line_width,
#                                 # edgecolor="darkblue",
#                                 color="darkblue",
#                                 label= "Water Areas POI")

# def y_fmt(tick_val, pos):
#     if tick_val > 1000000:
#         val = int(tick_val)/1000000
#         return f'{val} M'
#     elif tick_val > 1000:
#         val = int(tick_val) / 1000
#         return f'{val} k'
#     else:
#         return tick_val


def y_fmt(tick_val, pos):
    if tick_val > 100000:
        val = int(tick_val) / 1000000
        return f'{val} M'
    elif tick_val > 1000:
        val = int(tick_val) / 1000
        return f'{val} k'
    else:
        return tick_val


ax2.yaxis.set_major_formatter(tick.FuncFormatter(y_fmt))
# ax2.xaxis.set_major_formatter(mtick.EngFormatter())

ax.set_xticklabels(cities, rotation=35)
ax.set_ylabel('Total population per POI')
ax2.set_ylabel("Reached population per category [%]")
# ax3.set_ylabel("Reached population per category [%]")

h1, l1 = ax.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
# h3, l3 = ax3.get_legend_handles_labels()
# cycing
# ax.legend(h1+h2, l1+l2, loc="lower right", bbox_to_anchor=(1.05, -0.15), prop={"size": 10}, ncol=2) # , bbox_to_anchor=(1, 1), ncol=2
# walking
ax.legend(h1 + h2,
          l1 + l2,
          loc="upper right",
          bbox_to_anchor=(1, 1),
          prop={"size": 10},
          ncol=2)  # , bbox_to_anchor=(1, 1), ncol=2

plt.tight_layout()
plt.show()
