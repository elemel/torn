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
