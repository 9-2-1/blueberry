import matplotlib.pyplot as plt


X = []
for a, b, c in [
    (2, 1.5, 40),
    (1.5, 1.5, 40),
    (1.5, 1, 40),
    (2, 1.9, 10),
    (3, 2.9, 10),
    (4, 3.9, 10),
    (5, 4.9, 10),
    (1, 0.9, 10),
    (-3, -4, 80),
]:
    X.extend([a + (b - a) * x / c for x in range(c)])

window = 10
jump = 0.2
W = [1 / (x + 1) ** 0.5 for x in range(window)]
D = [X[i] - X[i - 1] if i > 0 else 0 for i in range(len(X))]
data_out: list[float] = []
for i in range(0, window):
    data_out.append(0)
for i in range(window, len(X)):
    XX = X[i - window : i]
    DD = D[i - window : i]
    for i in range(window):
        if abs(DD[i]) > jump:
            if i == 0:
                DD[i] = DD[i + 1]
            elif i == window - 1:
                DD[i] = DD[i - 1]
            else:
                DD[i] = (DD[i - 1] + DD[i + 1]) / 2
    cur = XX[0]
    curv = DD[0]
    for i in range(1, window):
        curv = curv + (DD[i] - curv) * W[i]
        cur += curv
        cur = cur + (XX[i] - cur) * W[i]
    data_out.append(cur)
N = [*range(len(X))]
plt.plot(N, X, N, data_out)
plt.show()
