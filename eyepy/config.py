# -*- coding: utf-8 -*-
import seaborn as sns

# Plotting config

# Line Style for Layers in B-Scan
layers_kwargs = {"linewidth": 1, "linestyle": "-"}

# Line Style for B-Scan positions on Slo
line_kwargs = {"linewidth": 0.3, "linestyle": "-"}

# Colors for different Layers
x = sns.color_palette("husl", 17)
color_palette = sns.color_palette(x[::3] + x[1::3] + x[2::3])
layers_color = {key: color_palette[value] for key, value in SEG_MAPPING.items()}
