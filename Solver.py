from __future__ import print_function
import skimage
import skimage.io
import skimage.color
import skimage.measure
import skimage.feature
import skimage.filters
import skimage.transform
import numpy as np
import ctypes
import os
import math
import pyautogui

# Enable multithreading?
MULTITHREAD = True

ailib = None
for suffix in ['so', 'dll', 'dylib']:
    dllfn = 'bin/2048.' + suffix
    if not os.path.isfile(dllfn):
        continue
    ailib = ctypes.CDLL(dllfn)
    break
else:
    print("Couldn't find 2048 library bin/2048.{so,dll,dylib}! Make sure to build it first.")
    exit()

ailib.init_tables()
ailib.find_best_move.argtypes = [ctypes.c_uint64]
ailib.score_toplevel_move.argtypes = [ctypes.c_uint64, ctypes.c_int]
ailib.score_toplevel_move.restype = ctypes.c_float
ailib.execute_move.argtypes = [ctypes.c_int, ctypes.c_uint64]
ailib.execute_move.restype = ctypes.c_uint64

def to_c_board(m):
    board = 0
    i = 0
    for row in m:
        for c in row:
            board |= int(c) << (4*i)
            i += 1
    return board

def print_board(m):
    for row in m:
        for c in row:
            print('%8d' % c, end=' ')
        print()

def _to_val(c):
    if c == 0: return 0
    return 2**c

def to_val(m):
    return [[_to_val(c) for c in row] for row in m]

def _to_score(c):
    if c <= 1:
        return 0
    return (c-1) * (2**c)

def to_score(m):
    return [[_to_score(c) for c in row] for row in m]

if MULTITHREAD:
    from multiprocessing.pool import ThreadPool
    pool = ThreadPool(4)
    def score_toplevel_move(args):
        return ailib.score_toplevel_move(*args)

    def find_best_move(m):
        board = to_c_board(m)

        # print_board(to_val(m))

        scores = pool.map(score_toplevel_move, [(board, move) for move in range(4)])
        bestmove, bestscore = max(enumerate(scores), key=lambda x:x[1])
        if bestscore == 0:
            return -1
        return bestmove
else:
    def find_best_move(m):
        board = to_c_board(m)
        return ailib.find_best_move(board)

def movename(move):
    return ['up', 'down', 'left', 'right'][move]

numbers_map = [None]*16
numbers_aspects = [0]*16

for i in range(16):
    number = skimage.io.imread(f"numbers/{i}.png")
    number = number.astype("uint8")
    number = number > 128
    numbers_map[i] = number
    numbers_aspects[i] = number.shape[0]/number.shape[1]

class Solver:
    def __init__(self):
        pass

    def capture_image(self):
        # capture image from live stream
        img = pyautogui.screenshot()
        img = np.array(img)
        img = skimage.color.rgb2gray(img[:, :, 0:3])
        return img

    def detect_numbers(self, img):
        # detect numbers on captured image
        numbers = np.zeros((4, 4), dtype="int")

        # 2048-4.jpg
        tiles_origin = (395, 730)  # (y, x)
        tiles_spacing = (7, 8)  # (y, x)
        tiles_size = (110, 109)  # (height, width)
        tiles_crop = 4  # pixels

        for i in range(4):

            y1 = tiles_origin[0] + (tiles_size[0] + tiles_spacing[0]) * i
            y2 = y1 + tiles_size[0]
            y1 += tiles_crop
            y2 -= tiles_crop

            for j in range(4):

                x1 = tiles_origin[1] + (tiles_size[1] + tiles_spacing[1]) * j
                x2 = x1 + tiles_size[1]
                x1 += tiles_crop
                x2 -= tiles_crop

                crop = img[y1:y2, x1:x2]

                stddev = np.std(crop)
                if (stddev < 0.01):
                    skimage.io.imsave(f"numbers_detected/{i}_{j}.png", (crop*255).astype("uint8"), check_contrast=False)    
                    continue

                # threshold image (black number on white background)
                thresh = skimage.filters.threshold_otsu(crop)
                crop = ((crop > thresh) * 255).astype("uint8")

                if (np.mean(crop) < 128):
                    crop = 255 - crop
                elif (np.mean(crop) > 250):
                    crop = np.ones_like(crop) * 255

                # crop white space
                yc, xc = np.nonzero(crop == 0)
                crop = crop[np.min(yc):np.max(yc) + 1, np.min(xc):np.max(xc) + 1]

                # find most similar number
                similarity = np.zeros(16, dtype="float64")
                for i_number in range(1, 16):
                    # check if aspect ratios are roughly similar
                    a1 = numbers_aspects[i_number]
                    a2 = crop.shape[0] / crop.shape[1]
                    err = np.abs(1 - a1 / a2)
                    if (err > 0.25):
                        similarity[i_number] = 0.0
                        continue
                    # check if image content is similar
                    number = numbers_map[i_number]
                    resized = skimage.transform.resize(crop, number.shape, anti_aliasing=False) > 0.5
                    # skimage.io.imsave(f"numbers_resized/{i}_{j}_{i_number}.png", resized.astype("uint8")*255)
                    similarity[i_number] = np.count_nonzero(resized == number)
                    
                skimage.io.imsave(f"numbers_detected/{i}_{j}.png", crop)

                exp = np.argmax(similarity)
                if (exp > 0):
                    numbers[i][j] = 2 ** exp

        return numbers

    def numbers_to_board(self, numbers):
        # convert numbers to board
        board = numbers.tolist()
        for i in range(4):
            for j in range(4):
                tval = board[i][j]
                if (tval == 0):
                    board[i][j] = 0
                else:
                    board[i][j] = int(round(math.log(tval, 2)))
        return board

    def compute_move(self, numbers):
        # compute best move
        board = self.numbers_to_board(numbers)
        move = find_best_move(board)
        return move

    def simulate_move(self, move, numbers):
        board = self.numbers_to_board(numbers)
        board = to_c_board(board)
        board = ailib.execute_move(move, board)
        numbers = np.zeros((4,4), dtype="uint")
        k = 0
        for i in range(4):
            for j in range(4):
                val = (board >> (k*4)) & int(0xF)
                if(val > 0):
                    numbers[i][j] = 2**val
                k += 1
        return numbers
