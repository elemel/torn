from euclid import *
from itertools import*
from math import *

__all__ = ['Polygon', 'is_point_in_polygon']

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
        edges = [LineSegment2(self.vertices[i], self.vertices[i + 1])
                 for i in xrange(len(self.vertices) - 1)]
        if self.closed and len(self.vertices) >= 3:
            edges.append(LineSegment2(self.vertices[-1], self.vertices[0]))
        return edges

    @property
    def lengths(self):
        return [e.length for e in self.edges]

    @property
    def area(self):
        """
        http://local.wasp.uwa.edu.au/~pbourke/geometry/clockwise/
        """
        if not self.closed:
            return 0
        edges = izip(self.vertices, self.vertices[1:] + self.vertices[:1])
        return sum(v1.x * v2.y - v2.x * v1.y for v1, v2 in edges) / 2

    @property
    def clockwise(self):
        return self.area < 0

    def reverse(self):
        self.vertices.reverse()

def is_point_in_polygon(point, vertices):
    """
    http://local.wasp.uwa.edu.au/~pbourke/geometry/insidepoly/
    """
    count = 0
    x, y = point
    for v1, v2 in izip(vertices, vertices[1:] + vertices[:1]):
        x1, y1 = v1
        x2, y2 = v2
        if min(y1, y2) < y <= max(y1, y2) and x <= max(x1, x2) and y1 != y2:
            if x1 == x2 or x <= (y - y1) * (x2 - x1) / (y2 - y1) + x1:
                count += 1
    return count % 2 != 0
