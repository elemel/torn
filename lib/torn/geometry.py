from euclid import *
from itertools import*
from math import *

__all__ = ['Polygon']

class Polygon(object):
    def __init__(self, vertices, closed=True):
        self.vertices = list(v.copy() for v in vertices)
        assert len(self.vertices) >= 1
        assert all(isinstance(v, Point2) for v in self.vertices)
        assert type(closed) is bool
        self.closed = closed

    def copy(self):
        return Polygon(self.vertices, self.closed)

    @property
    def edges(self):
        if self.closed:
            return izip(self.vertices, self.vertices[1:] + self.vertices[:1])
        else:
            return izip(self.vertices[:-1], self.vertices[1:])

    @property
    def area(self):
        """
        http://local.wasp.uwa.edu.au/~pbourke/geometry/clockwise/
        """
        if self.closed:
            return sum(v1.x * v2.y - v2.x * v1.y for v1, v2 in self.edges) / 2
        else:
            return 0

    @property
    def clockwise(self):
        return self.area < 0

    def reverse(self):
        self.vertices.reverse()

    def intersect(self, other):
        """
        http://local.wasp.uwa.edu.au/~pbourke/geometry/insidepoly/
        """
        assert isinstance(other, Point2)
        if not self.closed:
            return False
        count = 0
        x, y = other
        for v1, v2 in self.edges:
            x1, y1 = v1
            x2, y2 = v2
            if min(y1, y2) < y <= max(y1, y2) and x <= max(x1, x2) and y1 != y2:
                if x1 == x2 or x <= (y - y1) * (x2 - x1) / (y2 - y1) + x1:
                    count += 1
        return count % 2 != 0
