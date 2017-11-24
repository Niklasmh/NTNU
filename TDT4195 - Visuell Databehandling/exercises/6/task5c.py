#!/usr/bin/python3

import numpy as np
import matplotlib.pyplot as plt
import imageio
from skimage.draw import line
from skimage.measure import shannon_entropy, label, regionprops
from skimage.feature import canny
from skimage.morphology import square, disk, binary_erosion, binary_dilation, binary_closing, skeletonize
from skimage.transform import hough_line, hough_line_peaks
from scipy.ndimage import binary_fill_holes

# Read in image
filepath = "images/task5-01.tiff"
img = imageio.imread(filepath)

def findEdges(img):

    # We use canny edge detection as of the gradients and thin lines
    edges = canny(img, 2)

    return edges

def findLines(img):
    r = img[..., 0]
    g = img[..., 1]
    b = img[..., 2]

    # Add all edges together
    edges = findEdges(r) + findEdges(g) + findEdges(b)

    # Dilate to make the edges thicker
    dilatedEdges = binary_dilation(edges)

    # To a Hough transform to find the lines
    h, theta, d = hough_line(dilatedEdges)

    return edges, dilatedEdges, (h, theta, d)

# Removing long lines from image
def removeChessboard(img):

    # Get the major lines in the image
    edges, dilatedEdges, (h, theta, d) = findLines(img)

    # Create image with ones to fill inn lines
    lines = np.ones(img.shape[:2])

    # Add lines to image as zeroes
    for _, angle, dist in zip(*hough_line_peaks(h, theta, d)):
        y0 = (dist - 0 * np.cos(angle)) / np.sin(angle)
        y1 = (dist - img.shape[1] * np.cos(angle)) / np.sin(angle)
        x, y = line(int(y1), 0, int(y0), img.shape[1] - 1)
        x = np.clip(x, 0, img.shape[0] - 1)
        y = np.clip(y, 0, img.shape[1] - 1)
        lines[x, y] = 0

    # Remove border edges from image with all edges
    w = 4
    edges = np.pad(edges[w:img.shape[0] - w, w:img.shape[1] - w], w, mode='constant')

    # Erode the lines bigger, such that they cover the original lines
    lines = binary_erosion(lines, square(13))

    # Remove major lines and close shape paths
    removedChessboard = binary_closing(edges * lines, square(8))

    return removedChessboard

def removeNoise(img):

    # Removing unimportant lines from the image
    removedNoise = removeChessboard(img)

    # Thinning the lines
    removedNoise = skeletonize(removedNoise)

    # Filling the holes in the image
    removedNoise = binary_fill_holes(removedNoise)

    return removedNoise

def segmentImage(img):

    regions = regionprops(label(removedNoise))

    return regions

def recognizeShapes(img):

    # Label and partition the regions
    regions = segmentImage(removedNoise)

    # Define info about shapes in the image
    # The order attribute is the order which the shapes are distributed based on a utility (area, shannon_entropy)
    shapes = {
        "star": { "bbox": None, "centroid": [ 0, 0 ], "color": [ .5, .5, .5 ], "order": 0 },
        "triangle": { "bbox": None, "centroid": [ 0, 0 ], "color": [ .9, .9, .4 ], "order": 1 },
        "romboid": { "bbox": None, "centroid": [ 0, 0 ], "color": [ 0, .6, 1.0 ], "order": 2 },
        "hexagon": { "bbox": None, "centroid": [ 0, 0 ], "color": [ .9, .9, .9 ], "order": 3 },
        "circle": { "bbox": None, "centroid": [ 0, 0 ], "color": [ .8, .5, .2 ], "order": 4 }
    }

    # Collection of shape attributes for each region
    shapeInfo = []
    for region in regions:
        # Based on area
        #shapeInfo.append([region.area, region.centroid, region.bbox])

        # Based on the shannon entropy
        shapeInfo.append([shannon_entropy(region.image), region.centroid, region.bbox])

    shapeInfo.sort()

    # Connecting the centroids and bounding boxes to each shape
    for shape in shapes:
        shapes[shape]["centroid"][0] = int(shapeInfo[shapes[shape]["order"]][1][0])
        shapes[shape]["centroid"][1] = int(shapeInfo[shapes[shape]["order"]][1][1])
        shapes[shape]["bbox"] = shapeInfo[shapes[shape]["order"]][2]

    return shapes

def fillShapes(originalImage, filteredImage, shapes):
    newImage = np.zeros(originalImage.shape)

    for shape in shapes:
        bbox = shapes[shape]["bbox"]
        c = shapes[shape]["centroid"]

        # Coloring the shapes
        newImage[bbox[0]:bbox[2], bbox[1]:bbox[3], 0] = filteredImage[bbox[0]:bbox[2], bbox[1]:bbox[3]] * shapes[shape]["color"][0]
        newImage[bbox[0]:bbox[2], bbox[1]:bbox[3], 1] = filteredImage[bbox[0]:bbox[2], bbox[1]:bbox[3]] * shapes[shape]["color"][1]
        newImage[bbox[0]:bbox[2], bbox[1]:bbox[3], 2] = filteredImage[bbox[0]:bbox[2], bbox[1]:bbox[3]] * shapes[shape]["color"][2]

        # Coloring the centroid
        s = 4 # Size
        newImage[c[0]-s-1:c[0]+s, c[1]-s-1:c[1]+s, 0] -= 100 * disk(s)
        newImage[c[0]-s-1:c[0]+s, c[1]-s-1:c[1]+s, 0] = np.clip(newImage[c[0]-s-1:c[0]+s, c[1]-s-1:c[1]+s, 0], 0, 1)
        newImage[c[0]-s-1:c[0]+s, c[1]-s-1:c[1]+s, 1] -= 100 * disk(s)
        newImage[c[0]-s-1:c[0]+s, c[1]-s-1:c[1]+s, 1] = np.clip(newImage[c[0]-s-1:c[0]+s, c[1]-s-1:c[1]+s, 1], 0, 1)
        newImage[c[0]-s-1:c[0]+s, c[1]-s-1:c[1]+s, 2] -= 100 * disk(s)
        newImage[c[0]-s-1:c[0]+s, c[1]-s-1:c[1]+s, 2] = np.clip(newImage[c[0]-s-1:c[0]+s, c[1]-s-1:c[1]+s, 2], 0, 1)

    return newImage

# Removing the noise and thinning the shapes left
removedNoise = removeNoise(img)

# Connect the shapes to a list of predefined shapes
recognizedShapes = recognizeShapes(img)

# Fill the shapes
filledShapes = fillShapes(img, removedNoise, recognizedShapes)

_, ax = plt.subplots(1, 2, figsize=(30, 10))
ax[0].imshow(img, cmap=plt.cm.gray)
ax[0].set_axis_off()

ax[1].imshow(filledShapes, cmap=plt.cm.gray)
ax[1].set_axis_off()

plt.show()
