import json
import math
import os.path
import random
import statistics

import svgwrite

width = 640
height = 1080
grid = 32
isLine = False

HEATMAP_COLORS = [
    '#ddffff',  # Blue       1% -  9%
    '#afffff',  # Blue      10% - 19%
    '#aaf191',  # Green     20% - 29%
    '#80d385',  # Green     30% - 39%
    '#ffff8c',  # Yellow    40% - 49%
    '#f9d057',  # Yellow    50% - 59%
    '#f29e2e',  # Orange    60% - 69%
    '#e76818',  # Orange    70% - 79%
    '#ff6161',  # Red       80% - 89%
    '#ff0000',  # Red       90% - 100%
]


class BaseHeatmap(object):
    def __init__(self, width=640, height=480, gridSize=10):
        self.width = width
        self.height = height
        self.gridSize = gridSize

    def translate(self, data, isLine=False):
        raise


class SimpleHeatmap(BaseHeatmap):
    def translate(self, data, isLine=False):
        group = svgwrite.container.Group()
        for point in data:
            extras = {
                'opacity': 0.4,
                'fill': HEATMAP_COLORS[point['users_relative'] - 1],
                'stroke': 'white',
            }
            rect = svgwrite.shapes.Rect(
                insert=(
                    0 if isLine else self.gridSize * point['x'],
                    self.gridSize * point['y'],
                ),
                size=(self.gridSize, self.gridSize),
                **extras,
            )
            rect.set_desc(title='{0}%'.format(point['users_relative'] * 10))
            group.add(rect)

        drawing = svgwrite.Drawing(
            'heatmap.svg',
            size=(self.width, self.height),
            profile='full',
            **{
                'class': 'ap-Heatmap_Grid',
                'style': 'background: black;',
            },
        )
        drawing.add(group)
        drawing.save()


class KDEHeatmap(BaseHeatmap):
    def __init__(self, width=640, height=480, gridSize=10):
        super(KDEHeatmap, self).__init__(width=width, height=height, gridSize=gridSize)
        self.densities = []
        self.xyPoints = []
        self.grid = self._genGrid()

        self.h = 0.389
        self.h2 = self.h ** 2

    def _genGrid(self):
        return [
            (j * self.gridSize + self.gridSize / 2, i * self.gridSize + self.gridSize / 2)
            for i in range(0, int(self.height/self.gridSize))
            for j in range(0, int(self.width/self.gridSize))
        ]

    def _psedoInterQuantileRange(self, data):
        n = len(data)
        return statistics.median_low(data[n//2:]) - statistics.median_high(data[:n//2])

    def updateBandwidth(self):
        xPoints = sorted([p[0] for p in self.xyPoints])
        iqr = self._psedoInterQuantileRange(xPoints)
        self.h = 1.06 * min(statistics.stdev(xPoints), iqr / 1.34) * math.pow(len(self.xyPoints), -0.2)
        self.h2 = self.h ** 2
        print('bw: h={0}, h2={1}'.format(self.h, self.h2))

    def gaussian(self, x: float):
        # sqrt(2 * PI) is approximately 2.5066
        return math.exp(-x * x / 2) / 2.5066

    def norm(self, v1, v2):
        # Norm of 2D arrays/vectors
        return math.sqrt((v1[0] - v2[0]) * (v1[0] - v2[0]) + (v1[1] - v2[1]) * (v1[1] - v2[1]))

    def kde(self, gridPoint):
        return statistics.mean(
            [self.gaussian(self.norm(p, gridPoint) / self.h) for p in self.xyPoints]
        ) / self.h2

    def outerScale(self, value, maximum):
        sentinel = len(HEATMAP_COLORS)
        d = int(value / maximum * sentinel)
        return d if d < sentinel else (sentinel - 1)

    def translate(self, data, isLine=False):
        self.xyPoints = [(p['x'] * self.gridSize, p['y'] * self.gridSize) for p in data]
        # self.updateBandwidth()
        self.densities = [self.kde(p) for p in self.grid]
        domainMax = max([v ** 0.4 for v in self.densities])
        print(self.densities)

        group = svgwrite.container.Group()
        for i in range(len(self.grid)):
            point = self.grid[i]
            color = HEATMAP_COLORS[self.outerScale(self.densities[i] ** 0.4, domainMax)]
            extras = {
                'opacity': 0.4,
                'fill': color,
                'stroke': 'white',
            }
            rect = svgwrite.shapes.Rect(
                insert=(
                    point[0] - self.gridSize / 2,
                    point[1] - self.gridSize / 2,
                ),
                size=(
                    self.gridSize,
                    self.gridSize,
                ),
                **extras,
            )
            rect.set_desc(title='{}'.format(self.densities[i] * 10))
            group.add(rect)

        drawing = svgwrite.Drawing(
            'heatmap_kde.svg',
            size=(self.width, self.height),
            profile='full',
            **{
                'class': 'ap-Heatmap_Grid',
                'style': 'background: black;',
            },
        )
        drawing.add(group)
        drawing.save()


def generateInteractions():
    data = []
    for i in range(720):
        data.append(dict(
            x=random.randint(0, grid - 1),
            y=random.randint(0, 100),
            users_relative=random.randint(1, 10),
        ))
    return data


def getInteractions(filename='source.json'):
    if os.path.exists(filename):
        return json.loads(open(filename, 'r').read())

    else:
        return generateInteractions()


def main():
    interactions = getInteractions()

    sheatmap = SimpleHeatmap(width=width, height=height, gridSize=int(width / grid))
    sheatmap.translate(interactions, isLine)

    kdeheatmap = KDEHeatmap(width=width, height=height, gridSize=int(width / grid))
    kdeheatmap.translate(interactions, isLine)


if __name__ == '__main__':
    main()
