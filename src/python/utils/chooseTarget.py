from __future__ import division, print_function
from math import *

# [input] a list of targets from signature with attributes
#         x, y (axis), w (width), h (height)
#
# [output] target x, y, w, h

def chooseTarget(TargetList，pixLocX, picLocY):
    xList = [i_target.x - pixLocX for i_target in TargetList]
    yList = [i_target.y - pixLocY for i_target in TargetList]
    wList = [i_target.w for i_target in TargetList]
    hList = [i_target.h for i_target in TargetList]
    areaList = [w*h for w, h in zip(wList, hList)]
    distList = [sqrt(x**2+y**2) for x, y in zip(xList, yList)]
    findTar = [area/dist for area, dist in zip(areaList, distList)]
    max_Tar = max(findTar)
    ind = [i for i in range(len(findTar)) if findTar[i] == max_Tar]
    return TargetList[ind[0]]
