# Play with triangle mesher

import matplotlib.pyplot as plt
import numpy as np

import triangle as tr

def quad(max_area:float=None):
    A = dict(vertices=np.array(((0, 0), (1, 0), (1, 1), (0, 1))))
    if max_area is not None:
        opt = f'qa{max_area}'
        B = tr.triangulate(A, opt)
    else:
        B = tr.triangulate(A)
    tr.compare(plt, A, B)
    plt.show()



def circle_with_hole(max_area:float=0.05):

    def circle(N, R):
        i = np.arange(N)
        theta = i * 2 * np.pi / N
        pts = np.stack([np.cos(theta), np.sin(theta)], axis=1) * R
        seg = np.stack([i, i + 1], axis=1) % N
        return pts, seg

    pts0, seg0 = circle(30, 1.4)
    pts1, seg1 = circle(16, 0.6)
    pts = np.vstack([pts0, pts1])
    seg = np.vstack([seg0, seg1 + seg0.shape[0]])

    A = dict(vertices=pts, segments=seg, holes=[[0, 0]])
    B = tr.triangulate(A, 'qpa0.05')
    tr.compare(plt, A, B)
    plt.show()

if __name__ == '__main__':
    circle_with_hole()