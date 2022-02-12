# -*- coding: utf-8 -*-
import logging

import numpy as np
from scipy import ndimage as ndimage

logger = logging.getLogger(__name__)


def filter_by_depth(drusen_map, minimum_depth=2):
    filtered_drusen = np.copy(drusen_map)
    if minimum_depth == 0:
        return drusen_map
    # get array where connected components get same label
    connected_component_array, num_drusen = ndimage.label(drusen_map)
    # Go through each component, sum it along axis 0 and check max depth against threshold
    max_depths = np.zeros_like(connected_component_array)
    for label, drusen_pos in enumerate(ndimage.find_objects(connected_component_array)):
        component_sub_vol = connected_component_array[drusen_pos]
        component_max_depth = np.max(np.sum(component_sub_vol == label + 1, axis=0))
        component_sub_vol[component_sub_vol == label + 1] = component_max_depth
        max_depths[drusen_pos] = component_sub_vol
    filtered_drusen[max_depths < minimum_depth] = False
    return filtered_drusen.astype(bool)


def filter_by_height(drusen_map, minimum_height=2):
    if minimum_height == 0:
        return drusen_map
    connected_component_array, num_drusen = ndimage.label(drusen_map)
    component_height_array = component_max_height(connected_component_array)

    filtered_drusen = np.copy(drusen_map)
    filtered_drusen[component_height_array < minimum_height] = False
    return filtered_drusen.astype(bool)


def component_max_height(connected_component_array):
    max_heights = np.zeros_like(connected_component_array)
    # Iterate over all connected drusen components
    for drusen_pos in ndimage.find_objects(connected_component_array):
        # Work on subvolume for faster processing
        component_sub_vol = connected_component_array[drusen_pos]
        # Find current label (most frequent label in the subvolume)
        label = np.bincount(component_sub_vol[component_sub_vol != 0]).argmax()
        component_max_height = np.max(np.sum(component_sub_vol == label, axis=1))
        # Set drusen region to drusen max height
        max_heights[drusen_pos][component_sub_vol == label] = component_max_height
    return max_heights
